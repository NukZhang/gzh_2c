# Markdown Draft Upload Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the article pipeline CLI so upload mode can read a Markdown file with YAML frontmatter and explicit image placeholders, then build and optionally submit a WeChat draft payload.

**Architecture:** Introduce a focused draft assembly module that parses Markdown frontmatter, validates placeholder references, renders controlled HTML, and builds the final WeChat article payload. Keep `article_pipeline.py` as the CLI orchestrator and reuse the shared article processing path plus `draft_upload.py` WeChat API functions.

**Tech Stack:** Python 3, argparse, PyYAML, requests, Pillow, NumPy, OpenCV, pytest

---

## File Structure

- Create: `src/article_drafts.py`
  - Markdown frontmatter parsing
  - placeholder validation and replacement
  - basic Markdown-to-HTML rendering
  - final article payload assembly
- Modify: `src/article_pipeline.py`
  - require `--markdown` for real upload flow
  - support `--output` for dry-run previews
  - orchestrate draft payload generation and optional upload
- Modify: `src/article_tools.py`
  - support image mapping and upload result data needed by draft assembly
- Modify: `src/draft_upload.py`
  - expose WeChat upload helpers for use by the new pipeline path
- Modify: `tests/test_article_pipeline.py`
  - CLI dry-run and upload payload tests
- Create: `tests/test_article_drafts.py`
  - Markdown parsing and payload assembly tests

## Chunk 1: Markdown Parsing and Placeholder Rendering

### Task 1: Add a failing frontmatter parsing test

**Files:**
- Create: `tests/test_article_drafts.py`
- Create: `src/article_drafts.py`

- [ ] **Step 1: Write the failing test**

Add:

```python
def test_load_markdown_draft_parses_frontmatter_and_body():
    draft = load_markdown_draft(path)
    assert draft["meta"]["title"] == "..."
    assert "{{image1}}" in draft["body"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_article_drafts.py::test_load_markdown_draft_parses_frontmatter_and_body -q`
Expected: FAIL because `article_drafts.py` does not exist

- [ ] **Step 3: Write minimal implementation**

Create `src/article_drafts.py` with:

```python
def load_markdown_draft(markdown_path):
    ...

def validate_draft_meta(meta):
    ...
```

The parser should:

- split YAML frontmatter from body
- require `title`, `digest`, `content_source_url`, `cover_image`
- keep the Markdown body unchanged

- [ ] **Step 4: Re-run the test to verify it passes**

Run: `python3 -m pytest tests/test_article_drafts.py::test_load_markdown_draft_parses_frontmatter_and_body -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/article_drafts.py tests/test_article_drafts.py
git commit -m "feat: add markdown draft parser"
```

### Task 2: Add a failing placeholder rendering test

**Files:**
- Modify: `tests/test_article_drafts.py`
- Modify: `src/article_drafts.py`

- [ ] **Step 1: Write the failing test**

Add:

```python
def test_render_markdown_body_replaces_image_placeholders():
    html = render_markdown_body(body, {"image1": "https://..."})
    assert "https://..." in html
    assert "{{image1}}" not in html
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_article_drafts.py::test_render_markdown_body_replaces_image_placeholders -q`
Expected: FAIL because rendering is not implemented yet

- [ ] **Step 3: Write minimal implementation**

Add:

```python
def render_markdown_body(body_markdown, image_map):
    ...
```

Support:

- paragraphs
- headings
- bold text
- ordered/unordered lists
- links
- explicit placeholder replacement for `{{imageN}}`

- [ ] **Step 4: Re-run the test to verify it passes**

Run: `python3 -m pytest tests/test_article_drafts.py::test_render_markdown_body_replaces_image_placeholders -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/article_drafts.py tests/test_article_drafts.py
git commit -m "feat: add markdown placeholder rendering"
```

### Task 3: Add a failing unresolved placeholder test

**Files:**
- Modify: `tests/test_article_drafts.py`
- Modify: `src/article_drafts.py`

- [ ] **Step 1: Write the failing test**

Add:

```python
def test_render_markdown_body_fails_on_unresolved_placeholder():
    with pytest.raises(ValueError):
        render_markdown_body("{{image2}}", {"image1": "https://..."})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_article_drafts.py::test_render_markdown_body_fails_on_unresolved_placeholder -q`
Expected: FAIL because placeholders are not strictly validated yet

- [ ] **Step 3: Write minimal implementation**

Update rendering to:

- detect all `{{imageN}}` references
- error on any missing mapping

- [ ] **Step 4: Re-run the test to verify it passes**

Run: `python3 -m pytest tests/test_article_drafts.py::test_render_markdown_body_fails_on_unresolved_placeholder -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/article_drafts.py tests/test_article_drafts.py
git commit -m "fix: validate markdown image placeholders"
```

## Chunk 2: Payload Assembly

### Task 4: Add a failing payload assembly test

**Files:**
- Modify: `tests/test_article_drafts.py`
- Modify: `src/article_drafts.py`

- [ ] **Step 1: Write the failing test**

Add:

```python
def test_build_article_payload_uses_cover_image_mapping():
    payload = build_article_payload(draft, image_map, thumb_media_id="thumb123", default_author="...")
    assert payload["title"] == "..."
    assert payload["thumb_media_id"] == "thumb123"
    assert payload["author"] == "..."
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_article_drafts.py::test_build_article_payload_uses_cover_image_mapping -q`
Expected: FAIL because payload assembly does not exist yet

- [ ] **Step 3: Write minimal implementation**

Add:

```python
def build_article_payload(draft, rendered_html, thumb_media_id, default_author):
    ...
```

Rules:

- `author` falls back to default when missing
- `thumb_media_id` comes from the selected cover image upload
- `content` is the rendered HTML

- [ ] **Step 4: Re-run the test to verify it passes**

Run: `python3 -m pytest tests/test_article_drafts.py::test_build_article_payload_uses_cover_image_mapping -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/article_drafts.py tests/test_article_drafts.py
git commit -m "feat: add wechat draft payload builder"
```

## Chunk 3: CLI Upload Dry-Run Previews

### Task 5: Add a failing dry-run preview test

**Files:**
- Modify: `tests/test_article_pipeline.py`
- Modify: `src/article_pipeline.py`
- Modify: `src/article_tools.py`
- Modify: `src/article_drafts.py`

- [ ] **Step 1: Write the failing test**

Add:

```python
def test_upload_dry_run_writes_preview_files(tmp_path, monkeypatch):
    ...
    exit_code = main(["upload", "--url", "...", "--markdown", markdown_path, "--dry-run", "--output", str(tmp_path)])
    assert (tmp_path / "body.html").exists()
    assert (tmp_path / "article.json").exists()
    assert (tmp_path / "image_map.json").exists()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_article_pipeline.py::test_upload_dry_run_writes_preview_files -q`
Expected: FAIL because markdown-driven upload preview is not implemented

- [ ] **Step 3: Write minimal implementation**

Update `src/article_pipeline.py` to:

- require `--markdown` for upload mode
- load Markdown draft
- prepare and upload image mappings in dry-run form
- write preview files when `--output` is provided

Add helpers to `src/article_tools.py` if needed for image key mapping.

- [ ] **Step 4: Re-run the test to verify it passes**

Run: `python3 -m pytest tests/test_article_pipeline.py::test_upload_dry_run_writes_preview_files -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/article_pipeline.py src/article_tools.py src/article_drafts.py tests/test_article_pipeline.py
git commit -m "feat: add markdown draft upload dry-run previews"
```

## Chunk 4: Real Upload Payload Flow

### Task 6: Add a failing upload payload orchestration test

**Files:**
- Modify: `tests/test_article_pipeline.py`
- Modify: `src/article_pipeline.py`
- Modify: `src/article_tools.py`

- [ ] **Step 1: Write the failing test**

Add:

```python
def test_upload_mode_builds_and_submits_wechat_draft(monkeypatch, tmp_path):
    ...
    exit_code = main(["upload", "--url", "...", "--markdown", markdown_path])
    assert captured_payload["articles"][0]["title"] == "..."
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_article_pipeline.py::test_upload_mode_builds_and_submits_wechat_draft -q`
Expected: FAIL because the pipeline still stops at image upload

- [ ] **Step 3: Write minimal implementation**

Update upload orchestration to:

- upload processed body images
- resolve `cover_image`
- upload cover image and get `thumb_media_id`
- render body HTML
- build final article payload
- call `draft_upload.upload_draft()`

- [ ] **Step 4: Re-run the test to verify it passes**

Run: `python3 -m pytest tests/test_article_pipeline.py::test_upload_mode_builds_and_submits_wechat_draft -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/article_pipeline.py src/article_tools.py src/article_drafts.py tests/test_article_pipeline.py
git commit -m "feat: create wechat drafts from markdown upload mode"
```

### Task 7: Add a failing cover-image validation test

**Files:**
- Modify: `tests/test_article_drafts.py`
- Modify: `src/article_drafts.py`

- [ ] **Step 1: Write the failing test**

Add:

```python
def test_cover_image_reference_must_exist():
    with pytest.raises(ValueError):
        resolve_cover_image_key({"cover_image": "image3"}, {"image1": "...", "image2": "..."})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_article_drafts.py::test_cover_image_reference_must_exist -q`
Expected: FAIL because cover validation is not strict enough yet

- [ ] **Step 3: Write minimal implementation**

Add strict cover key resolution and clear failure messages.

- [ ] **Step 4: Re-run the test to verify it passes**

Run: `python3 -m pytest tests/test_article_drafts.py::test_cover_image_reference_must_exist -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/article_drafts.py tests/test_article_drafts.py
git commit -m "fix: validate markdown cover image references"
```

## Chunk 5: Final Verification

### Task 8: Run full verification and smoke test the CLI

**Files:**
- Create: `src/article_drafts.py`
- Modify: `src/article_pipeline.py`
- Modify: `src/article_tools.py`
- Modify: `src/draft_upload.py`
- Create: `tests/test_article_drafts.py`
- Modify: `tests/test_article_pipeline.py`

- [ ] **Step 1: Run the full test suite**

Run: `python3 -m pytest tests/test_article_drafts.py tests/test_article_pipeline.py tests/test_draft_upload.py -q`
Expected: all tests pass

- [ ] **Step 2: Run syntax verification**

Run: `python3 -m py_compile src/article_drafts.py src/article_tools.py src/article_pipeline.py src/draft_upload.py tests/test_article_drafts.py tests/test_article_pipeline.py tests/test_draft_upload.py`
Expected: exit code 0

- [ ] **Step 3: Run a real dry-run smoke**

Run:

```bash
python3 src/article_pipeline.py upload \
  --url https://mp.weixin.qq.com/s/101JT4crNZbak8zF9g2rdA \
  --markdown path/to/article.md \
  --dry-run \
  --output .tmp/markdown_upload_smoke
```

Expected:

- command exits 0
- `.tmp/markdown_upload_smoke/body.html` exists
- `.tmp/markdown_upload_smoke/article.json` exists
- `.tmp/markdown_upload_smoke/image_map.json` exists

- [ ] **Step 4: Commit the completed implementation**

```bash
git add src/article_drafts.py src/article_tools.py src/article_pipeline.py src/draft_upload.py tests/test_article_drafts.py tests/test_article_pipeline.py tests/test_draft_upload.py
git commit -m "feat: add markdown-driven wechat draft upload"
```
