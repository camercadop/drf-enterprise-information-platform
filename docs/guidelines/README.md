# Guidelines

Practical how-to documents for implementing features correctly in this project. Each guideline covers a specific concern and teaches developers the patterns, conventions, and tools available.

## Index

Sorted by importance to the project — core architectural concerns first, then implementation patterns, then supporting processes.

| Guideline | Summary |
|-----------|---------|
| [Multi-Tenancy](multi-tenancy.md) | Tenant-scoped models, query filtering, injection |
| [Access Control](access-control.md) | Permission classes, tenant isolation, declarative write perms |
| [Building Endpoints](building-endpoints.md) | Base classes, lifecycle hooks, pagination, response envelope, URL registration |
| [Building Serializers](building-serializers.md) | Base classes, lifecycle hooks, plugins, ForeignKeyField, output transformation |
| [API Documentation](api-documentation.md) | Annotating endpoints for OpenAPI schema generation (drf-spectacular) |
| [Input Validation](input-validation.md) | Field, serializer, and model-level validation |
| [Error Handling](error-handling.md) | Exception hierarchy, error codes, response envelope |
| [Soft-Delete](soft-delete.md) | Deletion strategy, filter backend, serializer mixin |
| [Inter-Module Communication](inter-module-communication.md) | Dependency direction, allowed interfaces, forbidden patterns |
| [Writing Tests](writing-tests.md) | Base classes, factories, fixtures, and test patterns |
| [Management Commands](management-commands.md) | BaseCommand, naming, output (Rich), logging, CI integration |
| [Creating a New App](creating-a-new-app.md) | Step-by-step checklist for adding a domain module |
| [Writing READMEs](writing-readmes.md) | Folder-level documentation levels, structure, and rules |
| [Guideline Standard](guideline-standard.md) | How to write a guideline for this folder |

## Related Documentation

- [Architecture](../architecture.md) — system design and layer responsibilities
- [Code Style](../code-style.md) — formatting, naming, structural conventions
- [ADRs](../adr/README.md) — architectural decisions and their rationale
