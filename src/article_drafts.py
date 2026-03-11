import html
import re
from pathlib import Path

import yaml


REQUIRED_META_FIELDS = {
    "title",
    "content_source_url",
    "cover_image",
}
MAX_DIGEST_LENGTH = 120


def validate_draft_meta(meta):
    if not meta.get("title"):
        raise ValueError("missing required frontmatter field: title; please let AI fill title before upload")

    missing = [field for field in REQUIRED_META_FIELDS if field != "title" and not meta.get(field)]
    if missing:
        raise ValueError("missing required frontmatter fields: {}".format(", ".join(sorted(missing))))


def _split_blocks(body_markdown):
    return [block.strip() for block in re.split(r"\n\s*\n", body_markdown.strip()) if block.strip()]


def _derive_digest(body_markdown):
    for block in _split_blocks(body_markdown):
        if re.fullmatch(r"\{\{image\d+\}\}", block):
            continue
        if re.match(r"^#{1,6}\s+", block):
            continue
        normalized = re.sub(r"\s+", " ", block).strip()
        if normalized:
            return normalized[:MAX_DIGEST_LENGTH]

    raise ValueError("digest cannot be derived from markdown body")


def _derive_cover_image(body_markdown):
    match = re.search(r"\{\{(image\d+)\}\}", body_markdown)
    if match:
        return match.group(1)

    raise ValueError("cover_image cannot be derived from markdown body")


def _normalize_draft_meta(meta, body_markdown, fallback_source_url=None):
    normalized = dict(meta)
    if not normalized.get("digest"):
        normalized["digest"] = _derive_digest(body_markdown)
    if not normalized.get("cover_image"):
        normalized["cover_image"] = _derive_cover_image(body_markdown)
    if not normalized.get("content_source_url") and fallback_source_url:
        normalized["content_source_url"] = fallback_source_url
    return normalized


def load_markdown_draft_text(text, fallback_source_url=None):
    if not text.startswith("---\n"):
        raise ValueError("markdown draft must start with YAML frontmatter")

    _, remainder = text.split("---\n", 1)
    frontmatter_text, body = remainder.split("\n---\n", 1)
    body = body.strip()
    meta = _normalize_draft_meta(
        yaml.safe_load(frontmatter_text) or {},
        body,
        fallback_source_url=fallback_source_url,
    )
    validate_draft_meta(meta)

    return {
        "meta": meta,
        "body": body,
    }


def load_markdown_draft(markdown_path, fallback_source_url=None):
    text = Path(markdown_path).read_text(encoding="utf-8")
    return load_markdown_draft_text(text, fallback_source_url=fallback_source_url)


def _render_inline(text):
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', escaped)
    return escaped


def _render_placeholder(placeholder_key, image_map):
    image_url = image_map[placeholder_key]
    return (
        '<p style="text-align:center;margin:15px 0;">'
        '<img src="{}" style="max-width:100%;border-radius:8px;"/>'
        "</p>"
    ).format(html.escape(image_url, quote=True))


def _validate_placeholders(body_markdown, image_map):
    placeholders = re.findall(r"\{\{(image\d+)\}\}", body_markdown)
    missing = [name for name in placeholders if name not in image_map]
    if missing:
        raise ValueError("unresolved image placeholders: {}".format(", ".join(sorted(set(missing)))))


def render_markdown_body(body_markdown, image_map):
    _validate_placeholders(body_markdown, image_map)

    blocks = _split_blocks(body_markdown)
    rendered_blocks = []

    for block in blocks:
        if re.fullmatch(r"\{\{image\d+\}\}", block):
            key = re.findall(r"\{\{(image\d+)\}\}", block)[0]
            rendered_blocks.append(_render_placeholder(key, image_map))
            continue

        if block.startswith("## "):
            rendered_blocks.append("<h2>{}</h2>".format(_render_inline(block[3:].strip())))
            continue

        if block.startswith("# "):
            rendered_blocks.append("<h1>{}</h1>".format(_render_inline(block[2:].strip())))
            continue

        rendered_blocks.append("<p>{}</p>".format(_render_inline(block.replace("\n", "<br/>"))))

    return "".join(rendered_blocks)


def resolve_cover_image_key(meta, image_map):
    cover_key = meta.get("cover_image")
    if cover_key not in image_map:
        raise ValueError("cover_image reference not found: {}".format(cover_key))
    return cover_key


def build_article_payload(draft, rendered_html, thumb_media_id, default_author):
    meta = draft["meta"]
    return {
        "title": meta["title"],
        "author": meta.get("author") or default_author,
        "content": rendered_html,
        "thumb_media_id": thumb_media_id,
        "digest": meta["digest"],
        "content_source_url": meta["content_source_url"],
        "need_open_comment": 0,
        "only_fans_can_comment": 0,
    }
