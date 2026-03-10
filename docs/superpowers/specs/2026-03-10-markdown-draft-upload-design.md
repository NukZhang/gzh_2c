# Markdown Draft Upload Design

**Date:** 2026-03-10

**Status:** Approved by user in terminal discussion

## Goal

Extend the reusable article pipeline CLI so `upload` can create a WeChat draft from a local Markdown file instead of relying on hardcoded article content in `src/draft_upload.py`.

The Markdown format must support:

- YAML frontmatter
- explicit image placeholders such as `{{image1}}`
- explicit cover selection through frontmatter

## Current State

- `src/article_pipeline.py` supports:
  - `analyze`
  - `upload --dry-run` that only fetches and processes article images
- `src/article_tools.py` supports:
  - mobile-first article HTML fetch
  - rich-pages image extraction
  - batch image processing
  - upload preparation
- `src/draft_upload.py` still contains:
  - WeChat config loading
  - token retrieval
  - image upload
  - draft upload
  - hardcoded article title, body, and digest

The missing piece is a reusable path from Markdown source file to WeChat draft payload.

## Scope

In scope:

- add Markdown-driven draft assembly
- require YAML frontmatter for draft metadata
- support explicit `{{imageN}}` placeholders
- support explicit `cover_image` frontmatter selection
- support `upload --dry-run --output <dir>` to preview generated payload and HTML
- reuse processed and uploaded image mappings for body and cover selection

Out of scope:

- rich Markdown extension ecosystem
- arbitrary custom HTML blocks
- templating beyond image placeholders
- auto-generating article copy from source material

## Recommended Approach

Add a dedicated Markdown draft assembly module:

- `src/article_drafts.py`
  - parse frontmatter
  - validate required fields
  - render basic Markdown to HTML
  - replace image placeholders with uploaded WeChat image URLs
  - build the final article payload

Use `src/article_pipeline.py` to orchestrate:

1. read Markdown draft file
2. fetch and process article images
3. upload processed images
4. render article HTML
5. upload the selected cover image
6. submit the draft payload unless `--dry-run`

This isolates Markdown and payload concerns from fetch and watermark-processing logic.

## Alternatives Considered

### Option A: Put Markdown parsing directly in `article_pipeline.py`

Pros:

- smallest file count increase

Cons:

- CLI file grows too quickly
- hard to test rendering logic independently

### Option B: Add a dedicated Markdown draft module

Pros:

- clear separation of concerns
- direct unit testing of parsing and placeholder replacement
- easiest to extend later

Cons:

- one more source file

### Option C: Reuse `draft_upload.py` as the draft builder

Pros:

- fewer immediate imports

Cons:

- continues coupling legacy operational code to new CLI behavior
- keeps hardcoded content history close to new behavior

## Markdown Format

Example:

```md
---
title: OpenClaw 安装指南
digest: 一篇关于 OpenClaw 安装和 Skills 使用的整理
content_source_url: https://mp.weixin.qq.com/s/101JT4crNZbak8zF9g2rdA
author: 老张
cover_image: image2
---

开头段落。

{{image1}}

第二段正文。

{{image2}}
```

### Frontmatter Rules

Required:

- `title`
- `digest`
- `content_source_url`
- `cover_image`

Optional:

- `author`

Behavior:

- if `author` is missing, fall back to `wechat.yml`
- `cover_image` must point to a placeholder key such as `image1`

## Rendering Rules

### Supported Markdown

Initial support:

- paragraphs
- headings
- bold text
- unordered lists
- ordered lists
- links

Not required in the first implementation:

- tables
- code fences with syntax highlighting
- nested block extensions

### Image Placeholder Replacement

Body placeholders use explicit keys:

- `{{image1}}`
- `{{image2}}`

Replacement rule:

- each placeholder must map to a successfully uploaded image URL
- unresolved placeholders are fatal errors

Rendered image HTML should use controlled inline styles suitable for WeChat article content.

## CLI Changes

Extend upload mode:

```bash
python3 src/article_pipeline.py upload \
  --url <article_url> \
  --markdown <article.md> \
  --limit 5
```

### New/Updated Flags

- `--markdown` required for real upload mode
- `--dry-run` optional
- `--output` optional for dry-run artifacts
- `--limit` optional

### Upload Execution Flow

1. read and parse Markdown file
2. fetch and process article images
3. upload body images to WeChat
4. build image key mapping (`image1` -> uploaded URL)
5. render body HTML with placeholder replacement
6. resolve `cover_image` to the uploaded image bytes or mapping
7. upload cover image and get `thumb_media_id`
8. build the final article payload
9. call WeChat draft API unless `--dry-run`

## Dry-Run Behavior

When `--dry-run` is enabled:

- do all steps except the actual WeChat upload calls
- write preview artifacts if `--output` is supplied:
  - `body.html`
  - `article.json`
  - `image_map.json`

This mode exists to validate Markdown structure and placeholder coverage before touching the WeChat account.

## Error Handling

Fatal errors:

- missing frontmatter
- missing required frontmatter fields
- invalid `cover_image`
- unresolved image placeholder
- trying to upload without `--markdown`

Recoverable errors:

- article image processing failures remain per-image and use existing batch summary rules

If a Markdown placeholder references an image that failed processing or upload, upload mode must stop with a clear error instead of silently omitting the image.

## Testing Strategy

Add tests for:

1. frontmatter parsing and required field validation
2. placeholder replacement success
3. unresolved placeholder failure
4. `cover_image` selection validation
5. `upload --dry-run` writes preview files without real WeChat upload
6. CLI upload path builds the expected article payload

## Risks

- Basic Markdown rendering without a mature parser can drift from expected formatting if implemented too loosely.
- Placeholder references create a strict coupling between article image order and Markdown body references.
- Real upload depends on operational config and network access to WeChat APIs.

## Future Extensions

- support local image placeholders in Markdown
- support reusable WeChat article style presets
- add richer Markdown rendering if authors need tables or code blocks
