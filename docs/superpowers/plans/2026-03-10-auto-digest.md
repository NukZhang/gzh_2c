# Auto Digest Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Markdown draft uploads derive `digest` from the first body paragraph when frontmatter omits it.

**Architecture:** Keep the change localized to `article_drafts.py`. Draft loading will normalize metadata after parsing frontmatter, derive `digest` from body text when needed, and reuse the resulting draft object in existing CLI upload flows. Tests cover parser behavior first, then CLI regression.

**Tech Stack:** Python, PyYAML, pytest

---

## Chunk 1: Parser Behavior

### Task 1: Cover derived digest in unit tests

**Files:**
- Modify: `tests/test_article_drafts.py`
- Test: `tests/test_article_drafts.py`

- [ ] **Step 1: Write the failing test**

```python
def test_load_markdown_draft_derives_digest_from_first_paragraph(tmp_path):
    ...
    assert draft["meta"]["digest"] == "第一段正文。"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_article_drafts.py::test_load_markdown_draft_derives_digest_from_first_paragraph -q`
Expected: FAIL because `digest` is still required in frontmatter.

- [ ] **Step 3: Write minimal implementation**

```python
def derive_digest(body_markdown):
    ...

def normalize_draft_meta(meta, body_markdown):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_article_drafts.py::test_load_markdown_draft_derives_digest_from_first_paragraph -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_article_drafts.py src/article_drafts.py
git commit -m "feat: derive digest from markdown body"
```

### Task 2: Keep explicit digest and fail on missing paragraph text

**Files:**
- Modify: `tests/test_article_drafts.py`
- Modify: `src/article_drafts.py`
- Test: `tests/test_article_drafts.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_load_markdown_draft_prefers_explicit_digest(tmp_path):
    ...

def test_load_markdown_draft_requires_body_text_for_digest(tmp_path):
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_article_drafts.py -q`
Expected: FAIL on the new expectations.

- [ ] **Step 3: Write minimal implementation**

```python
if meta.get("digest"):
    return meta["digest"]
raise ValueError(...)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_article_drafts.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_article_drafts.py src/article_drafts.py
git commit -m "test: cover markdown digest fallback rules"
```

## Chunk 2: CLI Regression

### Task 3: Prove upload flows work without frontmatter digest

**Files:**
- Modify: `tests/test_article_pipeline.py`
- Test: `tests/test_article_pipeline.py`

- [ ] **Step 1: Write the failing regression test**

```python
def test_upload_dry_run_accepts_markdown_without_digest(tmp_path, monkeypatch):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_article_pipeline.py::test_upload_dry_run_accepts_markdown_without_digest -q`
Expected: FAIL because draft loading rejects the Markdown file.

- [ ] **Step 3: Reuse the parser change without new CLI logic**

```python
# No CLI-specific implementation should be needed once draft parsing is fixed.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_article_pipeline.py::test_upload_dry_run_accepts_markdown_without_digest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_article_pipeline.py
git commit -m "test: cover upload markdown digest fallback"
```

## Chunk 3: Verification

### Task 4: Run focused regression checks

**Files:**
- Modify: `none`
- Test: `tests/test_article_drafts.py`
- Test: `tests/test_article_pipeline.py`

- [ ] **Step 1: Run targeted suites**

Run: `python3 -m pytest tests/test_article_drafts.py tests/test_article_pipeline.py -q`
Expected: PASS

- [ ] **Step 2: Run syntax verification**

Run: `python3 -m py_compile src/article_drafts.py src/article_pipeline.py tests/test_article_drafts.py tests/test_article_pipeline.py`
Expected: PASS

- [ ] **Step 3: Commit if needed**

```bash
git status --short
```
