# Auto Digest Design

## Goal

Make Markdown draft uploads derive `digest` automatically from body content instead of requiring it in YAML frontmatter.

## Context

The current Markdown draft workflow stores account-level defaults in `wechat.yml` and draft-level metadata in Markdown frontmatter. Requiring `digest` in frontmatter adds friction because the value is already present in the article body and can be inferred deterministically.

## Options Considered

### Option 1: Keep `digest` required in frontmatter

- Pros: explicit and predictable
- Cons: duplicates article content and forces manual entry for every draft

### Option 2: Make `digest` optional and derive it from the first body paragraph

- Pros: minimal authoring burden, deterministic behavior, keeps `wechat.yml` limited to account config
- Cons: summary quality depends on the first paragraph being a good introduction

### Option 3: Generate `digest` from multiple paragraphs or Markdown summary syntax

- Pros: potentially better summaries
- Cons: more parsing rules, more ambiguity, unnecessary for the current workflow

## Decision

Use Option 2.

## Behavior

- `wechat.yml` remains responsible only for account-level settings such as `appid`, `secret`, and default `author`.
- Markdown frontmatter keeps `title`, `cover_image`, and `content_source_url` as the primary draft metadata.
- `digest` becomes optional in frontmatter.
- If `digest` is present and non-empty, keep using it.
- If `digest` is missing, derive it from the first non-empty body paragraph after removing heading lines and image placeholders.
- Paragraph text is normalized by collapsing internal whitespace.
- The derived digest is truncated to a short summary length suitable for WeChat draft metadata.
- If no usable paragraph exists, draft loading should fail with a clear error instead of producing an empty digest.

## Affected Code

- `src/article_drafts.py`
- `tests/test_article_drafts.py`
- `tests/test_article_pipeline.py`

## Testing

- Loading a Markdown draft without `digest` should populate a derived digest from the first paragraph.
- Existing drafts with explicit `digest` should preserve that value.
- Draft loading should fail when the body contains no paragraph text that can be used as a digest.
- CLI dry-run and upload paths should continue to work without requiring `digest` in frontmatter.
