from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import article_drafts


def test_load_markdown_draft_parses_frontmatter_and_body(tmp_path):
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

    draft = article_drafts.load_markdown_draft(markdown_path)

    assert draft["meta"]["title"] == "示例标题"
    assert draft["meta"]["cover_image"] == "image1"
    assert "{{image1}}" in draft["body"]


def test_render_markdown_body_replaces_image_placeholders():
    html = article_drafts.render_markdown_body(
        "## 小标题\n\n第一段正文。\n\n{{image1}}\n",
        {"image1": "https://example.com/image1.jpg"},
    )

    assert "<h2>小标题</h2>" in html
    assert "https://example.com/image1.jpg" in html
    assert "{{image1}}" not in html


def test_render_markdown_body_fails_on_unresolved_placeholder():
    with pytest.raises(ValueError):
        article_drafts.render_markdown_body("{{image2}}", {"image1": "https://example.com/image1.jpg"})
