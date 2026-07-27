"""Custom Celery database backend using Postgres-generated UUID primary keys."""

import sqlalchemy as sa
from celery import states
from celery.backends.database import DatabaseBackend as _DatabaseBackend
from celery.backends.database.models import _get_utc_now
from celery.backends.database.session import ResultModelBase
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import PickleType


class _Task(ResultModelBase):
    """Task result model with a Postgres UUID primary key."""

    __tablename__ = "celery_taskmeta"
    __table_args__ = {"extend_existing": True}

    id = sa.Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )
    task_id = sa.Column(sa.String(155), unique=True)
    status = sa.Column(sa.String(50), default=states.PENDING)
    result = sa.Column(PickleType, nullable=True)
    date_done = sa.Column(
        sa.DateTime,
        default=_get_utc_now,
        onupdate=_get_utc_now,
        nullable=True,
        index=True,
    )
    traceback = sa.Column(sa.Text, nullable=True)
    created_at = sa.Column(
        sa.DateTime,
        default=_get_utc_now,
        server_default=sa.text("now()"),
        nullable=False,
    )

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id

    def to_dict(self) -> dict:
        """Return a dict representation of the task result."""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "result": self.result,
            "traceback": self.traceback,
            "date_done": self.date_done,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return f"<Task {self.task_id} state: {self.status}>"

    @classmethod
    def configure(cls, schema: str | None = None, name: str | None = None) -> None:
        """Set the schema and table name for this model.

        Args:
            schema: Postgres schema name (e.g. ``async_tasks``).
            name: Override the table name. Defaults to ``celery_taskmeta``.
        """
        cls.__table__.schema = schema
        cls.__table__.name = name or cls.__tablename__


class _TaskExtended(_Task):
    """Extended task result model."""

    __tablename__ = "celery_taskmeta"
    __table_args__ = {"extend_existing": True}

    def to_dict(self) -> dict:
        """Return a dict representation including extended fields."""
        task_dict = super().to_dict()
        task_dict.update(
            {
                "name": self.name,
                "args": self.args,
                "kwargs": self.kwargs,
                "worker": self.worker,
                "retries": self.retries,
                "queue": self.queue,
            }
        )
        return task_dict


class _TaskSet(ResultModelBase):
    """TaskSet result model with a Postgres UUID primary key."""

    __tablename__ = "celery_tasksetmeta"
    __table_args__ = {"extend_existing": True}

    id = sa.Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )
    taskset_id = sa.Column(sa.String(155), unique=True)
    result = sa.Column(PickleType, nullable=True)
    date_done = sa.Column(sa.DateTime, default=_get_utc_now, nullable=True, index=True)

    def __init__(self, taskset_id: str, result: object) -> None:
        self.taskset_id = taskset_id
        self.result = result

    def to_dict(self) -> dict:
        """Return a dict representation of the taskset result."""
        return {
            "taskset_id": self.taskset_id,
            "result": self.result,
            "date_done": self.date_done,
        }

    def __repr__(self) -> str:
        return f"<TaskSet: {self.taskset_id}>"

    @classmethod
    def configure(cls, schema: str | None = None, name: str | None = None) -> None:
        """Set the schema and table name for this model.

        Args:
            schema: Postgres schema name (e.g. ``async_tasks``).
            name: Override the table name. Defaults to ``celery_tasksetmeta``.
        """
        cls.__table__.schema = schema
        cls.__table__.name = name or cls.__tablename__


class TaskResultBackend(_DatabaseBackend):
    """DatabaseBackend that stores task results with Postgres UUID primary keys.

    Drop-in replacement for ``celery.backends.database.DatabaseBackend``.
    Requires PostgreSQL — ``gen_random_uuid()`` is used as the server default
    for the ``id`` column on both the task and taskset result tables.

    Use this backend by setting the Celery ``backend`` argument to
    ``'core.celery.backend.TaskResultBackend'``.
    """

    task_cls = _Task
    taskset_cls = _TaskSet

    @property
    def extended_result(self) -> bool:
        """Return whether extended result storage is enabled.

        Returns:
            True if ``result_extended`` is set in Celery config.
        """
        result: bool = self.app.conf.find_value_for_key("extended", "result")
        return result

    def __init__(self, *args: object, **kwargs: object) -> None:
        if self.extended_result:  # type: ignore[misc]
            self.task_cls = _TaskExtended
        super().__init__(*args, **kwargs)
