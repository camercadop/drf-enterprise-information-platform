"""Tests for core.base.context scope management."""

import pytest

from core.base.context import bind_scope, get_bound_scope, unbind_scope


class TestGetBoundScope:
    def test_returns_empty_dict_when_unbound(self):
        assert get_bound_scope() == {}

    def test_returns_bound_scope(self):
        token = bind_scope({"tenant_id": "abc-123"})
        try:
            assert get_bound_scope() == {"tenant_id": "abc-123"}
        finally:
            unbind_scope(token)


class TestBindScope:
    def test_returns_token(self):
        token = bind_scope({"tenant_id": "abc-123"})
        try:
            assert token is not None
        finally:
            unbind_scope(token)

    def test_overwrites_previous_scope(self):
        token1 = bind_scope({"tenant_id": "first"})
        token2 = bind_scope({"tenant_id": "second"})
        try:
            assert get_bound_scope() == {"tenant_id": "second"}
        finally:
            unbind_scope(token2)
            unbind_scope(token1)


class TestUnbindScope:
    def test_restores_previous_state(self):
        token = bind_scope({"tenant_id": "abc-123"})
        unbind_scope(token)
        assert get_bound_scope() == {}

    def test_restores_nested_scope(self):
        token1 = bind_scope({"tenant_id": "outer"})
        token2 = bind_scope({"tenant_id": "inner"})

        unbind_scope(token2)
        assert get_bound_scope() == {"tenant_id": "outer"}

        unbind_scope(token1)
        assert get_bound_scope() == {}

    def test_raises_on_reused_token(self):
        token = bind_scope({"tenant_id": "abc-123"})
        unbind_scope(token)

        with pytest.raises(RuntimeError):
            unbind_scope(token)
