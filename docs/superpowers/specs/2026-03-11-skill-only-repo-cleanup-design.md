# Skill-Only Repo Cleanup Design

## Goal

Shrink this repository into a product-focused codebase for WeChat article republish skills, while keeping every supported adapter: generic skill, Codex/Claude Code, Trae, and iFlow.

## Scope

Keep only files that directly support one of these concerns:

- deterministic WeChat republish CLI implementation
- tests for the republish pipeline
- adapter skills and iFlow memory/example files
- minimal repository operations needed to package the repo
- minimal entrypoint documentation

Delete the SDAC template, governance pack, whitepaper material, and other generic scaffolding that no longer serves the product goal.

## Keep

- `src/`
- `tests/`
- `skills/`
- `iflow/examples/`
- `IFLOW.md`
- `README.md`
- `requirements.txt`
- `LICENSE`
- `.gitignore`
- `tools/package.sh`
- `docs/superpowers/`

## Delete

- `.claude/`
- `CHANGELOG.md`
- `docs/README.md`
- `docs/whitepaper.md`
- `docs/zh/`
- `examples/`
- `res/`
- `spec/`
- `spec-team/`
- `tools/README.md`
- `tools/checklists/`
- `tools/templates/`

## Documentation Changes

- Rewrite `README.md` to describe this repository as a WeChat republish skill backend.
- Document the kept adapters and the core CLI commands.
- Remove references to deleted SDAC docs and template paths.
- Leave `IFLOW.md` and adapter skill docs as product-facing integration docs.

## Safety Rules

- Do not delete files under `src/`, `tests/`, `skills/`, or `iflow/examples/`.
- Do not change business logic unless a kept file references a deleted path and must be repaired.
- Treat existing uncommitted business-code changes as in-scope only when they are inside files that must remain.

## Verification

After cleanup:

- no kept file should reference deleted paths
- the package script should parse successfully
- Python tests should run from `python3 -m pytest`
- `git status` should show only the intended keep/delete set
