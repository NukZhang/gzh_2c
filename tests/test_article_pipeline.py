import io
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import article_tools


def make_image_bytes(size=(120, 80), color=(60, 120, 180)):
    output = io.BytesIO()
    Image.new("RGB", size, color).save(output, format="JPEG", quality=95)
    return output.getvalue()


def test_extract_article_image_urls_prefers_rich_pages_images():
    html = """
    <html>
      <body>
        <img src="https://mmbiz.qpic.cn/mmbiz_jpg/cover/0?wx_fmt=jpeg" alt="cover_image" />
        <img class="rich_pages wxw-img" data-src="https://mmbiz.qpic.cn/mmbiz_png/foo/640?wx_fmt=png&amp;from=appmsg" />
        <img class="other" data-src="https://mmbiz.qpic.cn/mmbiz_png/skip/640?wx_fmt=png&amp;from=appmsg" />
        <img class="rich_pages wxw-img" src="https://mmbiz.qpic.cn/mmbiz_jpg/bar/640?wx_fmt=jpeg&amp;from=appmsg" />
      </body>
    </html>
    """

    urls = article_tools.extract_article_image_urls(html)

    assert urls == [
        "https://mmbiz.qpic.cn/mmbiz_png/foo/640?wx_fmt=png&from=appmsg",
        "https://mmbiz.qpic.cn/mmbiz_jpg/bar/640?wx_fmt=jpeg&from=appmsg",
    ]


def test_process_article_images_returns_per_image_summary(tmp_path):
    raw_bytes = make_image_bytes()
    clean_bytes = make_image_bytes(color=(80, 140, 200))
    mask = np.zeros((80, 120), dtype=np.uint8)
    mask[-24:, -24:] = 255

    def fake_download(_url, session=None, timeout=20):
        return raw_bytes

    def fake_analyze(_image_bytes):
        return {
            "cleaned_bytes": clean_bytes,
            "mask": mask,
            "score": 0.81,
        }

    result = article_tools.process_article_images(
        ["https://example.com/1.jpg"],
        output_dir=tmp_path,
        save_images=True,
        download_image_fn=fake_download,
        analyze_image_fn=fake_analyze,
    )

    assert result["images"][0]["status"] == "processed"
    assert result["images"][0]["changed"] is True
    assert result["images"][0]["score"] == 0.81
    assert (tmp_path / "01_original.jpg").exists()
    assert (tmp_path / "01_mask.png").exists()
    assert (tmp_path / "01_clean.jpg").exists()


def test_article_pipeline_analyze_writes_summary_json(tmp_path, monkeypatch):
    import article_pipeline

    html = """
    <img class="rich_pages wxw-img" data-src="https://mmbiz.qpic.cn/mmbiz_png/foo/640?wx_fmt=png&amp;from=appmsg" />
    """

    monkeypatch.setattr(article_tools, "fetch_article_html", lambda article_url, session=None, user_agent=None, timeout=20: html)
    monkeypatch.setattr(
        article_tools,
        "process_article_images",
        lambda image_urls, output_dir=None, save_images=False, download_image_fn=None, analyze_image_fn=None, session=None: {
            "images": [
                {
                    "index": 1,
                    "url": image_urls[0],
                    "size": [120, 80],
                    "score": 0.81,
                    "mask_pixels": 50,
                    "changed": True,
                    "diff_sum": 1234,
                    "status": "processed",
                    "error": None,
                }
            ]
        },
    )

    exit_code = article_pipeline.main(
        ["analyze", "--url", "https://mp.weixin.qq.com/s/example", "--output", str(tmp_path)]
    )

    assert exit_code == 0
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["images"][0]["status"] == "processed"


def test_article_pipeline_analyze_uses_draft_upload_watermark_analyzer(tmp_path, monkeypatch):
    import article_pipeline
    import draft_upload

    captured = {}

    def fake_analyze_article(
        article_url,
        output_dir,
        save_images=True,
        session=None,
        analyze_image_fn=None,
        download_image_fn=None,
    ):
        captured["analyze_image_fn"] = analyze_image_fn
        return {"images": [], "counts": {"total": 0, "processed": 0, "unchanged": 0, "failed": 0}}

    monkeypatch.setattr(article_tools, "analyze_article", fake_analyze_article)

    exit_code = article_pipeline.main(
        ["analyze", "--url", "https://mp.weixin.qq.com/s/example", "--output", str(tmp_path)]
    )

    assert exit_code == 0
    assert captured["analyze_image_fn"] is draft_upload.analyze_watermark


def test_analyze_article_continues_when_one_image_download_fails(tmp_path, monkeypatch):
    html = """
    <img class="rich_pages wxw-img" data-src="https://mmbiz.qpic.cn/mmbiz_png/one/640?wx_fmt=png&amp;from=appmsg" />
    <img class="rich_pages wxw-img" data-src="https://mmbiz.qpic.cn/mmbiz_png/two/640?wx_fmt=png&amp;from=appmsg" />
    <img class="rich_pages wxw-img" data-src="https://mmbiz.qpic.cn/mmbiz_png/three/640?wx_fmt=png&amp;from=appmsg" />
    """
    raw_bytes = make_image_bytes()

    monkeypatch.setattr(article_tools, "fetch_article_html", lambda article_url, session=None, user_agent=None, timeout=20: html)

    def fake_download(image_url, session=None, timeout=20):
        if "two" in image_url:
            raise RuntimeError("boom")
        return raw_bytes

    summary = article_tools.analyze_article(
        "https://mp.weixin.qq.com/s/example",
        output_dir=tmp_path,
        save_images=False,
        analyze_image_fn=lambda image_bytes: {"cleaned_bytes": image_bytes, "mask": None, "score": 0.0},
        download_image_fn=fake_download,
    )

    assert [item["status"] for item in summary["images"]] == [
        "unchanged",
        "download_failed",
        "unchanged",
    ]
    assert summary["counts"]["failed"] == 1


def test_article_pipeline_upload_dry_run_skips_wechat_upload(tmp_path, monkeypatch):
    import article_pipeline

    markdown_path = tmp_path / "article.md"
    markdown_path.write_text(
        """---
title: 示例标题
digest: 示例摘要
content_source_url: https://example.com/article
cover_image: image1
---

第一段正文。

{{image1}}
""",
        encoding="utf-8",
    )

    events = []
    monkeypatch.setattr(
        article_tools,
        "prepare_article_images",
        lambda article_url, limit=None, session=None, analyze_image_fn=None, download_image_fn=None: (
            events.append("prepare")
            or {
                "images": [
                    {
                        "index": 1,
                        "url": "https://mmbiz.qpic.cn/mmbiz_png/foo/640?wx_fmt=png&from=appmsg",
                        "size": [120, 80],
                        "score": 0.81,
                        "mask_pixels": 50,
                        "changed": True,
                        "diff_sum": 1234,
                        "status": "processed",
                        "error": None,
                        "cleaned_bytes": b"processed",
                    }
                ],
                "counts": {"total": 1, "processed": 1, "unchanged": 0, "failed": 0},
            }
        ),
    )

    upload_calls = []
    monkeypatch.setattr(
        article_tools,
        "upload_processed_images",
        lambda *args, **kwargs: upload_calls.append((args, kwargs)) or {"images": [], "counts": {}},
        raising=False,
    )

    exit_code = article_pipeline.main(
        [
            "upload",
            "--url",
            "https://mp.weixin.qq.com/s/example",
            "--markdown",
            str(markdown_path),
            "--dry-run",
        ]
    )

    assert exit_code == 0
    assert events == ["prepare"]
    assert upload_calls == []


def test_upload_dry_run_accepts_markdown_without_digest(tmp_path, monkeypatch):
    import article_pipeline

    markdown_path = tmp_path / "article.md"
    markdown_path.write_text(
        """---
title: 示例标题
content_source_url: https://example.com/article
cover_image: image1
---

第一段正文，应该自动生成摘要。

{{image1}}
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        article_tools,
        "prepare_article_images",
        lambda article_url, limit=None, session=None, analyze_image_fn=None, download_image_fn=None: {
            "images": [
                {
                    "index": 1,
                    "url": "https://mmbiz.qpic.cn/mmbiz_png/foo/640?wx_fmt=png&from=appmsg",
                    "size": [120, 80],
                    "score": 0.81,
                    "mask_pixels": 50,
                    "changed": True,
                    "diff_sum": 1234,
                    "status": "processed",
                    "error": None,
                    "cleaned_bytes": b"processed",
                }
            ],
            "counts": {"total": 1, "processed": 1, "unchanged": 0, "failed": 0},
        },
    )

    exit_code = article_pipeline.main(
        [
            "upload",
            "--url",
            "https://mp.weixin.qq.com/s/example",
            "--markdown",
            str(markdown_path),
            "--dry-run",
        ]
    )

    assert exit_code == 0


def test_upload_dry_run_accepts_markdown_without_cover_image_or_source_url(tmp_path, monkeypatch):
    import article_pipeline

    markdown_path = tmp_path / "article.md"
    markdown_path.write_text(
        """---
title: 示例标题
---

第一段正文，应该自动生成摘要。

{{image1}}
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        article_tools,
        "prepare_article_images",
        lambda article_url, limit=None, session=None, analyze_image_fn=None, download_image_fn=None: {
            "images": [
                {
                    "index": 1,
                    "url": "https://mmbiz.qpic.cn/mmbiz_png/foo/640?wx_fmt=png&from=appmsg",
                    "size": [120, 80],
                    "score": 0.81,
                    "mask_pixels": 50,
                    "changed": True,
                    "diff_sum": 1234,
                    "status": "processed",
                    "error": None,
                    "cleaned_bytes": b"processed",
                }
            ],
            "counts": {"total": 1, "processed": 1, "unchanged": 0, "failed": 0},
        },
    )

    exit_code = article_pipeline.main(
        [
            "upload",
            "--url",
            "https://mp.weixin.qq.com/s/example",
            "--markdown",
            str(markdown_path),
            "--dry-run",
            "--output",
            str(tmp_path / "preview"),
        ]
    )

    assert exit_code == 0
    preview = json.loads((tmp_path / "preview" / "article.json").read_text(encoding="utf-8"))
    assert preview["content_source_url"] == "https://mp.weixin.qq.com/s/example"
    assert preview["thumb_media_id"] == "dry-run:image1"


def test_upload_dry_run_writes_preview_files(tmp_path, monkeypatch):
    import article_pipeline

    markdown_path = tmp_path / "article.md"
    markdown_path.write_text(
        """---
title: 示例标题
digest: 示例摘要
content_source_url: https://example.com/article
cover_image: image1
---

第一段正文。

{{image1}}
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        article_tools,
        "prepare_article_images",
        lambda article_url, limit=None, session=None, analyze_image_fn=None, download_image_fn=None: {
            "images": [
                {
                    "index": 1,
                    "url": "https://mmbiz.qpic.cn/mmbiz_png/foo/640?wx_fmt=png&from=appmsg",
                    "size": [120, 80],
                    "score": 0.81,
                    "mask_pixels": 50,
                    "changed": True,
                    "diff_sum": 1234,
                    "status": "processed",
                    "error": None,
                    "cleaned_bytes": b"processed",
                }
            ],
            "counts": {"total": 1, "processed": 1, "unchanged": 0, "failed": 0},
        },
    )

    exit_code = article_pipeline.main(
        [
            "upload",
            "--url",
            "https://mp.weixin.qq.com/s/example",
            "--markdown",
            str(markdown_path),
            "--dry-run",
            "--output",
            str(tmp_path / "preview"),
        ]
    )

    assert exit_code == 0
    assert (tmp_path / "preview" / "body.html").exists()
    assert (tmp_path / "preview" / "article.json").exists()
    assert (tmp_path / "preview" / "image_map.json").exists()


def test_upload_requires_title_from_markdown_or_ai(tmp_path, monkeypatch):
    import article_pipeline

    markdown_path = tmp_path / "article.md"
    markdown_path.write_text(
        """---
content_source_url: https://example.com/article
---

第一段正文。

{{image1}}
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        article_tools,
        "prepare_article_images",
        lambda article_url, limit=None, session=None, analyze_image_fn=None, download_image_fn=None: {
            "images": [],
            "counts": {"total": 0, "processed": 0, "unchanged": 0, "failed": 0},
        },
    )

    with pytest.raises(ValueError, match="AI"):
        article_pipeline.main(
            [
                "upload",
                "--url",
                "https://mp.weixin.qq.com/s/example",
                "--markdown",
                str(markdown_path),
                "--dry-run",
            ]
        )


def test_legacy_fetch_article_images_uses_shared_extractor(monkeypatch):
    import draft_upload

    html = """
    <img class="rich_pages wxw-img" data-src="https://mmbiz.qpic.cn/mmbiz_png/foo/640?wx_fmt=png&amp;from=appmsg" />
    <img class="rich_pages wxw-img" data-src="https://mmbiz.qpic.cn/mmbiz_jpg/bar/640?wx_fmt=jpeg&amp;from=appmsg" />
    """

    monkeypatch.setattr(
        article_tools,
        "fetch_article_html",
        lambda article_url, session=None, user_agent=None, timeout=20: html,
    )

    assert draft_upload.fetch_article_images("https://mp.weixin.qq.com/s/example") == [
        "https://mmbiz.qpic.cn/mmbiz_png/foo/640?wx_fmt=png&from=appmsg",
        "https://mmbiz.qpic.cn/mmbiz_jpg/bar/640?wx_fmt=jpeg&from=appmsg",
    ]


def test_upload_mode_builds_and_submits_wechat_draft(tmp_path, monkeypatch):
    import article_pipeline

    markdown_path = tmp_path / "article.md"
    markdown_path.write_text(
        """---
title: 示例标题
digest: 示例摘要
content_source_url: https://example.com/article
cover_image: image1
---

第一段正文。

{{image1}}
""",
        encoding="utf-8",
    )

    processed = {
        "images": [
            {
                "index": 1,
                "url": "https://mmbiz.qpic.cn/mmbiz_png/foo/640?wx_fmt=png&from=appmsg",
                "size": [120, 80],
                "score": 0.81,
                "mask_pixels": 50,
                "changed": True,
                "diff_sum": 1234,
                "status": "processed",
                "error": None,
                "cleaned_bytes": b"processed-image-bytes",
            }
        ],
        "counts": {"total": 1, "processed": 1, "unchanged": 0, "failed": 0},
    }

    monkeypatch.setattr(article_tools, "prepare_article_images", lambda *args, **kwargs: processed)

    upload_calls = []

    def fake_upload_image(access_token, image_bytes):
        upload_calls.append(image_bytes)
        if len(upload_calls) == 1:
            return {"url": "https://weixin.example/body-image.jpg", "media_id": "body-media"}
        return {"media_id": "thumb123", "url": "https://weixin.example/cover-image.jpg"}

    captured = {}

    monkeypatch.setattr("draft_upload.load_config", lambda: {"wechat": {"appid": "a", "secret": "b", "author": "默认作者"}})
    monkeypatch.setattr("draft_upload.get_access_token", lambda appid, secret: "token123")
    monkeypatch.setattr("draft_upload.upload_permanent_image", fake_upload_image)
    monkeypatch.setattr(
        "draft_upload.upload_draft",
        lambda access_token, articles: captured.setdefault("articles", articles) or {"media_id": "draft123"},
    )

    exit_code = article_pipeline.main(
        [
            "upload",
            "--url",
            "https://mp.weixin.qq.com/s/example",
            "--markdown",
            str(markdown_path),
        ]
    )

    assert exit_code == 0
    assert captured["articles"][0]["title"] == "示例标题"
    assert captured["articles"][0]["thumb_media_id"] == "thumb123"
    assert "https://weixin.example/body-image.jpg" in captured["articles"][0]["content"]


def test_upload_dry_run_generates_markdown_via_ai_cli(tmp_path, monkeypatch):
    import article_drafts
    import article_pipeline
    import article_source
    import ai_rewrite

    source_article = {
        "title": "原文标题",
        "body_markdown": "原文第一段。\n\n{{image1}}",
        "blocks": [
            {"type": "paragraph", "text": "原文第一段。", "level": None},
            {"type": "image", "key": "image1", "url": "https://mmbiz.qpic.cn/mmbiz_png/foo/640?wx_fmt=png"},
        ],
        "image_keys": ["image1"],
    }

    processed = {
        "images": [
            {
                "index": 1,
                "url": "https://mmbiz.qpic.cn/mmbiz_png/foo/640?wx_fmt=png&from=appmsg",
                "size": [120, 80],
                "score": 0.81,
                "mask_pixels": 50,
                "changed": True,
                "diff_sum": 1234,
                "status": "processed",
                "error": None,
                "cleaned_bytes": b"processed-image-bytes",
            }
        ],
        "counts": {"total": 1, "processed": 1, "unchanged": 0, "failed": 0},
    }

    monkeypatch.setattr(article_tools, "fetch_article_html", lambda *args, **kwargs: "<html>...</html>")
    monkeypatch.setattr(article_source, "extract_source_article", lambda html: source_article)
    monkeypatch.setattr(article_tools, "prepare_article_images", lambda *args, **kwargs: processed)

    captured = {}

    def fake_generate_markdown_draft(**kwargs):
        captured.update(kwargs)
        markdown = """---
title: 新标题
content_source_url: https://mp.weixin.qq.com/s/example
cover_image: image1
---

新正文。

{{image1}}
"""
        return {
            "command": "fake-ai",
            "prompt": "prompt text",
            "markdown": markdown,
            "draft": article_drafts.load_markdown_draft_text(markdown),
        }

    monkeypatch.setattr(ai_rewrite, "generate_markdown_draft", fake_generate_markdown_draft)

    exit_code = article_pipeline.main(
        [
            "upload",
            "--url",
            "https://mp.weixin.qq.com/s/example",
            "--thought",
            "我的思考",
            "--dry-run",
            "--output",
            str(tmp_path / "preview"),
        ]
    )

    assert exit_code == 0
    assert captured["thought_text"] == "我的思考"
    assert (tmp_path / "preview" / "source.json").exists()
    assert (tmp_path / "preview" / "prompt.txt").exists()
    assert (tmp_path / "preview" / "generated.md").exists()
    preview = json.loads((tmp_path / "preview" / "article.json").read_text(encoding="utf-8"))
    assert preview["title"] == "新标题"


def test_upload_mode_rejects_markdown_and_thought_together(tmp_path):
    import article_pipeline

    markdown_path = tmp_path / "article.md"
    markdown_path.write_text(
        """---
title: 示例标题
content_source_url: https://example.com/article
cover_image: image1
---

正文

{{image1}}
""",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        article_pipeline.main(
            [
                "upload",
                "--url",
                "https://mp.weixin.qq.com/s/example",
                "--markdown",
                str(markdown_path),
                "--thought",
                "额外想法",
            ]
        )


def test_upload_mode_submits_generated_draft_from_thought_file(tmp_path, monkeypatch):
    import article_drafts
    import article_pipeline
    import article_source
    import ai_rewrite

    thought_path = tmp_path / "thought.txt"
    thought_path.write_text("文件里的思考", encoding="utf-8")

    source_article = {
        "title": "原文标题",
        "body_markdown": "原文第一段。\n\n{{image1}}",
        "blocks": [
            {"type": "paragraph", "text": "原文第一段。", "level": None},
            {"type": "image", "key": "image1", "url": "https://mmbiz.qpic.cn/mmbiz_png/foo/640?wx_fmt=png"},
        ],
        "image_keys": ["image1"],
    }

    processed = {
        "images": [
            {
                "index": 1,
                "url": "https://mmbiz.qpic.cn/mmbiz_png/foo/640?wx_fmt=png&from=appmsg",
                "size": [120, 80],
                "score": 0.81,
                "mask_pixels": 50,
                "changed": True,
                "diff_sum": 1234,
                "status": "processed",
                "error": None,
                "cleaned_bytes": b"processed-image-bytes",
            }
        ],
        "counts": {"total": 1, "processed": 1, "unchanged": 0, "failed": 0},
    }

    monkeypatch.setattr(article_tools, "fetch_article_html", lambda *args, **kwargs: "<html>...</html>")
    monkeypatch.setattr(article_source, "extract_source_article", lambda html: source_article)
    monkeypatch.setattr(article_tools, "prepare_article_images", lambda *args, **kwargs: processed)

    captured_generation = {}

    def fake_generate_markdown_draft(**kwargs):
        captured_generation.update(kwargs)
        markdown = """---
title: AI 新标题
content_source_url: https://mp.weixin.qq.com/s/example
cover_image: image1
---

AI 生成正文。

{{image1}}
"""
        return {
            "command": "fake-ai",
            "prompt": "prompt text",
            "markdown": markdown,
            "draft": article_drafts.load_markdown_draft_text(markdown),
        }

    monkeypatch.setattr(ai_rewrite, "generate_markdown_draft", fake_generate_markdown_draft)

    upload_calls = []

    def fake_upload_image(access_token, image_bytes):
        upload_calls.append(image_bytes)
        if len(upload_calls) == 1:
            return {"url": "https://weixin.example/body-image.jpg", "media_id": "body-media"}
        return {"media_id": "thumb123", "url": "https://weixin.example/cover-image.jpg"}

    captured = {}

    monkeypatch.setattr("draft_upload.load_config", lambda: {"wechat": {"appid": "a", "secret": "b", "author": "默认作者"}})
    monkeypatch.setattr("draft_upload.get_access_token", lambda appid, secret: "token123")
    monkeypatch.setattr("draft_upload.upload_permanent_image", fake_upload_image)
    monkeypatch.setattr(
        "draft_upload.upload_draft",
        lambda access_token, articles: captured.setdefault("articles", articles) or {"media_id": "draft123"},
    )

    exit_code = article_pipeline.main(
        [
            "upload",
            "--url",
            "https://mp.weixin.qq.com/s/example",
            "--thought-file",
            str(thought_path),
        ]
    )

    assert exit_code == 0
    assert captured_generation["thought_text"] == "文件里的思考"
    assert captured["articles"][0]["title"] == "AI 新标题"
    assert captured["articles"][0]["thumb_media_id"] == "thumb123"
    assert "https://weixin.example/body-image.jpg" in captured["articles"][0]["content"]
