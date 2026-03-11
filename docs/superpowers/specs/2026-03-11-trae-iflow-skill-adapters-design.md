# Trae And iFlow Skill Adapter Design

**Date:** 2026-03-11

**Status:** Approved by user in terminal discussion

## Goal

Add two more host-side adapters for the existing WeChat republish skill system:

- a native iFlow CLI project memory adapter
- a thin Trae-oriented skill adapter

The adapters must continue to treat this repository as the deterministic upload backend while letting the host tool use its own model for article generation.

## Current State

- The repository already has:
  - a generic core skill at `skills/wechat-article-republish/`
  - a thin Codex/Claude Code adapter at `skills/codex-wechat-article-republish/`
- The project CLI already supports Markdown upload through:

```bash
python3 src/article_pipeline.py upload --url <article_url> --markdown <generated.md>
```

## Verified External Facts

### iFlow CLI

Official docs state:

- `IFLOW.md` is the core memory file for iFlow CLI
- project-level `IFLOW.md` is supported at `/path/to/your/project/IFLOW.md`
- `IFLOW.md` supports `@` imports for modular organization

Sources:

- https://platform.iflow.cn/en/cli/configuration/iflow
- https://platform.iflow.cn/cli/configuration/settings

### Trae

Official public pages confirm:

- Trae is an AI-first IDE / agent workspace
- public blog index includes posts for `Agent Skills in TRAE`, `TRAE Rules`, and `@Agent`

This is enough to justify a Trae-oriented rules/skill adapter, but not enough to assert a single canonical local config filename equivalent to `IFLOW.md`.

Sources:

- https://www.trae.ai/blog
- https://www.trae.ai/solo

## Options Considered

### Option 1: Add both adapters as repo-local `skills/*/SKILL.md`

Pros:

- uniform repo shape

Cons:

- does not use iFlow's native `IFLOW.md` memory mechanism

### Option 2: Add `IFLOW.md` for iFlow and `skills/trae-.../SKILL.md` for Trae

Pros:

- uses iFlow in the shape its docs describe
- avoids inventing unsupported Trae file conventions
- keeps the generic core skill as source of truth

Cons:

- adapter formats differ slightly

## Decision

Use Option 2.

## Architecture

### iFlow Adapter

Add root-level `IFLOW.md` that:

- imports the generic core skill and references with `@` syntax
- states that iFlow should use its own model to generate the Markdown draft
- points iFlow to the repository CLI for dry-run and upload

This keeps the iFlow adapter minimal and aligned with official project-memory behavior.

### Trae Adapter

Add `skills/trae-wechat-article-republish/SKILL.md` that:

- targets Trae rules / agent-skill style usage
- points back to the generic core skill
- states that Trae should generate the Markdown itself
- points to the repository CLI for dry-run and upload

This avoids guessing at an unsupported Trae-specific root config format.

## File Layout

```text
IFLOW.md
skills/
  wechat-article-republish/
    SKILL.md
    references/
      markdown-contract.md
      workflow.md
  codex-wechat-article-republish/
    SKILL.md
  trae-wechat-article-republish/
    SKILL.md
```

## Non-Goals

- creating a Trae-specific root memory filename without official evidence
- duplicating the Markdown contract into each adapter
- changing the project CLI behavior

## Validation Strategy

- confirm root-level `IFLOW.md` exists
- confirm `skills/trae-wechat-article-republish/SKILL.md` exists
- confirm adapters point to the generic core instead of duplicating rules
- confirm README points to the new adapters
- confirm CLI help output still matches the adapter instructions
