# Article Pipeline CLI Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable CLI that can analyze images from a WeChat article and reuse the same fetch/process pipeline for draft upload.

**Architecture:** Introduce a new shared module for article fetch, image extraction, batch processing, and optional upload orchestration. Keep `src/article_pipeline.py` as the CLI surface and shrink `src/draft_upload.py` into a compatibility layer that reuses the shared module instead of owning the full workflow.

**Tech Stack:** Python 3, argparse, requests, Pillow, NumPy, OpenCV, pytest

---

## File Structure

- Create: `src/article_tools.py`
  - Shared fetch, extraction, image processing, analysis report, and upload orchestration helpers.
- Create: `src/article_pipeline.py`
  - CLI argument parsing and mode dispatch for `analyze` and `upload`.
- Modify: `src/draft_upload.py`
  - Delegate article fetch/process/upload work to the shared module while preserving current watermark utilities.
- Create: `tests/test_article_pipeline.py`
  - Tests for HTML extraction, analyze output, per-image failure handling, dry-run upload, and legacy compatibility.

## Chunk 1: Shared HTML Extraction and Processing Skeleton

### Task 1: Add the first failing parser test

**Files:**
- Create: `tests/test_article_pipeline.py`
- Test: `tests/test_article_pipeline.py`

- [ ] **Step 1: Write the failing test**

Add a test for mobile HTML extraction:

```python
def test_extract_article_image_urls_prefers_rich_pages_images():
    html = \"\"\"...rich_pages img tags...\"\"\"
    urls = extract_article_image_urls(html)
    assert urls == [expected_1, expected_2]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_article_pipeline.py::test_extract_article_image_urls_prefers_rich_pages_images -q`
Expected: FAIL because `article_tools.py` and the helper do not exist yet

- [ ] **Step 3: Write minimal implementation**

Create `src/article_tools.py` with:

```python
MOBILE_UA = "..."

def fetch_article_html(article_url, session=None, user_agent=None):
    ...

def extract_article_image_urls(html):
    ...
```

The extractor should only keep `rich_pages` images with `mmbiz` URLs.

- [ ] **Step 4: Re-run the test to verify it passes**

Run: `python3 -m pytest tests/test_article_pipeline.py::test_extract_article_image_urls_prefers_rich_pages_images -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/article_tools.py tests/test_article_pipeline.py
git commit -m "feat: add article image extraction helpers"
```

### Task 2: Add a failing test for batch image processing metadata

**Files:**
- Modify: `tests/test_article_pipeline.py`
- Modify: `src/article_tools.py`

- [ ] **Step 1: Write the failing test**

Add a test for:

```python
def test_process_article_images_returns_per_image_summary(tmp_path):
    result = process_article_images([...], output_dir=tmp_path, save_images=True)
    assert result["images"][0]["status"] == "processed"
    assert (tmp_path / "01_original.jpg").exists()
    assert (tmp_path / "01_mask.png").exists()
    assert (tmp_path / "01_clean.jpg").exists()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_article_pipeline.py::test_process_article_images_returns_per_image_summary -q`
Expected: FAIL because the batch processor does not exist yet

- [ ] **Step 3: Write minimal implementation**

Add to `src/article_tools.py`:

```python
def download_image(image_url, session=None, timeout=20):
    ...

def process_article_images(image_urls, output_dir=None, save_images=False, process_image_fn=None):
    ...
```

The function should:

- download each image
- call watermark processing
- record per-image status fields
- optionally save artifacts

- [ ] **Step 4: Re-run the test to verify it passes**

Run: `python3 -m pytest tests/test_article_pipeline.py::test_process_article_images_returns_per_image_summary -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/article_tools.py tests/test_article_pipeline.py
git commit -m "feat: add article image batch processor"
```

## Chunk 2: CLI Analyze Mode

### Task 3: Add a failing CLI analyze test

**Files:**
- Modify: `tests/test_article_pipeline.py`
- Create: `src/article_pipeline.py`
- Modify: `src/article_tools.py`

- [ ] **Step 1: Write the failing test**

Add a CLI test:

```python
def test_article_pipeline_analyze_writes_summary_json(tmp_path, monkeypatch):
    ...
    exit_code = main([...])
    assert exit_code == 0
    assert (tmp_path / "summary.json").exists()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_article_pipeline.py::test_article_pipeline_analyze_writes_summary_json -q`
Expected: FAIL because the CLI entrypoint does not exist yet

- [ ] **Step 3: Write minimal implementation**

Create `src/article_pipeline.py` with:

```python
def build_parser():
    ...

def run_analyze(args):
    ...

def main(argv=None):
    ...
```

Add summary writing in `article_tools.py`:

```python
def analyze_article(article_url, output_dir, save_images=True, session=None):
    ...
```

- [ ] **Step 4: Re-run the test to verify it passes**

Run: `python3 -m pytest tests/test_article_pipeline.py::test_article_pipeline_analyze_writes_summary_json -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/article_pipeline.py src/article_tools.py tests/test_article_pipeline.py
git commit -m "feat: add article analyze cli"
```

### Task 4: Add a failing resilience test for per-image download errors

**Files:**
- Modify: `tests/test_article_pipeline.py`
- Modify: `src/article_tools.py`

- [ ] **Step 1: Write the failing test**

Add:

```python
def test_analyze_article_continues_when_one_image_download_fails(tmp_path):
    ...
    assert summary["images"][1]["status"] == "download_failed"
    assert summary["images"][2]["status"] in {"processed", "unchanged"}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_article_pipeline.py::test_analyze_article_continues_when_one_image_download_fails -q`
Expected: FAIL because the current batch path aborts on a per-image error

- [ ] **Step 3: Write minimal implementation**

Update `process_article_images()` to:

- catch download exceptions per image
- record `status` and `error`
- continue processing later images

- [ ] **Step 4: Re-run the test to verify it passes**

Run: `python3 -m pytest tests/test_article_pipeline.py::test_analyze_article_continues_when_one_image_download_fails -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/article_tools.py tests/test_article_pipeline.py
git commit -m "fix: keep article analysis running on image failures"
```

## Chunk 3: Upload Mode and Legacy Compatibility

### Task 5: Add a failing dry-run upload test

**Files:**
- Modify: `tests/test_article_pipeline.py`
- Modify: `src/article_pipeline.py`
- Modify: `src/article_tools.py`

- [ ] **Step 1: Write the failing test**

Add:

```python
def test_article_pipeline_upload_dry_run_skips_wechat_upload(monkeypatch):
    ...
    exit_code = main(["upload", "--url", "...", "--dry-run"])
    assert exit_code == 0
    assert upload_calls == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_article_pipeline.py::test_article_pipeline_upload_dry_run_skips_wechat_upload -q`
Expected: FAIL because upload mode is not implemented yet

- [ ] **Step 3: Write minimal implementation**

Add to `article_tools.py`:

```python
def upload_article_images(..., dry_run=False):
    ...
```

Add to `article_pipeline.py`:

```python
def run_upload(args):
    ...
```

Dry-run should:

- fetch article HTML
- extract image URLs
- process images
- print what would be uploaded
- avoid real WeChat upload calls

- [ ] **Step 4: Re-run the test to verify it passes**

Run: `python3 -m pytest tests/test_article_pipeline.py::test_article_pipeline_upload_dry_run_skips_wechat_upload -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/article_pipeline.py src/article_tools.py tests/test_article_pipeline.py
git commit -m "feat: add article upload dry-run mode"
```

### Task 6: Add a failing legacy compatibility test

**Files:**
- Modify: `tests/test_article_pipeline.py`
- Modify: `src/draft_upload.py`
- Modify: `src/article_tools.py`

- [ ] **Step 1: Write the failing test**

Add a compatibility test proving legacy fetch delegates to the shared module:

```python
def test_legacy_fetch_article_images_uses_shared_extractor(monkeypatch):
    ...
    assert draft_upload.fetch_article_images("https://...") == expected_urls
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_article_pipeline.py::test_legacy_fetch_article_images_uses_shared_extractor -q`
Expected: FAIL because the legacy script still owns its own fetch logic

- [ ] **Step 3: Write minimal implementation**

Update `src/draft_upload.py` so `fetch_article_images()` and any shared article processing path call into `article_tools.py` instead of duplicating the extraction path.

- [ ] **Step 4: Re-run the test to verify it passes**

Run: `python3 -m pytest tests/test_article_pipeline.py::test_legacy_fetch_article_images_uses_shared_extractor -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/draft_upload.py src/article_tools.py tests/test_article_pipeline.py
git commit -m "refactor: route legacy article fetch through shared tools"
```

## Chunk 4: Final Verification

### Task 7: Run full verification and inspect actual outputs

**Files:**
- Create: `src/article_tools.py`
- Create: `src/article_pipeline.py`
- Modify: `src/draft_upload.py`
- Create: `tests/test_article_pipeline.py`

- [ ] **Step 1: Run the article pipeline tests**

Run: `python3 -m pytest tests/test_article_pipeline.py tests/test_draft_upload.py -q`
Expected: all tests pass

- [ ] **Step 2: Run syntax verification**

Run: `python3 -m py_compile src/article_tools.py src/article_pipeline.py src/draft_upload.py tests/test_article_pipeline.py tests/test_draft_upload.py`
Expected: exit code 0

- [ ] **Step 3: Run one dry-run analyze command locally**

Run:

```bash
python3 src/article_pipeline.py analyze --url https://mp.weixin.qq.com/s/101JT4crNZbak8zF9g2rdA --output .tmp/article_pipeline_smoke
```

Expected:

- command exits 0
- `.tmp/article_pipeline_smoke/summary.json` exists
- terminal prints real counts

- [ ] **Step 4: Commit the completed implementation**

```bash
git add src/article_tools.py src/article_pipeline.py src/draft_upload.py tests/test_article_pipeline.py
git commit -m "feat: add reusable article pipeline cli"
```
