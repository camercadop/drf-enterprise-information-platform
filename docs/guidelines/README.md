# Guidelines

Practical how-to documents for implementing features correctly in this project. Each guideline covers a specific concern and teaches developers the patterns, conventions, and tools available.

## Index

| Guideline | Summary |
|-----------|---------|
| [Guideline Standard](guideline-standard.md) | How to write a guideline for this folder |
| [Access Control](access-control.md) | Permission classes, tenant isolation, declarative write perms |
| [Creating a New App](creating-a-new-app.md) | Step-by-step checklist for adding a domain module |
| [Error Handling](error-handling.md) | Exception hierarchy, error codes, response envelope |
| [Building Endpoints](building-endpoints.md) | Base classes, lifecycle hooks, pagination, response envelope, URL registration |
| [Building Serializers](building-serializers.md) | Base classes, lifecycle hooks, plugins, ForeignKeyField, output transformation |
| [Input Validation](input-validation.md) | Field, serializer, and model-level validation |
| [Multi-Tenancy](multi-tenancy.md) | Tenant-scoped models, query filtering, injection |
| [Soft-Delete](soft-delete.md) | Deletion strategy, filter backend, serializer mixin |
| [Inter-Module Communication](inter-module-communication.md) | Dependency direction, allowed interfaces, forbidden patterns |
| [Writing READMEs](writing-readmes.md) | Folder-level documentation levels, structure, and rules |

## Related Documentation

- [Architecture](../architecture.md) — system design and layer responsibilities
- [Code Style](../code-style.md) — formatting, naming, structural conventions
- [ADRs](../adr/README.md) — architectural decisions and their rationale
