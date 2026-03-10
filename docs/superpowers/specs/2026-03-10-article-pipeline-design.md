# Article Pipeline CLI Design

**Date:** 2026-03-10

**Status:** Approved by user in terminal discussion

## Goal

Create a reusable CLI workflow that can:

1. Analyze images from a WeChat article locally and output a structured report with image artifacts.
2. Reuse the same fetch and watermark-removal pipeline to continue into draft upload.

The CLI must avoid duplicating image-fetch and image-processing logic across analyze and upload modes.

## Current State

- `src/draft_upload.py` contains:
  - config loading
  - token fetching
  - watermark detection and inpainting
  - article image extraction
  - image upload
  - draft upload
  - hardcoded article body generation
- Real article analysis is currently done through ad hoc one-off shell snippets.
- Desktop article fetch can be redirected to a WeChat verification page, while mobile UA fetch succeeds.
- Temporary analysis outputs live in `.tmp/article_tuning/` but there is no supported workflow for generating them.

## Scope

In scope:

- Add a dedicated CLI entrypoint for article analysis and upload
- Prefer mobile-user-agent HTML fetch for article image extraction
- Reuse the same processing path for both analyze and upload modes
- Produce machine-readable and human-readable analysis output
- Keep `src/draft_upload.py` functional by delegating to the new shared module
- Add tests for extraction, analysis output, and dry-run upload behavior

Out of scope:

- Building a general article authoring system
- Replacing WeChat draft assembly content generation
- Removing existing upload functions entirely
- Supporting arbitrary content platforms beyond WeChat articles

## Recommended Approach

Use a module-oriented CLI:

- `src/article_pipeline.py` becomes the CLI entrypoint.
- `src/article_tools.py` becomes the reusable operations module.
- `src/draft_upload.py` remains as a compatibility layer and existing operational script, but delegates shared work into the new module.

This approach keeps the CLI explicit while preventing upload and analysis logic from diverging.

## Alternatives Considered

### Option A: Extend `draft_upload.py` with CLI flags

Pros:

- smallest file count change
- least immediate refactoring

Cons:

- makes an already overloaded file larger
- blends operational upload code with diagnostics workflow
- harder to test in isolation

### Option B: New CLI plus shared module

Pros:

- clean separation between entrypoint and reusable logic
- analyze and upload share exactly one fetch/process path
- easier testing and future tuning

Cons:

- requires moderate extraction from `draft_upload.py`

### Option C: Separate analyze and upload scripts

Pros:

- superficially simple commands

Cons:

- high risk of duplicated logic and drift
- two places to change fetch rules and watermark behavior

## File Structure

### New Files

- `src/article_pipeline.py`
  - parse command-line arguments
  - dispatch to `analyze` or `upload`
  - print terminal summaries

- `src/article_tools.py`
  - article HTML fetch with mobile-first strategy
  - rich-pages image URL extraction
  - image download helpers
  - article image processing loop
  - analysis report generation
  - upload orchestration shared by CLI and legacy script

- `tests/test_article_pipeline.py`
  - focused tests for extraction, analyze outputs, and dry-run upload

### Modified Files

- `src/draft_upload.py`
  - keep watermark utilities
  - call shared article helpers instead of owning the full pipeline

## CLI Design

### Analyze Mode

```bash
python3 src/article_pipeline.py analyze --url <article_url> --output .tmp/article_tuning
```

Supported flags:

- `--url` required
- `--output` optional, default to `.tmp/article_analysis/<timestamp-or-slug>`
- `--save-images` optional, default on for analyze
- `--mobile-fetch` optional, default on
- `--debug-watermark` optional

Behavior:

1. fetch article HTML
2. extract article image URLs
3. download each image
4. run watermark removal
5. write `summary.json`
6. optionally write `*_original`, `*_mask`, `*_clean`
7. print a concise terminal summary

### Upload Mode

```bash
python3 src/article_pipeline.py upload --url <article_url> --limit 5
```

Supported flags:

- `--url` required
- `--limit` optional
- `--dry-run` optional
- `--mobile-fetch` optional, default on
- `--debug-watermark` optional

Behavior:

1. fetch article HTML
2. extract and download images
3. process images using the same analysis pipeline
4. if `--dry-run`, stop after reporting what would be uploaded
5. otherwise upload processed images and continue draft creation

## Data Flow

The shared path must be:

1. `fetch_article_html()`
2. `extract_article_image_urls()`
3. `process_article_images()`

Both analyze and upload must call this same path so tuning applies everywhere.

The output of `process_article_images()` should include per-image metadata:

- index
- source URL
- width and height
- watermark score
- mask pixel count
- changed or unchanged
- diff summary
- status
- error if any
- processed bytes if successful

## Fetch Strategy

Default strategy:

1. fetch article HTML with mobile UA using `requests`
2. extract `rich_pages` image tags
3. keep only article content images

Fallback strategy:

- use Playwright only if HTML extraction fails or if a caller explicitly needs it
- Playwright browser availability must not be required for normal analysis

## Error Handling

### Analyze

- one image failure must not terminate the entire batch
- each image entry records:
  - `status`: `processed`, `unchanged`, `download_failed`, `processing_failed`
  - `error`: message or null

### Upload

- download failure: skip image and continue
- processing failure: keep original bytes and continue
- upload failure: record and continue where possible
- final command summary must report actual counts, not assumed success

## Output Format

Recommended analyze output directory contents:

- `summary.json`
- `01_original.jpg`
- `01_mask.png`
- `01_clean.jpg`

Terminal summary should report:

- total images found
- successfully downloaded
- repaired images count
- unchanged images count
- failed images count

## Testing Strategy

Add tests for:

1. mobile HTML extraction returns article image URLs from rich-pages content
2. analyze mode writes `summary.json`
3. analyze mode continues when one image download fails
4. upload mode supports `--dry-run` without making real WeChat upload requests
5. legacy `draft_upload.py` can still use the shared helpers

Tests should prefer mocked network responses and temporary directories rather than real article fetches.

## Risks

- WeChat article HTML structure can change; extraction must be conservative and easy to update.
- Keeping backward compatibility with `draft_upload.py` may tempt over-coupling if extraction is not cleanly separated.
- Upload behavior still depends on operational config in `wechat.yml`.

## Future Extensions

- add CSV or Markdown summary export for analysis mode
- support passing a local HTML file for offline parser debugging
- optionally expose per-image filtering flags such as `--only-changed`
