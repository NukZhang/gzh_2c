import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import article_tools


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
