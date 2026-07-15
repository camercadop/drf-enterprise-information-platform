# API Documentation

How to annotate endpoints and serializers so `drf-spectacular` generates accurate OpenAPI schemas — from zero-config defaults to explicit overrides for edge cases.

---

## Overview

The project uses `drf-spectacular` to auto-generate an OpenAPI 3.0 schema from DRF views and serializers. Most endpoints require no manual annotation — the schema is inferred from serializer fields, viewset actions, and URL patterns.

Manual annotation is needed when:

- The inferred schema is incorrect or incomplete (e.g., polymorphic responses, file uploads)
- You want to add descriptions, examples, or tags beyond what the code expresses
- An endpoint uses `APIView` with no serializer (raw `request.data` handling)

---

## Zero-Config Defaults

`drf-spectacular` automatically documents:

- Request/response bodies from serializer fields (types, required, nullable)
- Path and query parameters from URL kwargs and filter backends
- Authentication requirements from `permission_classes`
- Pagination envelope from the configured pagination class
- HTTP methods and status codes from viewset actions

The project uses a custom `AutoSchema` (`core.openapi.AutoSchema`) that wraps all 2xx responses in the `{status: "OK", data: ...}` envelope automatically. No per-view annotation is needed for the envelope — it's applied globally.

If your endpoint uses `BaseViewSet` with a typed serializer, the schema is generated correctly with no extra work.

---

## Adding Descriptions

### View/ViewSet Docstrings

The class docstring becomes the operation description in the schema:

```python
from core.base.views import BaseViewSet

from .models import Invoice
from .serializers import InvoiceSerializer


class InvoiceViewSet(BaseViewSet):
    """Manage invoices for the current tenant.

    list:
    Return all invoices, ordered by creation date.

    create:
    Create a new invoice. Requires admin role.
    """

    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
```

Per-action descriptions use the `action_name:\n description` format in the docstring.

---

## Explicit Schema Annotation

### @extend_schema

Use `@extend_schema` when the inferred schema is wrong or needs enrichment:

```python
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import PasswordChangeSerializer


class PasswordChangeView(APIView):
    @extend_schema(
        request=PasswordChangeSerializer,
        responses={200: None},
        description="Change the authenticated user's password.",
    )
    def post(self, request: Request) -> Response:
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_200_OK)
```

### Common @extend_schema Parameters

| Parameter | Use Case |
|-----------|----------|
| `request` | Override inferred request body serializer |
| `responses` | Override inferred response body (use `{status: Serializer}` or `{status: None}`) |
| `description` | Operation description (overrides docstring) |
| `summary` | Short one-line summary shown in Swagger UI |
| `tags` | Group endpoints under custom tags |
| `exclude` | Set to `True` to hide the endpoint from the schema |
| `parameters` | Manually define query/path parameters |

### Excluding Endpoints

```python
from drf_spectacular.utils import extend_schema


@extend_schema(exclude=True)
def internal_action(self, request):
    ...
```

---

## Serializer Annotations

### Field Descriptions via help_text

`help_text` on serializer fields maps directly to the OpenAPI field description:

```python
from rest_framework import serializers


class TenantSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=100,
        help_text="Display name of the tenant organization.",
    )
    is_active = serializers.BooleanField(
        read_only=True,
        help_text="Whether the tenant is currently active.",
    )
```

### Inline Examples

Use `@extend_schema_serializer` for request/response examples:

```python
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from rest_framework import serializers


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Valid tenant",
            value={"name": "Acme Corp", "slug": "acme-corp"},
            request_only=True,
        ),
    ]
)
class TenantCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    slug = serializers.SlugField(max_length=50)
```

---

## Custom Actions

`@action` decorators on viewsets are documented automatically. Add `@extend_schema` only if the inferred types are wrong:

```python
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from core.base.views import BaseViewSet


class MembershipViewSet(BaseViewSet):
    @extend_schema(request=None, responses={204: None})
    @action(detail=True, methods=["post"])
    def deactivate(self, request: Request, pk: str | None = None) -> Response:
        membership = self.get_object()
        membership.is_active = False
        membership.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)
```

---

## Tags

By default, endpoints are grouped by viewset name. Override with `@extend_schema(tags=[...])` or configure globally:

```python
# config/settings/base.py
SPECTACULAR_SETTINGS = {
    "TITLE": "DRF Enterprise Information Platform",
    "TAGS": [
        {"name": "Authentication", "description": "Login, logout, token management"},
        {"name": "Tenants", "description": "Tenant CRUD and configuration"},
    ],
}
```

---

## Validating the Schema

Generate and validate the schema locally:

```bash
# Generate schema to stdout
uv run python manage.py spectacular --color --validate

# Write to file
uv run python manage.py spectacular --file schema.yml
```

---

## Decision Guide

| Scenario | Approach |
|----------|----------|
| Standard ViewSet with typed serializer | No annotation needed — schema is inferred |
| APIView with no serializer | Use `@extend_schema(request=..., responses=...)` |
| Action returns 204 with no body | `@extend_schema(responses={204: None})` |
| Field needs a description | Add `help_text` on the serializer field |
| Endpoint should be hidden | `@extend_schema(exclude=True)` |
| Custom grouping in Swagger UI | Use `tags` parameter or `SPECTACULAR_SETTINGS["TAGS"]` |
| Polymorphic or union responses | Use `PolymorphicProxySerializer` from drf-spectacular |
| File upload endpoint | Use `@extend_schema(request={"multipart/form-data": ...})` |
