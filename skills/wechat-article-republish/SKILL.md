---
name: wechat-article-republish
description: Use when an AI tool needs to rewrite a WeChat article from a source URL, incorporate user thoughts, and send the result to a WeChat draft box through this project.
---

# WeChat Article Republish

Use this skill when the task is "公众号链接二创并入草稿箱".

This repository is the deterministic upload backend. The host AI tool must use its own model to generate the article Markdown, then hand that Markdown to this project for dry-run or upload.

## When To Use

Use this skill when the user wants any of the following:

- rewrite a WeChat article from a URL
- combine a source article with personal thoughts
- preview or upload a rewritten article to the WeChat draft box

Do not use this skill for:

- direct publishing outside WeChat drafts
- non-WeChat platforms
- pure writing tasks that do not need image processing or draft upload

## Required Workflow

1. Read the source article and user thoughts.
2. Generate a new article with the host AI tool's own model.
3. Write the generated result to a local Markdown file.
4. Run this project's CLI in `--dry-run` mode first unless the user explicitly wants direct upload.
5. If the preview is acceptable, run the real upload.

## Markdown Contract

Read [references/markdown-contract.md](references/markdown-contract.md) before generating the article file.

The generated Markdown must follow the contract exactly:

- YAML frontmatter
- `title`
- `content_source_url`
- `cover_image`
- body text with `{{imageN}}` placeholders

## Execution Commands

Read [references/workflow.md](references/workflow.md) for the exact command flow.

The project CLI entrypoint is:

```bash
python3 src/article_pipeline.py upload --url <article_url> --markdown <generated.md>
```

## Key Rule

Do not ask this project to do the creative writing when operating through this skill. The host AI tool owns the rewrite. This project owns image handling, validation, and WeChat draft submission.
