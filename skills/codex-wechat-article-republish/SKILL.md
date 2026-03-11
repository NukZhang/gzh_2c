---
name: codex-wechat-article-republish
description: Use when Codex or Claude Code should rewrite a WeChat article with its own model, then hand the Markdown to this repository for dry-run or WeChat draft upload.
---

# Codex WeChat Article Republish

This is a thin adapter for Codex or Claude Code style environments.

## Workflow

1. Read [../wechat-article-republish/SKILL.md](../wechat-article-republish/SKILL.md).
2. Use your own model to generate a Markdown draft that follows the referenced contract.
3. Save the Markdown to a local file.
4. Run the repository CLI for dry-run or upload.

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

Do not delegate the rewrite to a hardcoded external AI CLI when this skill is active. Generate the Markdown yourself, then use this repository as the upload executor.
