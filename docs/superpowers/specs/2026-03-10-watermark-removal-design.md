# Watermark Removal Design

**Date:** 2026-03-10

**Status:** Approved by user in terminal discussion

## Goal

Replace the current crop-based "watermark removal" flow in `src/draft_upload.py` with a local, non-paid, watermark-detection-plus-inpainting pipeline that preserves the original image dimensions.

## Current State

- `detect_watermark_by_vision()` assumes the watermark lives in the lower-right area and returns a crop boundary.
- `remove_watermark()` crops the image when detection succeeds and falls back to another crop when detection fails.
- Failure mode is destructive: false positives or weak detection remove real image content.

## Scope

In scope:

- Right-lower-corner semi-transparent watermark text or logo
- Right-lower-corner QR-code style badge blocks common in WeChat article images
- Local-only processing with open source libraries
- Replacing destructive fallback behavior with non-destructive fallback

Out of scope:

- Arbitrary watermark positions across the full image
- Large-area repeated watermarks
- External API services
- Deep-learning restoration as the first implementation

## Proposed Approach

Use a two-stage pipeline:

1. Detect a watermark mask in a lower-right ROI using lightweight image heuristics.
2. Repair only the masked region with OpenCV inpainting, then paste the repaired ROI back into the original image.

If confidence is too low or repair fails, return the original image instead of cropping.

## Detection Strategy

Analyze only a lower-right ROI sized at roughly 30% of image width and 22% of image height.

Build the candidate mask from three signals:

1. Bright, low-saturation regions in HSV/Lab space to catch white semi-transparent text and logos.
2. Dense edge regions using Sobel or Canny to catch QR-code style badges.
3. Connected-component filtering to keep only candidates that:
   - sit near the lower-right corner
   - have a reasonable area ratio
   - have plausible aspect ratios for text marks or badge blocks

Post-process the merged mask with close and dilate operations so translucent edges are covered before repair.

## Repair Strategy

- For small text/logo masks, use `cv2.inpaint(..., cv2.INPAINT_TELEA)`.
- For QR-like blocks, dilate the mask more aggressively before inpainting.
- Limit repair to the ROI so the rest of the image remains untouched.
- Keep output size identical to input size.

## Confidence and Fallback

Assign a confidence score based on:

- proximity to the lower-right corner
- candidate area ratio
- edge density
- brightness or contrast characteristics

Rules:

- high confidence: apply inpaint
- low confidence: return original image
- exception during processing: return original image

The fallback must never crop the image.

## Code Structure

Keep the implementation in `src/draft_upload.py` for now to avoid unrelated restructuring, but separate responsibilities into focused helpers:

- `load_image_array(image_data)`
- `detect_watermark_mask(image_bgr)`
- `score_watermark_candidate(...)`
- `inpaint_watermark(image_bgr, mask, roi_bounds)`
- `remove_watermark(image_data)`

Optional debug output should be gated behind a flag and should save:

- original image
- generated mask
- cleaned image

## Dependencies

Add local dependencies only:

- `opencv-python`
- existing `numpy`
- existing `Pillow`

No paid or hosted API usage.

## Verification Plan

Cover these cases with automated tests:

1. Image with bright semi-transparent watermark in the lower-right corner
2. Image with QR-like badge in the lower-right corner
3. Image with no watermark
4. Image with legitimate lower-right content that should not be removed

Assertions:

- output dimensions stay unchanged
- watermark cases trigger a non-empty mask and modified output
- no-watermark case returns unchanged bytes or pixel-equivalent output
- low-confidence cases do not crop or heavily alter the image

## Risks

- Heuristic thresholds may need tuning across different article image styles.
- Inpainting quality degrades on highly detailed textured backgrounds.
- QR-like blocks are easier to detect than faint translucent text over bright backgrounds.

## Future Extensions

- Move image-processing helpers into a dedicated module if this script grows further.
- Add optional local deep-learning inpainting behind a feature flag if heuristic repair quality is insufficient.
