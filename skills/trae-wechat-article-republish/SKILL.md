---
name: trae-wechat-article-republish
description: Use when Trae should rewrite a WeChat article from a source URL with its own model, then send the resulting Markdown to this repository for preview or WeChat draft upload.
---

# Trae WeChat Article Republish

This is a thin Trae-oriented adapter for the generic WeChat republish workflow.

## Workflow

1. Read [../wechat-article-republish/SKILL.md](../wechat-article-republish/SKILL.md).
2. Generate the rewritten article Markdown with Trae itself.
3. Save the result to a local file.
4. Use this repository to preview or upload the draft.

## Commands

Preview first:

```bash
python3 src/article_pipeline.py upload \
  --url '<article_url>' \
  --markdown <generated.md> \
  --dry-run \
  --output <preview_dir>
```

Real upload:

```bash
python3 src/article_pipeline.py upload \
  --url '<article_url>' \
  --markdown <generated.md>
```

## Rule

Keep Trae responsible for generation. Keep this repository responsible for Markdown validation, image handling, and WeChat draft submission.
