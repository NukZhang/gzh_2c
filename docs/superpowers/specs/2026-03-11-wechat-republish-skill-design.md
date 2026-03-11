# WeChat Republish Skill Design

**Date:** 2026-03-11

**Status:** Approved by user in terminal discussion

## Goal

Package the current project as a reusable skill workflow for WeChat article republishing, so external AI tools can use their own model capability for rewrite generation while this project remains the deterministic upload executor.

The design must avoid binding the workflow to a single AI CLI such as Codex, Claude Code, or Trae.

## Current State

- The project already supports:
  - source article image extraction and processing
  - Markdown-based draft assembly
  - WeChat draft upload
  - optional in-project AI CLI generation path
- The workflow has now been validated end-to-end with a real WeChat draft upload.

What is missing:

- a reusable skill specification that tells an external AI tool how to:
  - trigger on the right user intent
  - generate compliant Markdown with its own model
  - hand off the final Markdown to this project for dry-run or upload
- a thin tool-specific adapter layer for immediate use in Codex/Claude Code style environments

## Problem Framing

The project should not be treated as "the AI writer." It should be treated as the stable execution backend for:

1. article image preparation
2. Markdown-to-WeChat draft conversion
3. real draft submission

The AI tool should own:

1. source article understanding
2. user-thought incorporation
3. rewrite generation
4. markdown authoring decisions

## Options Considered

### Option 1: Create only a tool-specific skill

Pros:

- fastest immediate usability

Cons:

- binds the workflow to one AI tool
- difficult to port cleanly later

### Option 2: Create only a repo-local generic skill specification

Pros:

- neutral and portable
- preserves a clean boundary between AI tool and upload backend

Cons:

- not immediately installable in a specific skill ecosystem

### Option 3: Create a two-layer structure with generic core plus thin tool adapter

Pros:

- immediate usability in current tools
- portable workflow definition
- minimizes duplicated rules

Cons:

- slightly more structure to maintain

## Decision

Use Option 3.

The repository will contain:

- a generic core skill definition that describes the workflow independent of any one AI host
- a thin Codex/Claude Code adapter skill that references the core workflow and gives those tools a directly usable entrypoint

## Architecture

### Layer 1: Generic Core Skill

Path:

- `skills/wechat-article-republish/`

Purpose:

- define the portable workflow
- define required Markdown shape
- define handoff to the project CLI
- define dry-run then upload workflow

This layer is the source of truth for:

- triggering conditions
- output format
- operational steps
- failure handling

### Layer 2: Tool Adapter Skill

Path:

- `skills/codex-wechat-article-republish/`

Purpose:

- make the workflow directly usable in Codex/Claude Code style environments
- keep host-specific instructions thin
- point back to the generic core instead of duplicating business logic

This layer should describe:

- when the tool should trigger the skill
- how to use its own model to generate the Markdown
- how to call this project for dry-run or real upload

## Workflow Boundary

### AI Tool Responsibilities

- understand the source article request
- incorporate user-provided thoughts
- generate a rewritten article in Markdown
- ensure the Markdown follows project constraints:
  - YAML frontmatter
  - title
  - `content_source_url`
  - `cover_image`
  - `{{imageN}}` placeholders

### Project Responsibilities

- fetch and process source images
- validate the generated Markdown
- map placeholders to uploaded images
- render article HTML
- upload permanent materials and submit WeChat draft

## Canonical Execution Flow

1. user provides article URL and optional thoughts
2. skill triggers in the AI tool
3. AI tool reads the generic core skill rules
4. AI tool fetches or reads source material as needed
5. AI tool generates compliant Markdown using its own model
6. AI tool writes the Markdown to a local file
7. AI tool calls this project:

```bash
python3 src/article_pipeline.py upload \
  --url <article_url> \
  --markdown <generated.md>
```

8. recommended first pass uses:

```bash
python3 src/article_pipeline.py upload \
  --url <article_url> \
  --markdown <generated.md> \
  --dry-run \
  --output <dir>
```

9. after inspection, the AI tool may run the real upload

## Generic Skill Content

The core skill should include:

- triggering conditions:
  - WeChat article rewrite
  - publish to WeChat draft box
  - repurpose article from URL
- Markdown contract:
  - required frontmatter fields and defaults
  - image placeholder rules
  - cover image rules
- operational guidance:
  - dry-run before upload when content is new or risky
  - use the project CLI as the deterministic executor
- failure modes:
  - invalid markdown
  - missing image placeholders
  - unresolved cover image
  - WeChat upload failure

## Tool Adapter Content

The adapter skill should be concise and mainly do three things:

1. trigger in the host tool on the right intent
2. tell the host tool to use its own model for article generation
3. direct the host tool to the core skill and the project CLI

The adapter must not:

- restate the full Markdown spec when it can reference the core skill
- hardcode a specific model or provider
- duplicate upload logic

## File Layout

Recommended repo layout:

```text
skills/
  wechat-article-republish/
    SKILL.md
    references/
      markdown-contract.md
      workflow.md
  codex-wechat-article-republish/
    SKILL.md
```

## Validation Strategy

Validation should cover both documentation quality and operational reality.

### Skill-Level Validation

- the core skill clearly defines when it applies
- the core skill clearly defines the Markdown contract
- the adapter skill references the core instead of duplicating rules
- the adapter skill makes the host generate Markdown itself, not by delegating to this project

### Workflow Validation

- run dry-run with a generated Markdown file
- run real upload with a generated Markdown file
- confirm the host tool can follow the documented sequence

### Existing Evidence Reused

- real WeChat draft upload already succeeded through this project
- the Markdown upload path is already covered by tests and runtime verification

## Non-Goals

- building a universal plugin package for every AI IDE in this iteration
- replacing the project CLI with skill-only logic
- turning the repository into a model provider abstraction layer
