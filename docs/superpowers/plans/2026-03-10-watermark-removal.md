# Watermark Removal Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace crop-based watermark handling with local watermark detection plus OpenCV inpainting while preserving original image dimensions.

**Architecture:** Keep the change centered in `src/draft_upload.py`, but split the image workflow into small helper functions for loading, ROI detection, candidate scoring, mask generation, and inpainting. Add focused tests that synthesize watermark-like images so the behavior can be verified without external fixtures.

**Tech Stack:** Python 3, Pillow, NumPy, OpenCV, pytest, requests, Playwright

---

## File Structure

- Modify: `src/draft_upload.py`
  - Replace crop-based watermark detection and fallback logic with ROI-based detection plus inpainting helpers.
- Create: `tests/test_draft_upload.py`
  - Add synthetic image tests for watermark detection and non-destructive fallback behavior.
- Create: `requirements.txt`
  - Document runtime and test dependencies, including `opencv-python` and `pytest`.

## Chunk 1: Dependency and Test Harness Setup

### Task 1: Add a minimal Python dependency manifest

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: Write the failing test harness expectation**

Document the command that should become runnable after setup:

```bash
pytest tests/test_draft_upload.py -q
```

- [ ] **Step 2: Run setup verification to confirm it currently fails**

Run: `python3 -m pytest tests/test_draft_upload.py -q`
Expected: FAIL because `pytest` and/or `tests/test_draft_upload.py` is missing

- [ ] **Step 3: Add the dependency manifest**

Create `requirements.txt` with the packages already used by the script plus new needs:

```text
requests
PyYAML
numpy
Pillow
playwright
opencv-python
pytest
```

- [ ] **Step 4: Install dependencies locally if needed**

Run: `python3 -m pip install -r requirements.txt`
Expected: dependencies install without resolution errors

- [ ] **Step 5: Commit**

```bash
git add requirements.txt
git commit -m "build: add python dependency manifest"
```

## Chunk 2: Watermark Detection and Repair Tests

### Task 2: Add a failing test for semi-transparent watermark cleanup

**Files:**
- Create: `tests/test_draft_upload.py`
- Test: `tests/test_draft_upload.py`

- [ ] **Step 1: Write the failing test**

Add a synthetic test image with a bright semi-transparent lower-right watermark block and assert:

```python
def test_remove_watermark_preserves_size_and_changes_watermarked_region():
    ...
    assert cleaned_image.size == source_image.size
    assert roi_difference > 0
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_draft_upload.py::test_remove_watermark_preserves_size_and_changes_watermarked_region -q`
Expected: FAIL because the helper behavior does not exist yet or still crops destructively

- [ ] **Step 3: Write minimal implementation**

Implement only enough code in `src/draft_upload.py` to preserve image size and apply local repair for the synthetic watermark case.

- [ ] **Step 4: Re-run the test to verify it passes**

Run: `python3 -m pytest tests/test_draft_upload.py::test_remove_watermark_preserves_size_and_changes_watermarked_region -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_draft_upload.py src/draft_upload.py
git commit -m "test: cover semi-transparent watermark cleanup"
```

### Task 3: Add a failing test for QR-like badge cleanup

**Files:**
- Modify: `tests/test_draft_upload.py`
- Modify: `src/draft_upload.py`

- [ ] **Step 1: Write the failing test**

Add a QR-like checkerboard badge in the lower-right ROI and assert the cleaned ROI differs while image size stays identical.

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_draft_upload.py::test_remove_watermark_cleans_qr_like_badge -q`
Expected: FAIL because dense-edge candidate handling is not implemented yet

- [ ] **Step 3: Write minimal implementation**

Add edge-density based candidate detection and mask dilation for QR-like blocks.

- [ ] **Step 4: Re-run the test to verify it passes**

Run: `python3 -m pytest tests/test_draft_upload.py::test_remove_watermark_cleans_qr_like_badge -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_draft_upload.py src/draft_upload.py
git commit -m "feat: support qr-like watermark badge cleanup"
```

### Task 4: Add failing safety tests for no-watermark and low-confidence cases

**Files:**
- Modify: `tests/test_draft_upload.py`
- Modify: `src/draft_upload.py`

- [ ] **Step 1: Write the failing tests**

Add:

```python
def test_remove_watermark_leaves_clean_image_unchanged():
    ...

def test_remove_watermark_does_not_destroy_legitimate_lower_right_content():
    ...
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_draft_upload.py::test_remove_watermark_leaves_clean_image_unchanged tests/test_draft_upload.py::test_remove_watermark_does_not_destroy_legitimate_lower_right_content -q`
Expected: FAIL because fallback still crops or over-masks

- [ ] **Step 3: Write minimal implementation**

Add confidence scoring and make the fallback return the original image when confidence is low or repair fails.

- [ ] **Step 4: Re-run the tests to verify they pass**

Run: `python3 -m pytest tests/test_draft_upload.py::test_remove_watermark_leaves_clean_image_unchanged tests/test_draft_upload.py::test_remove_watermark_does_not_destroy_legitimate_lower_right_content -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_draft_upload.py src/draft_upload.py
git commit -m "fix: keep low-confidence images unchanged"
```

## Chunk 3: Refine the Production Pipeline

### Task 5: Refactor image processing into focused helpers

**Files:**
- Modify: `src/draft_upload.py`
- Test: `tests/test_draft_upload.py`

- [ ] **Step 1: Write the failing test**

Add a focused test for mask generation returning a non-empty mask only for lower-right watermark cases:

```python
def test_detect_watermark_mask_only_flags_lower_right_candidates():
    ...
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_draft_upload.py::test_detect_watermark_mask_only_flags_lower_right_candidates -q`
Expected: FAIL because helper does not exist or does not enforce ROI rules

- [ ] **Step 3: Write minimal implementation**

Split the processing flow into small helpers:

```python
def load_image_array(image_data): ...
def detect_watermark_mask(image_bgr): ...
def score_watermark_candidate(...): ...
def inpaint_watermark(image_bgr, mask, roi_bounds): ...
```

- [ ] **Step 4: Re-run the test to verify it passes**

Run: `python3 -m pytest tests/test_draft_upload.py::test_detect_watermark_mask_only_flags_lower_right_candidates -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/draft_upload.py tests/test_draft_upload.py
git commit -m "refactor: extract watermark detection helpers"
```

### Task 6: Add optional debug output controls

**Files:**
- Modify: `src/draft_upload.py`
- Modify: `tests/test_draft_upload.py`

- [ ] **Step 1: Write the failing test**

Add a test that enables debug mode with a temp directory and verifies expected debug files are created only when a watermark is repaired.

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_draft_upload.py::test_remove_watermark_writes_debug_artifacts_when_enabled -q`
Expected: FAIL because debug hooks are not present

- [ ] **Step 3: Write minimal implementation**

Add a small debug toggle and conditional file output for original image, mask, and cleaned image.

- [ ] **Step 4: Re-run the test to verify it passes**

Run: `python3 -m pytest tests/test_draft_upload.py::test_remove_watermark_writes_debug_artifacts_when_enabled -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/draft_upload.py tests/test_draft_upload.py
git commit -m "feat: add optional watermark debug artifacts"
```

## Chunk 4: Final Verification

### Task 7: Run full verification and document actual status

**Files:**
- Modify: `src/draft_upload.py`
- Modify: `tests/test_draft_upload.py`
- Create: `requirements.txt`

- [ ] **Step 1: Run the focused test suite**

Run: `python3 -m pytest tests/test_draft_upload.py -q`
Expected: all tests pass

- [ ] **Step 2: Run a syntax check on the script**

Run: `python3 -m py_compile src/draft_upload.py tests/test_draft_upload.py`
Expected: exit code 0

- [ ] **Step 3: Review the diff against the approved spec**

Check that:
- output image dimensions are preserved
- failure fallback returns the original image
- crop-based fallback has been removed
- the implementation stays local-only

- [ ] **Step 4: Commit the finished implementation**

```bash
git add requirements.txt src/draft_upload.py tests/test_draft_upload.py
git commit -m "feat: replace crop-based watermark handling"
```
