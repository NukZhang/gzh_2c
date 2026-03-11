import ast
import re
from html.parser import HTMLParser


MSG_TITLE_PATTERN = re.compile(
    r"var\s+msg_title\s*=\s*(?P<quoted>'(?:\\.|[^'])*'|\"(?:\\.|[^\"])*\")\.html\(false\)",
    re.S,
)
OG_TITLE_PATTERN = re.compile(
    r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)


def _normalize_inline_text(text):
    lines = []
    for raw_line in text.splitlines():
        normalized = re.sub(r"\s+", " ", raw_line).strip()
        if normalized:
            lines.append(normalized)
    return "\n".join(lines)


def _normalize_image_url(url):
    if url.startswith("//"):
        return "https:" + url
    return url


def _extract_title(html):
    match = MSG_TITLE_PATTERN.search(html)
    if match:
        return ast.literal_eval(match.group("quoted")).strip()

    match = OG_TITLE_PATTERN.search(html)
    if match:
        return match.group(1).strip()

    raise ValueError("article title could not be extracted")


class _SourceArticleParser(HTMLParser):
    TEXT_TAGS = {"p", "li", "blockquote"}
    HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._in_content = False
        self._content_depth = 0
        self._active_block = None
        self._blocks = []
        self._image_keys = []
        self._image_key_by_url = {}

    @property
    def blocks(self):
        return list(self._blocks)

    @property
    def image_keys(self):
        return list(self._image_keys)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if not self._in_content:
            if tag == "div" and attrs.get("id") == "js_content":
                self._in_content = True
                self._content_depth = 1
            return

        self._content_depth += 1

        if tag in self.TEXT_TAGS and self._active_block is None:
            self._active_block = {"tag": tag, "kind": "paragraph", "parts": []}
            return

        if tag in self.HEADING_TAGS and self._active_block is None:
            self._active_block = {
                "tag": tag,
                "kind": "heading",
                "level": int(tag[1]),
                "parts": [],
            }
            return

        if tag == "br" and self._active_block is not None:
            self._active_block["parts"].append("\n")
            return

        if tag == "img":
            self._append_image_block(attrs)

    def handle_startendtag(self, tag, attrs):
        if tag == "img":
            self.handle_starttag(tag, attrs)
            if self._in_content:
                self._content_depth -= 1

    def handle_endtag(self, tag):
        if not self._in_content:
            return

        if self._active_block is not None and tag == self._active_block["tag"]:
            text = _normalize_inline_text("".join(self._active_block["parts"]))
            if text:
                self._append_text_block(
                    kind=self._active_block["kind"],
                    text=text,
                    level=self._active_block.get("level"),
                )
            self._active_block = None

        self._content_depth -= 1
        if self._content_depth == 0:
            self._in_content = False

    def handle_data(self, data):
        if self._active_block is not None:
            self._active_block["parts"].append(data)

    def _append_text_block(self, kind, text, level=None):
        self._blocks.append(
            {
                "type": kind,
                "text": text,
                "level": level,
            }
        )

    def _append_image_block(self, attrs):
        classes = attrs.get("class", "")
        image_url = attrs.get("data-src") or attrs.get("src")

        if "rich_pages" not in classes or not image_url or "mmbiz" not in image_url:
            return

        normalized_url = _normalize_image_url(image_url)
        image_key = self._image_key_by_url.get(normalized_url)
        if image_key is None:
            image_key = "image{}".format(len(self._image_keys) + 1)
            self._image_keys.append(image_key)
            self._image_key_by_url[normalized_url] = image_key

        self._blocks.append(
            {
                "type": "image",
                "key": image_key,
                "url": normalized_url,
            }
        )


def _render_body_markdown(blocks):
    rendered = []
    for block in blocks:
        if block["type"] == "paragraph":
            rendered.append(block["text"])
            continue

        if block["type"] == "heading":
            level = min(max(block.get("level") or 2, 1), 6)
            rendered.append("{} {}".format("#" * level, block["text"]))
            continue

        if block["type"] == "image":
            rendered.append("{{{{{}}}}}".format(block["key"]))

    return "\n\n".join(rendered)


def extract_source_article(html):
    title = _extract_title(html)
    parser = _SourceArticleParser()
    parser.feed(html)
    parser.close()

    body_markdown = _render_body_markdown(parser.blocks)
    has_text = any(block["type"] in {"paragraph", "heading"} for block in parser.blocks)
    if not has_text:
        raise ValueError("source body must contain text content")

    return {
        "title": title,
        "body_markdown": body_markdown,
        "blocks": parser.blocks,
        "image_keys": parser.image_keys,
    }
