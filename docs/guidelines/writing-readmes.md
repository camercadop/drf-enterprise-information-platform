# Writing READMEs

How to write folder-level documentation — from choosing the right detail level to structuring content, deciding when to include diagrams, and knowing which folders to skip.

---

## Overview

Every meaningful folder gets a `README.md` that answers the questions a developer would have when using the module, without requiring them to read the source code.

READMEs are not guidelines (they don't teach "how to do X") and not ADRs (they don't explain "why"). They answer: **"What is this folder, what's inside, and how do I use it?"**

---

## When to Write a README

Write a README for:

- Every app in `apps/`
- Every module folder in `core/` with 2+ files
- Top-level packages (`apps/`, `core/`, `docs/`)
- `config/` (one README for the whole folder)

Skip a README for:

- Folders that only contain `__init__.py`
- `__pycache__/`, `.github/`, `.amazonq/`, `tests/`, cache directories
- Individual settings files (covered by the `config/` README)

---

## Levels

READMEs have three levels of detail based on folder depth and complexity.

### Level 1 — Package Root

For top-level packages (`apps/`, `core/`, `docs/`). Answers: "What is this package and what's inside?"

```markdown
# {Package Name}

{One paragraph describing the package's role in the system.}

## Modules

### submodule/

{One-line purpose.}

- `ClassName` — one-line description
- `function_name` — one-line description
```

Level 1 READMEs serve as both navigation and a quick-reference index. Include a brief API summary per submodule (one-liner per public class/function) so developers can find what they need without opening each subfolder's README.

### Level 2 — Submodule

For folders inside a package (`core/permissions/`, `core/utils/`, `config/`). Answers: "What does this module do, what's its public API, and how do I use it?"

```markdown
# {Module Name}

{One paragraph: purpose, responsibility, and when to use it.}

## Structure (optional)

{File tree showing folder contents — include when the folder has 3+ files
and the organization isn't obvious from filenames alone.}

## API

- `ClassName` — one-line description
- `function_name` — one-line description

## Usage

{Short code snippet showing typical import and usage.}
```

### Level 3 — App or Complex Folder

For app modules (`apps/tenants/`, `apps/authentication/`) and deeper folders with 3+ files or non-obvious logic. Answers: "What does each component do, what are the endpoints, permissions, and edge cases?"

```markdown
# {Module Name}

{One paragraph: purpose and scope.}

## Models (if the module defines models)

{Model tables with fields, types, descriptions. Include constraints.}

## Relationships (if 2+ related models)

{Mermaid ER diagram.}

## API Endpoints (if the module exposes endpoints)

{Table: Method, Path, Action, Description.}

## Response Format (if non-trivial responses)

{Example JSON showing success and error shapes.}

## Error Responses (if the module has specific error contracts)

{Table: Endpoint/Condition, Error shape/code.}

## Permissions (if the module enforces access rules)

{Table: Action, Requirement.}

## Validation Rules (if the module has input constraints)

{Table: Field, Constraint.}

## Utilities (if the module exposes public helpers)

{Public functions/classes with signatures and usage examples.}

## Notes (optional)

{Gotchas, constraints, or brief design rationale that helps consumers
understand limitations. Keep it short — full reasoning belongs in an ADR.}
```

All Level 3 sections are optional — include only those that apply to the module. An app without endpoints skips "API Endpoints", "Response Format", "Error Responses", and "Permissions".

---

## Level Comparison

| Aspect | Level 1 | Level 2 | Level 3 |
|--------|---------|---------|---------|
| Focus | Navigation + quick-reference | API surface | Full module documentation |
| Modules with API summaries | ✓ | — | — |
| Structure (file tree) | — | Optional | — |
| API list | — | ✓ | ✓ |
| Code examples | — | ✓ (brief) | ✓ (detailed) |
| Models/endpoints | — | — | ✓ (if applicable) |
| Response/error format | — | — | ✓ (if applicable) |
| Permissions/validation | — | — | ✓ (if applicable) |
| Notes/rationale | — | — | ✓ (optional, brief) |

---

## Writing Rules

### Content

- Answer the questions a developer would have when *using* the module — not when *building* it
- Include imports in code examples
- Document the public API only — skip internal helpers unless they have non-obvious behavior
- Link to related guidelines when the README touches a cross-cutting concern (e.g., link to [Multi-Tenancy](multi-tenancy.md) when documenting a tenant plugin)

### Mermaid Diagrams

- Use ER diagrams (`erDiagram`) when the module has 2+ related models
- Use flowcharts when documenting filter/plugin behavior with branching logic
- Do not add diagrams as decoration — only when they clarify relationships or flows that prose alone can't convey efficiently

### Formatting

- Language: English
- Title: the folder/module name in sentence case
- Use tables for structured data (fields, endpoints, permissions)
- Use code blocks with language annotation
- Do not use emojis

### Level Assignment

| Folder | Level |
|--------|-------|
| `apps/`, `core/`, `docs/` | 1 |
| `core/permissions/`, `core/utils/`, `core/filters/`, `config/` | 2 |
| `apps/tenants/`, `apps/authentication/`, `apps/users/` | 3 |
| `core/base/` (many files, complex API) | 3 |
| Any folder with 3+ files and non-obvious logic | 3 |
| Any folder with 1-2 files and a clear API | 2 |

---

## Common Pitfalls

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Documenting implementation details that change frequently | README goes stale quickly | Document the *what* and *how to use*, not the *how it works internally* |
| Duplicating guideline content | Two places to maintain, inevitable drift | Link to the guideline instead |
| Writing a README for a `__init__.py`-only folder | Noise, no value | Skip it |
| Missing code examples in Level 2/3 | Developer still has to read source to understand usage | Always include at least one usage snippet |
| Documenting private/internal helpers | Couples consumers to implementation | Only document the public API |

---

## Decision Guide

| Scenario | Approach |
|----------|----------|
| Top-level package with subfolders | Level 1 — modules table |
| Utility/infrastructure folder with a clear API | Level 2 — API list + usage example |
| App with models, endpoints, permissions | Level 3 — full module documentation |
| Folder with only `__init__.py` | Skip |
| `tests/` folder | Skip |
| Folder behavior is a cross-cutting concern | Document basics in README, link to the guideline for full details |
| Unsure about the level | If a developer needs to know endpoints/permissions to use it → Level 3; if they just need the API → Level 2 |
