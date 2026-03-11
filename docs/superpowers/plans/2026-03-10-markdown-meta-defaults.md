# Markdown Meta Defaults Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-derive `cover_image` and `content_source_url` for Markdown draft uploads while keeping `title` explicitly required from the calling AI.

**Architecture:** Keep metadata normalization in `src/article_drafts.py` so all draft consumers share one path. `src/article_pipeline.py` will pass the article URL as fallback metadata, and tests will prove the new defaults and error messaging through unit and CLI dry-run coverage.

**Tech Stack:** Python, PyYAML, pytest

---

## Chunk 1: Draft Normalization Rules

### Task 1: Cover metadata defaults in unit tests

**Files:**
- Modify: `tests/test_article_drafts.py`
- Test: `tests/test_article_drafts.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_load_markdown_draft_derives_cover_image_from_first_placeholder(tmp_path):
    ...

def test_load_markdown_draft_uses_fallback_source_url(tmp_path):
    ...

def test_load_markdown_draft_requires_title_from_ai(tmp_path):
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_article_drafts.py -q`
Expected: FAIL because `cover_image` and `content_source_url` are still required in frontmatter and the title error message is generic.

- [ ] **Step 3: Write minimal implementation**

```python
def _derive_cover_image(body_markdown):
    ...

def _normalize_draft_meta(meta, body_markdown, fallback_source_url=None):
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_article_drafts.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_article_drafts.py src/article_drafts.py
git commit -m "feat: derive markdown draft metadata defaults"
```

## Chunk 2: CLI Regression

### Task 2: Pass article URL fallback through upload flow

**Files:**
- Modify: `tests/test_article_pipeline.py`
- Modify: `src/article_pipeline.py`
- Test: `tests/test_article_pipeline.py`

- [ ] **Step 1: Write the failing regression tests**

```python
def test_upload_dry_run_accepts_markdown_without_cover_image_or_source_url(...):
    ...

def test_upload_requires_title_from_markdown_or_ai(...):
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_article_pipeline.py -q`
Expected: FAIL because the fallback URL is not passed into draft loading and the title validation message is not specific enough.

- [ ] **Step 3: Write minimal implementation**

```python
draft = article_drafts.load_markdown_draft(args.markdown, fallback_source_url=args.url)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_article_pipeline.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_article_pipeline.py src/article_pipeline.py
git commit -m "test: cover markdown upload metadata defaults"
```

## Chunk 3: Verification

### Task 3: Fresh verification and smoke run

**Files:**
- Modify: `none`
- Test: `tests/test_article_drafts.py`
- Test: `tests/test_article_pipeline.py`

- [ ] **Step 1: Run focused suites**

Run: `python3 -m pytest tests/test_article_drafts.py tests/test_article_pipeline.py -q`
Expected: PASS

- [ ] **Step 2: Run syntax verification**

Run: `python3 -m py_compile src/article_drafts.py src/article_pipeline.py tests/test_article_drafts.py tests/test_article_pipeline.py`
Expected: PASS

- [ ] **Step 3: Run a dry-run smoke command**

Run: `python3 src/article_pipeline.py upload --url "https://mp.weixin.qq.com/s/101JT4crNZbak8zF9g2rdA" --markdown .tmp/auto_meta_smoke.md --dry-run --output .tmp/auto_meta_smoke_output`
Expected: PASS with generated preview files and derived metadata.
