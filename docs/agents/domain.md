# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root — glossary of domain terms. Will be created lazily by `/domain-modeling` when terms are resolved.
- **`docs/adr/`** — 7 ADRs currently exist covering the foundational architecture decisions (Python FastAPI, Web app vs miniprogram, PostgreSQL+pgvector, LangGraph agent architecture, WeChat OAuth, React Next.js frontend). Read ADRs that touch the area you're about to work in.
- **`docs/questionnaire-canonical.md`** — the canonical source-of-truth declaration for the question bank (4-level authority hierarchy). Read before modifying any scoring or questionnaire code.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The `/domain-modeling` skill creates `CONTEXT.md` lazily when terms or decisions actually get resolved.

## File structure

Single-context repo:

```
/
├── CONTEXT.md                       ← to be created
├── docs/
│   ├── adr/                         ← 7 ADRs
│   ├── agents/                      ← this file + issue-tracker + triage-labels
│   ├── scoring-design.md
│   ├── build-plan.md
│   └── questionnaire-canonical.md
├── backend/
│   └── app/
└── frontend/
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (PostgreSQL+pgvector) — but worth reopening because…_
