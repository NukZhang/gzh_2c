from pathlib import Path

import yaml


REQUIRED_META_FIELDS = {
    "title",
    "digest",
    "content_source_url",
    "cover_image",
}


def validate_draft_meta(meta):
    missing = [field for field in REQUIRED_META_FIELDS if not meta.get(field)]
    if missing:
        raise ValueError("missing required frontmatter fields: {}".format(", ".join(sorted(missing))))


def load_markdown_draft(markdown_path):
    text = Path(markdown_path).read_text(encoding="utf-8")

    if not text.startswith("---\n"):
        raise ValueError("markdown draft must start with YAML frontmatter")

    _, remainder = text.split("---\n", 1)
    frontmatter_text, body = remainder.split("\n---\n", 1)
    meta = yaml.safe_load(frontmatter_text) or {}
    validate_draft_meta(meta)

    return {
        "meta": meta,
        "body": body.strip(),
    }
