# Markdown Meta Defaults Design

## Goal

Reduce required Markdown frontmatter for draft uploads by auto-deriving deterministic metadata while keeping `title` explicitly provided by the calling AI.

## Context

The current Markdown upload flow already derives `digest` from the first body paragraph when omitted. The remaining required frontmatter fields are `title`, `cover_image`, and `content_source_url`. The user wants the project to behave like a skill invoked by an AI CLI: the AI should decide semantic fields such as `title`, while the script should infer deterministic fields on its own.

## Options Considered

### Option 1: Keep all metadata explicit in frontmatter

- Pros: simple validation rules
- Cons: duplicates information the script can derive deterministically

### Option 2: Derive deterministic fields and keep `title` required

- Pros: aligns with AI-CLI workflow, minimizes manual metadata, keeps semantic decisions outside the script
- Cons: requires a small amount of normalization logic during draft loading

### Option 3: Derive everything, including `title`

- Pros: maximum automation
- Cons: pushes semantic generation into the script, which conflicts with the intended AI-skill integration boundary

## Decision

Use Option 2.

## Behavior

- `title`
  - If present in frontmatter, use it.
  - If missing, fail early with an error telling the caller to let AI fill `title` first.
- `digest`
  - If present in frontmatter, use it.
  - If missing, derive it from the first non-empty paragraph after ignoring headings and image placeholders.
- `cover_image`
  - If present in frontmatter, use it.
  - If missing, derive it from the first `{{imageN}}` placeholder in the body.
- `content_source_url`
  - If present in frontmatter, use it.
  - If missing, fall back to the CLI `--url` value.
- All derivation and validation happen while loading the Markdown draft, before image uploads or WeChat API calls.

## Affected Code

- `src/article_drafts.py`
- `src/article_pipeline.py`
- `tests/test_article_drafts.py`
- `tests/test_article_pipeline.py`

## Testing

- Draft loading should derive `cover_image` from the first image placeholder.
- Draft loading should fall back to the CLI article URL when `content_source_url` is omitted.
- Draft loading should fail with a clear AI-oriented message when `title` is missing.
- `upload --dry-run` should work with Markdown files that only provide `title`.
