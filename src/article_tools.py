import io
import os
import re
from collections import OrderedDict

import numpy as np
import requests
from PIL import Image

MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 "
    "Mobile/15E148 Safari/604.1"
)


def fetch_article_html(article_url, session=None, user_agent=None, timeout=20):
    client = session or requests
    headers = {"User-Agent": user_agent or MOBILE_USER_AGENT}
    response = client.get(article_url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.text


def extract_article_image_urls(html):
    img_tags = re.findall(r"<img[^>]+class=\"[^\"]*rich_pages[^\"]*\"[^>]*>", html, re.I)
    urls = []

    for tag in img_tags:
        match = re.search(r'data-src=\"([^\"]+)\"', tag) or re.search(r'src=\"([^\"]+)\"', tag)
        if not match:
            continue

        url = match.group(1).replace("&amp;", "&")
        if "mmbiz" in url:
            urls.append(url)

    return list(OrderedDict.fromkeys(urls))


def download_image(image_url, session=None, timeout=20):
    client = session or requests
    normalized_url = "https:" + image_url if image_url.startswith("//") else image_url
    headers = {
        "User-Agent": MOBILE_USER_AGENT,
        "Referer": "https://mp.weixin.qq.com/",
    }
    response = client.get(normalized_url, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.content


def _load_rgb_image(image_bytes):
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


def _default_analyze_image(image_bytes):
    return {
        "cleaned_bytes": image_bytes,
        "mask": None,
        "score": 0.0,
    }


def _write_artifacts(output_dir, index, original_image, cleaned_image, mask):
    original_image.save(os.path.join(output_dir, f"{index:02d}_original.jpg"), format="JPEG", quality=95)
    cleaned_image.save(os.path.join(output_dir, f"{index:02d}_clean.jpg"), format="JPEG", quality=95)

    if mask is None:
        mask = np.zeros((original_image.height, original_image.width), dtype=np.uint8)
    Image.fromarray(mask).save(os.path.join(output_dir, f"{index:02d}_mask.png"), format="PNG")


def process_article_images(
    image_urls,
    output_dir=None,
    save_images=False,
    download_image_fn=None,
    analyze_image_fn=None,
    session=None,
):
    download_image_fn = download_image_fn or download_image
    analyze_image_fn = analyze_image_fn or _default_analyze_image

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    image_results = []

    for index, image_url in enumerate(image_urls, 1):
        try:
            original_bytes = download_image_fn(image_url, session=session, timeout=20)
            original_image = _load_rgb_image(original_bytes)
            analysis = analyze_image_fn(original_bytes) or {}
            cleaned_bytes = analysis.get("cleaned_bytes") or original_bytes
            cleaned_image = _load_rgb_image(cleaned_bytes)
            mask = analysis.get("mask")
            score = float(analysis.get("score") or 0.0)
            diff_sum = int(
                np.abs(
                    np.array(original_image, dtype=np.int16) - np.array(cleaned_image, dtype=np.int16)
                ).sum()
            )
            changed = diff_sum > 0

            if save_images and output_dir:
                _write_artifacts(output_dir, index, original_image, cleaned_image, mask)

            image_results.append(
                {
                    "index": index,
                    "url": image_url,
                    "size": [original_image.width, original_image.height],
                    "score": score,
                    "mask_pixels": int(np.count_nonzero(mask)) if mask is not None else 0,
                    "changed": changed,
                    "diff_sum": diff_sum,
                    "status": "processed" if changed else "unchanged",
                    "error": None,
                    "cleaned_bytes": cleaned_bytes,
                }
            )
        except Exception as exc:
            image_results.append(
                {
                    "index": index,
                    "url": image_url,
                    "size": None,
                    "score": 0.0,
                    "mask_pixels": 0,
                    "changed": False,
                    "diff_sum": 0,
                    "status": "download_failed",
                    "error": str(exc),
                    "cleaned_bytes": None,
                }
            )

    return {"images": image_results}
