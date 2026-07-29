"""Tests for core.celery.backend."""


class TestTask:
    def test_init_sets_task_id(self) -> None:
        from core.celery.backend import _Task

        task = _Task("abc-123")
        assert task.task_id == "abc-123"

    def test_to_dict_contains_expected_keys(self) -> None:
        from core.celery.backend import _Task

        task = _Task("abc-123")
        result = task.to_dict()
        assert set(result.keys()) == {"task_id", "status", "result", "traceback", "date_done", "created_at"}

    def test_repr(self) -> None:
        from core.celery.backend import _Task

        task = _Task("abc-123")
        assert "abc-123" in repr(task)


class TestTaskExtended:
    def test_to_dict_includes_extended_fields(self) -> None:
        from core.celery.backend import _TaskExtended

        task = _TaskExtended("ext-1")
        result = task.to_dict()
        assert "name" in result
        assert "args" in result
        assert "worker" in result


class TestTaskSet:
    def test_init_sets_taskset_id_and_result(self) -> None:
        from core.celery.backend import _TaskSet

        ts = _TaskSet("ts-1", {"key": "val"})
        assert ts.taskset_id == "ts-1"
        assert ts.result == {"key": "val"}

    def test_to_dict_contains_expected_keys(self) -> None:
        from core.celery.backend import _TaskSet

        ts = _TaskSet("ts-1", None)
        result = ts.to_dict()
        assert set(result.keys()) == {"taskset_id", "result", "date_done"}

    def test_repr(self) -> None:
        from core.celery.backend import _TaskSet

        ts = _TaskSet("ts-1", None)
        assert "ts-1" in repr(ts)
