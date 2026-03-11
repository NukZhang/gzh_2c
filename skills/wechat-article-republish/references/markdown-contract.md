# Markdown Contract

The generated article file must be a UTF-8 Markdown file with YAML frontmatter.

## Required Shape

```md
---
title: 新标题
content_source_url: https://mp.weixin.qq.com/s/example
cover_image: image1
---

正文第一段。

{{image1}}

正文第二段。
```

## Frontmatter Rules

- `title`
  - required
- `content_source_url`
  - required
  - should be the original WeChat article URL
- `cover_image`
  - required
  - must point to an image placeholder used in the body
- `digest`
  - optional
  - if omitted, the project derives it from the first non-heading text paragraph
- `author`
  - optional
  - if omitted, the project falls back to `wechat.yml`

## Body Rules

- The body must contain real text paragraphs.
- Image placeholders must use the exact form `{{imageN}}`.
- `N` starts at `1` and follows source image order.
- Every placeholder used in the body must map to a source image.
- The first placeholder may be reused as the cover, or another body placeholder may be chosen.

## Content Rules

- The rewrite must remain faithful to source facts.
- Do not invent source facts, people, data, or events.
- The host AI tool may reorganize the article and change tone, but not fabricate content.

## Failure Cases

The project upload will fail if:

- frontmatter is missing
- `title` is missing
- the body has no usable text for digest derivation
- `cover_image` points to a nonexistent placeholder
- the body references placeholders that cannot be resolved
