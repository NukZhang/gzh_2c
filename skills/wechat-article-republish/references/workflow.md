# Workflow

## Recommended Path

### Step 1: Generate Markdown with the host AI tool

The host AI tool should:

- read the source article URL
- read the user's thoughts
- produce a local Markdown file that follows `markdown-contract.md`

### Step 2: Preview with dry-run

Run:

```bash
python3 src/article_pipeline.py upload \
  --url '<article_url>' \
  --markdown <generated.md> \
  --dry-run \
  --output <preview_dir>
```

Inspect:

- `body.html`
- `article.json`
- `image_map.json`

### Step 3: Real upload

If preview looks correct, run:

```bash
python3 src/article_pipeline.py upload \
  --url '<article_url>' \
  --markdown <generated.md>
```

Expected output includes:

- `上传前处理完成: N 张图片`
- `上传完成: N 张图片`
- `草稿创建成功: <media_id>`

## Notes

- The repository handles image extraction, placeholder mapping, cover upload, and WeChat draft submission.
- The repository does not need to know which model generated the Markdown.
- If the AI tool prefers to call the project's built-in AI mode, that is optional and outside this skill's primary workflow.
