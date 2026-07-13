# Guideline Standard

This document defines what a guideline is, when to write one, and how to structure it.

---

## What Is a Guideline?

A guideline is a practical how-to document that teaches developers how to implement a specific concern correctly in this project. It answers: **"How do I do X here?"**

---

## Guidelines vs. Other Documentation

| Document Type | Location | Answers | Example |
|---------------|----------|---------|---------|
| Guideline | `docs/guidelines/` | "How do I do X?" | How to validate input, how to add a new app |
| ADR | `docs/adr/` | "Why did we decide X?" | Why modular monolith, why soft-delete by default |
| Reference doc | `docs/*.md` | "What exists and how is it configured?" | Architecture overview, data model, security model |
| README | Per-folder | "What is this folder and what's inside?" | Module API surface, file descriptions |
| Code Style | `docs/code-style.md` | "What should code look like?" | Naming, formatting, import order |

### Decision Rules

- If you're explaining a **decision and its rationale** → write an ADR
- If you're describing **what exists** at a high level → write/update a reference doc
- If you're teaching **how to accomplish a task** using project patterns → write a guideline
- If you're documenting a **folder's contents and API** → write a README

---

## When to Write a Guideline

Write a guideline when:

- A pattern or convention is used across multiple files/apps and developers need to follow it
- The "right way" to do something is non-obvious or differs from vanilla Django/DRF
- A new developer would need to read multiple source files to understand the approach
- You find yourself explaining the same pattern in code reviews repeatedly

Do NOT write a guideline for:

- A pattern used in exactly one place (document it in that file's docstring or README)
- Standard Django/DRF behavior that works as documented upstream
- Implementation details that change frequently (those belong in code comments)

---

## Structure

Every guideline follows this structure. Sections marked as optional may be omitted if they don't apply.

```markdown
# {Title}

{One or two sentences: what this guideline covers and why it matters.
The intro must scope what the guideline covers AND signal the range/depth.
Good: "How to validate incoming data at each layer — from declarative field constraints to cross-field business rules."
Bad: "This document describes validation."}

---

## Overview

{Brief explanation of the concept. Include Mermaid diagrams if they aids understanding.}

---

## {Core Sections}

{The main content — organized by topic, layer, or workflow step.
Each section should include:
- Explanation of the pattern
- Code examples showing correct usage
- Tables for quick reference where appropriate}

---

## Common Pitfalls (optional)

{Table or list of frequent mistakes and their solutions.}

---

## Decision Guide

{Table mapping scenarios to the recommended approach.
Format: | Scenario | Approach |}
```

### Section Guidelines

- **Overview** — always present. Sets context. Include Mermaid diagrams when the concept involves a flow, lifecycle, or decision tree.
- **Core sections** — the bulk of the document. Organize by whatever axis makes the content most scannable (by layer, by use case, by complexity).
- **Common Pitfalls** — include when there are known mistakes developers make. Skip if the topic is straightforward.
- **Decision Guide** — always present. A quick-reference table that helps developers pick the right approach without reading the full document.

---

## Writing Rules

### Tone and Audience

- Write for a developer joining the project who knows Django/DRF but not this codebase
- Be direct and prescriptive — guidelines tell you what to do, not what you could do
- Use "Use X" and "Do not Y" instead of "You might consider X" or "It's recommended to Y"

### Content

- Show the correct way first, then explain alternatives or edge cases
- Every code example must be syntactically correct and runnable in context
- Include imports in code examples — don't assume the reader knows where things live
- Reference other guidelines by relative link when relevant, don't duplicate content
- Keep examples minimal — show the pattern, not a full feature implementation
- Cover the full picture: include standard Django/DRF approaches alongside project-specific tools. A guideline should teach "how to do X here" completely — if a vanilla framework feature is the correct choice for some scenarios, document it. Do not limit content to custom components only

### Formatting

- Language: English
- Use `---` horizontal rules to separate top-level sections
- Use Mermaid diagrams when they clarify flows, lifecycles, or decision trees — not decoratively
- Use tables for quick-reference comparisons (decision guides, parameter lists, hook summaries)
- Use code blocks with language annotation (`python`, `bash`, `json`)
- Do not use emojis

### Naming

- Filename: `kebab-case.md` (e.g., `input-validation.md`, `creating-a-new-app.md`)
- Title: sentence case, concise noun phrase (e.g., "Input Validation", "Access Control")

#### Picking the Right Name

1. **Describe the concern or goal, not the implementation** — `soft-delete.md` not `soft-deletable-model-mixin.md`
2. **Not too generic** — a name like `validation.md` or `permissions.md` is ambiguous (validation of what? permissions where?). Qualify it: `input-validation.md`, `access-control.md`
3. **Not too specific** — a name like `tenant-filter-backend.md` scopes to one component. Broaden to the concern it serves: `multi-tenancy.md`
4. **Use "building-X" for layer-oriented how-to guides** — when the guideline teaches how to construct something from scratch across multiple patterns (e.g., `building-endpoints.md`, `building-serializers.md`)
5. **Use "creating-X" for procedural checklists** — when the guideline is a step-by-step recipe (e.g., `creating-a-new-app.md`)
6. **Test the name with this question**: "If a developer searches for how to do Y, would they look for this filename?" If the name only makes sense after reading the content, rename it

### Maintenance

- When code patterns change, update the affected guideline in the same PR
- If a guideline becomes obsolete, remove it and update the README index
- Guidelines do not have a "Status" field — they are either current or deleted

---

## Mermaid Diagrams

Include a Mermaid diagram when:

- The concept involves a sequential flow (use `sequenceDiagram`)
- There's a decision tree or branching logic (use `flowchart TD`)
- Multiple components interact in a non-obvious order (use `sequenceDiagram` or `flowchart LR`)

Do NOT include a diagram when:

- The concept is a simple list of options (use a table instead)
- The diagram would just restate what the prose already says
- The flow is linear with no branching (prose or a numbered list is clearer)

---

## Checklist for New Guidelines

Before submitting a new guideline:

1. Does it answer "how do I do X?" (not "why" or "what exists")?
2. Is the pattern used across multiple files/apps?
3. Does it have an Overview section with context?
4. Does it have a Decision Guide table?
5. Are all code examples syntactically correct with imports?
6. Are Mermaid diagrams used only where they add clarity?
7. Is the filename kebab-case and descriptive of the concern?
8. Is the README index updated?
