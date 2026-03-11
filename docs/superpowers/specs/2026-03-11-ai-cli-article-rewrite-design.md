# AI CLI Article Rewrite Design

**Date:** 2026-03-11

**Status:** Approved by user in terminal discussion

## Goal

Extend the existing WeChat article upload pipeline so the project can accept a source article URL plus optional user thoughts, call a local AI CLI for rewrite generation, and submit the generated article to the WeChat draft box.

The design must preserve the current Markdown-driven upload path and add the smallest viable bridge from source material to generated Markdown.

## Current State

- `src/article_pipeline.py` already supports:
  - `analyze`
  - `upload --markdown <file>`
  - `upload --dry-run`
- `src/article_drafts.py` already supports:
  - YAML frontmatter parsing
  - derived `digest`
  - derived `cover_image`
  - placeholder validation and HTML rendering
- `src/article_tools.py` already supports:
  - fetching article HTML
  - extracting article image URLs
  - downloading and processing article images
  - building uploaded image mappings
- `src/draft_upload.py` already supports:
  - WeChat config loading
  - access token retrieval
  - permanent image upload
  - draft submission

Missing pieces:

- source article title and body extraction
- conversion of source content into rewrite-ready material
- local AI CLI orchestration
- validation of AI-generated Markdown before upload
- `upload` mode that works without a prewritten Markdown file

## Constraints

- Reuse the current Python stack and project structure.
- Do not add third-party dependencies unless already present.
- Preserve the current `--markdown` upload behavior.
- Use the local AI CLI as the generation engine instead of adding an SDK integration.
- Keep the upload path deterministic after Markdown has been generated.

## Options Considered

### Option 1: Add a local AI CLI bridge inside the existing upload pipeline

Pros:

- matches the user's requested workflow
- avoids adding SDK dependencies
- keeps generation and upload boundaries explicit
- reuses the existing Markdown upload path

Cons:

- requires a stable CLI contract
- adds validation needs around generated Markdown

### Option 2: Bind the project to one model SDK directly

Pros:

- easier request/response handling
- less shell orchestration

Cons:

- conflicts with the requirement to rely on AI CLI model capability
- likely requires new dependencies and account-specific code

### Option 3: Continue requiring external Markdown authoring

Pros:

- smallest code change

Cons:

- does not satisfy the requested link-to-draft workflow

## Decision

Use Option 1.

The project will extract source material locally, build an AI prompt from the source article plus optional user thoughts plus `spec/Me2AI/人设.md`, call a configurable local AI CLI, validate the generated Markdown, and then reuse the existing upload pipeline.

## Architecture

Add two focused modules and keep `src/article_pipeline.py` as the orchestrator:

- `src/article_source.py`
  - fetch-free parsing helpers for source article title, body blocks, and image placeholder ordering
  - convert source HTML into rewrite-ready structured data
- `src/ai_rewrite.py`
  - read persona/rule text from `spec/Me2AI/人设.md`
  - build the prompt from source content and user thoughts
  - invoke a configurable local AI CLI
  - validate the returned Markdown draft
- `src/article_pipeline.py`
  - preserve current `--markdown` path
  - add automatic generation path driven by `--thought` or `--thought-file`
  - continue reusing `article_drafts.py`, `article_tools.py`, and `draft_upload.py`

## Source Extraction

The extractor only needs stable content primitives, not full DOM fidelity.

Inputs:

- fetched article HTML from `article_tools.fetch_article_html()`

Outputs:

- source article title
- ordered body blocks
  - paragraphs
  - level-2 headings when present
  - image placeholders in source order
- source image key list, aligned with existing `image1`, `image2`, ... convention

Extraction rules:

- prefer `var msg_title = '...'` when present
- fall back to `og:title`
- use the `#js_content` container as the source body
- keep only text-bearing blocks and rich-pages images
- normalize whitespace
- emit `{{imageN}}` placeholders in article order
- ignore unsupported embeds and decorative wrapper markup

This gives the AI a stable, text-first representation without needing a general-purpose HTML rendering engine.

## AI CLI Contract

The generation path will call a local shell command configured by:

1. CLI flag `--ai-command`
2. environment variable `ARTICLE_AI_COMMAND`

The command is treated as the executable prefix. The project writes the prompt to stdin and reads Markdown from stdout.

Prompt inputs:

- source article title
- normalized source body with `{{imageN}}` placeholders
- optional user thoughts
- persona and style requirements from `spec/Me2AI/人设.md`
- output schema requirements

Required output:

```md
---
title: ...
content_source_url: ...
cover_image: imageN
---

正文...
```

Rules enforced on the generated Markdown:

- must include YAML frontmatter
- must contain `title`
- body must contain real text for digest derivation
- any referenced placeholder must be of form `{{imageN}}`
- cover image must resolve to an available placeholder after normalization

`digest` remains optional because the existing draft loader already derives it.

## CLI Changes

Keep the `upload` subcommand and add a second input mode.

Supported modes:

- existing Markdown mode
  - `upload --url <url> --markdown <draft.md>`
- automatic rewrite mode
  - `upload --url <url> --thought "..." [--ai-command "..."]`
  - `upload --url <url> --thought-file <notes.txt> [--ai-command "..."]`

Rules:

- `--markdown` is mutually exclusive with `--thought` and `--thought-file`
- `--thought` and `--thought-file` are mutually exclusive
- if no Markdown source and no thought source are supplied, fail early
- empty thought text is allowed and means rewrite from source only

## Upload Flow

Automatic rewrite mode runs:

1. fetch article HTML
2. extract structured source content
3. build prompt from source content, persona, and thought text
4. call AI CLI and obtain Markdown draft
5. parse and validate generated draft
6. fetch and process source images
7. map uploaded images into generated placeholders
8. render final HTML
9. upload cover image
10. submit WeChat draft unless `--dry-run`

Markdown mode continues to skip steps 2 to 4 and reuse the current behavior.

## Dry-Run Behavior

In automatic rewrite mode, `--dry-run --output <dir>` should write:

- `source.json`
- `prompt.txt`
- `generated.md`
- `body.html`
- `article.json`
- `image_map.json`

This preserves a fully inspectable trail before any WeChat API calls.

In Markdown mode, existing dry-run artifacts remain unchanged.

## Error Handling

Fatal errors:

- article fetch failure
- title extraction failure
- empty or invalid extracted body
- missing AI CLI configuration
- AI CLI non-zero exit status
- empty AI CLI output
- invalid generated Markdown structure
- unresolved placeholders in generated body
- cover image that does not resolve

Recoverable errors:

- individual source image download failures remain governed by existing per-image handling
- source blocks unsupported by the extractor are omitted rather than failing the run

## Testing Strategy

Add focused unit coverage:

- `tests/test_article_source.py`
  - title extraction
  - body extraction
  - source placeholder ordering
  - failure on empty source text
- `tests/test_ai_rewrite.py`
  - prompt includes source content, persona, and user thought
  - command invocation uses stdin/stdout contract
  - non-zero exit handling
  - Markdown validation failures
- `tests/test_article_pipeline.py`
  - automatic rewrite dry-run path
  - automatic rewrite upload orchestration
  - argument exclusivity errors
  - current Markdown path regression coverage remains green

## Validation Evidence

The implementation should be verified with:

- targeted pytest commands for new modules
- full test suite
- `py_compile`
- a dry-run using the user-provided source article URL

Observed during design:

- the provided URL `https://mp.weixin.qq.com/s/101JT4crNZbak8zF9g2rdA` returns HTTP 200 with accessible article HTML
- the page contains both `var msg_title = ...` and `id="js_content"` markers, which are sufficient for the planned extractor

## Non-Goals

- general-purpose HTML to Markdown conversion
- arbitrary embedded widget preservation
- automatic publish
- multi-platform syndication
- model SDK integrations
