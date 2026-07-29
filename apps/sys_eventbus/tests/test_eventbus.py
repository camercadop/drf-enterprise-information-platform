"""Tests for sys_eventbus publisher, consumer, and tasks."""

import uuid
from unittest.mock import MagicMock, call, patch

import pytest
from django.test import override_settings

from apps.sys_eventbus.envelope import EventEnvelope
from apps.sys_eventbus.models import DeadLetterEvent, ProcessedEvent


# ---------------------------------------------------------------------------
# Publisher
# ---------------------------------------------------------------------------

EVENTBUS_SETTINGS = {
    "STREAM_NAME": "test:eventbus",
    "CONSUMER_GROUP": "test_group",
    "CONSUMER_NAME": "test_consumer",
    "BATCH_SIZE": 10,
    "MAX_RETRIES": 3,
}


class TestPublish:
    def test_publishes_event_and_returns_message_id(self) -> None:
        from apps.sys_eventbus.publisher import publish

        mock_client = MagicMock()
        mock_client.xadd.return_value = "1700000000000-0"

        with (
            patch("apps.sys_eventbus.publisher.get_redis_client", return_value=mock_client),
            override_settings(APP_SYS_EVENTBUS=EVENTBUS_SETTINGS),
        ):
            message_id = publish(
                event_type="document.created",
                payload={"key": "value"},
                tenant_id="tenant-1",
                actor_id="actor-1",
            )

        assert message_id == "1700000000000-0"
        mock_client.xadd.assert_called_once()
        args = mock_client.xadd.call_args
        assert args[0][0] == "test:eventbus"

    def test_publish_event_from_request_extracts_context(self) -> None:
        from apps.sys_eventbus.publisher import publish_event_from_request

        mock_client = MagicMock()
        mock_client.xadd.return_value = "1700000000000-0"
        request = MagicMock()
        request.user.pk = uuid.uuid4()
        request.auth = {"tenant_id": str(uuid.uuid4())}

        with (
            patch("apps.sys_eventbus.publisher.get_redis_client", return_value=mock_client),
            patch("apps.sys_eventbus.publisher.get_tenant_id", return_value="tenant-1"),
            override_settings(APP_SYS_EVENTBUS=EVENTBUS_SETTINGS),
        ):
            message_id = publish_event_from_request("doc.created", {"x": 1}, request)

        assert message_id == "1700000000000-0"

    def test_stream_name_defaults_to_sys_eventbus(self) -> None:
        from apps.sys_eventbus.publisher import _stream_name

        with override_settings(APP_SYS_EVENTBUS={}):
            assert _stream_name() == "sys:eventbus"

    def test_stream_name_reads_from_settings(self) -> None:
        from apps.sys_eventbus.publisher import _stream_name

        with override_settings(APP_SYS_EVENTBUS={"STREAM_NAME": "custom:stream"}):
            assert _stream_name() == "custom:stream"


# ---------------------------------------------------------------------------
# Consumer
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEnsureGroup:
    def test_creates_group_when_not_exists(self) -> None:
        from apps.sys_eventbus.consumer import _ensure_group

        mock_client = MagicMock()
        with patch("apps.sys_eventbus.consumer.get_redis_client", return_value=mock_client):
            _ensure_group("stream", "group")

        mock_client.xgroup_create.assert_called_once_with("stream", "group", id="0", mkstream=True)

    def test_ignores_busygroup_error(self) -> None:
        from apps.sys_eventbus.consumer import _ensure_group

        mock_client = MagicMock()
        mock_client.xgroup_create.side_effect = Exception("BUSYGROUP already exists")

        with patch("apps.sys_eventbus.consumer.get_redis_client", return_value=mock_client):
            _ensure_group("stream", "group")  # should not raise

    def test_reraises_non_busygroup_error(self) -> None:
        from apps.sys_eventbus.consumer import _ensure_group

        mock_client = MagicMock()
        mock_client.xgroup_create.side_effect = Exception("connection refused")

        with patch("apps.sys_eventbus.consumer.get_redis_client", return_value=mock_client):
            with pytest.raises(Exception, match="connection refused"):
                _ensure_group("stream", "group")


@pytest.mark.django_db
class TestPollStream:
    def _make_fields(self, event_type: str = "test.event") -> dict[str, str]:
        envelope = EventEnvelope(type=event_type, payload={"k": "v"})
        return envelope.to_redis_fields()

    def test_returns_early_when_no_messages(self) -> None:
        from apps.sys_eventbus.consumer import poll_stream

        mock_client = MagicMock()
        mock_client.xreadgroup.return_value = []

        with (
            patch("apps.sys_eventbus.consumer.get_redis_client", return_value=mock_client),
            patch("apps.sys_eventbus.consumer._ensure_group"),
            override_settings(APP_SYS_EVENTBUS=EVENTBUS_SETTINGS),
        ):
            poll_stream()

        mock_client.xack.assert_not_called()

    def test_skips_already_processed_message(self) -> None:
        from apps.sys_eventbus.consumer import poll_stream

        fields = self._make_fields()
        ProcessedEvent.objects.create(message_id="msg-1", event_type="test.event")

        mock_client = MagicMock()
        mock_client.xreadgroup.return_value = [("stream", [("msg-1", fields)])]

        with (
            patch("apps.sys_eventbus.consumer.get_redis_client", return_value=mock_client),
            patch("apps.sys_eventbus.consumer._ensure_group"),
            override_settings(APP_SYS_EVENTBUS=EVENTBUS_SETTINGS),
        ):
            poll_stream()

        mock_client.xack.assert_called_once_with("test:eventbus", "test_group", "msg-1")

    def test_skips_message_with_no_handlers(self) -> None:
        from apps.sys_eventbus.consumer import poll_stream

        fields = self._make_fields("unregistered.event")
        mock_client = MagicMock()
        mock_client.xreadgroup.return_value = [("stream", [("msg-2", fields)])]

        with (
            patch("apps.sys_eventbus.consumer.get_redis_client", return_value=mock_client),
            patch("apps.sys_eventbus.consumer._ensure_group"),
            patch("apps.sys_eventbus.consumer.get_handlers", return_value=[]),
            override_settings(APP_SYS_EVENTBUS=EVENTBUS_SETTINGS),
        ):
            poll_stream()

        mock_client.xack.assert_called_once()

    def test_dispatches_handler_task_for_each_handler(self) -> None:
        from apps.sys_eventbus.consumer import poll_stream

        fields = self._make_fields("test.event")
        mock_handler = MagicMock()
        mock_handler.__qualname__ = "test_handler"
        mock_client = MagicMock()
        mock_client.xreadgroup.return_value = [("stream", [("msg-3", fields)])]
        mock_task = MagicMock()

        with (
            patch("apps.sys_eventbus.consumer.get_redis_client", return_value=mock_client),
            patch("apps.sys_eventbus.consumer._ensure_group"),
            patch("apps.sys_eventbus.consumer.get_handlers", return_value=[mock_handler]),
            patch("apps.sys_eventbus.tasks.dispatch_handler", mock_task),
            override_settings(APP_SYS_EVENTBUS=EVENTBUS_SETTINGS),
        ):
            poll_stream()

        mock_task.delay.assert_called_once_with("test_handler", "msg-3", fields)
        mock_client.xack.assert_called_once()


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDispatchHandler:
    def _make_fields(self, event_type: str = "test.event") -> dict[str, str]:
        envelope = EventEnvelope(type=event_type, payload={"k": "v"})
        return envelope.to_redis_fields()

    def test_skips_already_processed_message(self) -> None:
        from apps.sys_eventbus.tasks import dispatch_handler

        ProcessedEvent.objects.create(message_id="msg-done", event_type="test.event")
        mock_handler = MagicMock()

        with patch("apps.sys_eventbus.tasks._resolve_handler", return_value=mock_handler):
            dispatch_handler("some.handler", "msg-done", self._make_fields())

        mock_handler.assert_not_called()

    def test_skips_when_handler_not_found(self) -> None:
        from apps.sys_eventbus.tasks import dispatch_handler

        with patch("apps.sys_eventbus.tasks._resolve_handler", return_value=None):
            dispatch_handler("missing.handler", "msg-x", self._make_fields())

        assert not ProcessedEvent.objects.filter(message_id="msg-x").exists()

    def test_records_processed_event_on_success(self) -> None:
        from apps.sys_eventbus.tasks import dispatch_handler

        mock_handler = MagicMock()

        with patch("apps.sys_eventbus.tasks._resolve_handler", return_value=mock_handler):
            dispatch_handler("ok.handler", "msg-ok", self._make_fields())

        assert ProcessedEvent.objects.filter(message_id="msg-ok").exists()
        mock_handler.assert_called_once()

    def test_writes_dlq_after_exhausting_retries(self) -> None:
        from apps.sys_eventbus.tasks import dispatch_handler

        mock_handler = MagicMock(side_effect=ValueError("boom"))
        fields = self._make_fields()

        with (
            patch("apps.sys_eventbus.tasks._resolve_handler", return_value=mock_handler),
            patch("apps.sys_eventbus.tasks._max_retries", return_value=1),
            override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=False),
            patch("celery.app.task.Task.backend", new_callable=MagicMock),
        ):
            dispatch_handler.apply(args=("fail.handler", "msg-dlq", fields), retries=0)

        assert DeadLetterEvent.objects.filter(message_id="msg-dlq").exists()
        assert not ProcessedEvent.objects.filter(message_id="msg-dlq").exists()

    def test_retries_before_dlq(self) -> None:
        from apps.sys_eventbus.tasks import dispatch_handler

        mock_handler = MagicMock(side_effect=ValueError("transient"))
        fields = self._make_fields()

        with (
            patch("apps.sys_eventbus.tasks._resolve_handler", return_value=mock_handler),
            patch("apps.sys_eventbus.tasks._max_retries", return_value=3),
            override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=False),
            patch("celery.app.task.Task.backend", new_callable=MagicMock),
        ):
            dispatch_handler.apply(args=("retry.handler", "msg-retry", fields), retries=0)

        # Handler was called max_retries times — retry path was exercised
        assert mock_handler.call_count == 3


@pytest.mark.django_db
class TestResolveHandler:
    def test_returns_handler_by_qualname(self) -> None:
        from apps.sys_eventbus.registry import _registry
        from apps.sys_eventbus.tasks import _resolve_handler

        def my_handler(envelope: EventEnvelope) -> None:
            pass

        _registry["resolve.test"].append(my_handler)
        try:
            result = _resolve_handler(my_handler.__qualname__)
            assert result is my_handler
        finally:
            _registry["resolve.test"].remove(my_handler)

    def test_returns_none_when_not_found(self) -> None:
        from apps.sys_eventbus.tasks import _resolve_handler

        assert _resolve_handler("nonexistent.handler") is None
