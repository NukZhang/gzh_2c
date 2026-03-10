import re
from collections import OrderedDict

import requests

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
