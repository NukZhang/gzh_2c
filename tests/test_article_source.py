from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import article_source


def test_extract_source_article_prefers_msg_title_and_body_blocks():
    html = """
    <html>
      <head>
        <meta property="og:title" content="后备标题" />
        <script>var msg_title = '示例标题'.html(false);</script>
      </head>
      <body>
        <div id="js_content">
          <p>第一段</p>
          <h2>小标题</h2>
          <figure><img class="rich_pages wxw-img" data-src="https://mmbiz.qpic.cn/1" /></figure>
          <p>第二段</p>
        </div>
      </body>
    </html>
    """

    source = article_source.extract_source_article(html)

    assert source["title"] == "示例标题"
    assert source["body_markdown"] == "第一段\n\n## 小标题\n\n{{image1}}\n\n第二段"
    assert source["image_keys"] == ["image1"]


def test_extract_source_article_falls_back_to_og_title():
    html = """
    <html>
      <head><meta property="og:title" content="后备标题" /></head>
      <body><div id="js_content"><p>正文</p></div></body>
    </html>
    """

    source = article_source.extract_source_article(html)

    assert source["title"] == "后备标题"


def test_extract_source_article_reuses_placeholder_for_duplicate_image_url():
    html = """
    <script>var msg_title = '示例标题'.html(false);</script>
    <div id="js_content">
      <p>第一段</p>
      <figure><img class="rich_pages wxw-img" data-src="https://mmbiz.qpic.cn/1" /></figure>
      <p>第二段</p>
      <figure><img class="rich_pages wxw-img" data-src="https://mmbiz.qpic.cn/1" /></figure>
    </div>
    """

    source = article_source.extract_source_article(html)

    assert source["image_keys"] == ["image1"]
    assert source["body_markdown"] == "第一段\n\n{{image1}}\n\n第二段\n\n{{image1}}"


def test_extract_source_article_requires_real_text():
    html = """
    <script>var msg_title = '示例标题'.html(false);</script>
    <div id="js_content">
      <figure><img class="rich_pages wxw-img" data-src="https://mmbiz.qpic.cn/1" /></figure>
    </div>
    """

    with pytest.raises(ValueError, match="source body"):
        article_source.extract_source_article(html)
