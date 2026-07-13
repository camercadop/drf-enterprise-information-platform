# Creating a New App

How to add a new domain module — from scaffolding and model definition to serializers, views, URL registration, migrations, and test factories.

---

## Overview

Create a new app when the feature represents a distinct domain boundary (e.g., invoices, notifications, documents). Do not create an app for utility code — that belongs in `core/`.

Each app is a self-contained module with models, serializers, views, and URLs. The platform's global infrastructure (tenant filtering, soft-delete, pagination, response envelope) activates automatically when you inherit from the correct base classes.

---

## Steps

### 1. Scaffold the App

```bash
cd apps/
uv run python ../manage.py startapp <app_name>
```

### 2. Required File Structure

```
apps/<app_name>/
├── migrations/
│   └── __init__.py
├── tests/
│   └── __init__.py
├── __init__.py
├── apps.py
├── models.py
├── serializers.py
├── urls.py
├── views.py
└── README.md
```

Delete any auto-generated files you won't use (`admin.py`, `forms.py`, etc.).

### 3. Configure the App

```python
# apps/<app_name>/apps.py
from django.apps import AppConfig

class <AppName>Config(AppConfig):
    name = "apps.<app_name>"
```

Do NOT set `default_auto_field` — all models define their own UUID primary key.

Register in settings:

```python
# config/settings/base.py
INSTALLED_APPS = [
    ...
    "apps.<app_name>",
]
```

### 4. Define Models

Choose the appropriate base class:

| Resource belongs to a tenant? | Inherit from |
|-------------------------------|--------------|
| Yes | `BaseModel` |
| No (platform-level) | `CoreModel` |

```python
from django.db import models

from core.base.models import BaseModel


class Invoice(BaseModel):
    number = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "invoices"
```

### 5. Define Serializers

```python
from core.base.serializers import DefaultModelSerializer

class InvoiceSerializer(DefaultModelSerializer):
    class Meta:
        model = Invoice
        fields = ["id", "number", "amount", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

class InvoiceListSerializer(DefaultModelSerializer):
    class Meta:
        model = Invoice
        fields = ["id", "number", "amount"]
```

Do not include `tenant` in writable fields — `TenantInjectionSerializerPlugin` handles it.

### 6. Define Views

```python
from core.base.views import BaseViewSet
from core.permissions.base import IsTenantAdmin

class InvoiceViewSet(BaseViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    serializer_classes = {"list": InvoiceListSerializer}
    write_permission_classes = [IsTenantAdmin]
    search_fields = ["number"]
    ordering_fields = ["number", "created_at", "amount"]
    ordering = ["-created_at"]
```

### 7. Define URLs

```python
from rest_framework.routers import DefaultRouter
from . import views

app_name = "<app_name>"

router = DefaultRouter()
router.register("", views.InvoiceViewSet, basename="invoice")

urlpatterns = router.urls
```

### 8. Register URLs in Root

```python
# config/urls.py
urlpatterns = [
    ...
    path("api/<app_name>/", include("apps.<app_name>.urls")),
]
```

### 9. Create and Run Migrations

```bash
uv run python manage.py makemigrations <app_name>
uv run python manage.py migrate
```

### 10. Write the README

Every app must have a `README.md`. Follow the format in [Writing READMEs](writing-readmes.md).

### 11. Add Test Factories

```python
# tests/factories/<app_name>.py
import factory
from apps.<app_name>.models import Invoice

class InvoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invoice

    number = factory.Sequence(lambda n: f"INV-{n:05d}")
    amount = factory.Faker("pydecimal", left_digits=5, right_digits=2, positive=True)
    tenant = factory.SubFactory("tests.factories.tenants.TenantFactory")
```

---

## What You Get for Free

By inheriting from the platform base classes, these behaviors activate automatically:

- Tenant-scoped query filtering (see [Multi-Tenancy](multi-tenancy.md))
- Server-side tenant injection on create (see [Multi-Tenancy](multi-tenancy.md))
- Soft-delete filtering and representation (see [Soft-Delete](soft-delete.md))
- Standard response envelope (see [Building Endpoints](building-endpoints.md#response-envelope))
- Pagination (see [Building Endpoints](building-endpoints.md#pagination))
- Search and ordering filters (see [Building Endpoints](building-endpoints.md))
- Plugin lifecycle execution (see [Building Serializers](building-serializers.md#plugins))

---

## Common Pitfalls

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Forgetting to add the app to `INSTALLED_APPS` | Migrations won't be detected, models won't load | Add `"apps.<app_name>"` to `config/settings/base.py` |
| Including `tenant` in serializer writable fields | Client can forge tenant ownership | Omit it — `TenantInjectionSerializerPlugin` handles injection |
| Missing `app_name` in `urls.py` | URL reversing fails (`reverse("app:view-name")`) | Always set `app_name = "<app_name>"` |
| Using `models.AutoField` or `default_auto_field` | Inconsistent with platform UUID primary keys | Inherit from `BaseModel`/`CoreModel` — they define the PK |
| Putting reusable utilities in the app | Cross-app imports create circular dependencies | Shared logic belongs in `core/` |
| Skipping the README | Other developers can't understand the module's purpose | Every app must have a `README.md` |
| Creating migrations before registering in `INSTALLED_APPS` | Django can't find the app to generate migrations | Register first, then run `makemigrations` |

---

## Decision Guide

| Scenario | Approach |
|----------|----------|
| Feature represents a distinct domain boundary | Create a new app |
| Utility/helper code used across apps | Add to `core/` |
| Resource belongs to a tenant | Inherit from `BaseModel` |
| Platform-level resource (no tenant) | Inherit from `CoreModel` |
| Need elevated write permissions | Set `write_permission_classes` on the viewset |
| Need custom query filtering beyond tenant | Override `get_queryset` on the viewset |
| Feature extends an existing domain (e.g., adding a sub-resource) | Add to the existing app, not a new one |
| Unsure if it's a new app or part of existing | If it shares the same aggregate root, keep it together |
