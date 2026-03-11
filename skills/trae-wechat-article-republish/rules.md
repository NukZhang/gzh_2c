# Trae Rules Snippet

当任务是“公众号链接二创并入草稿箱”时：

- 用 Trae 自己的模型生成 Markdown，不要把创作委托给本仓库。
- Markdown 必须包含 YAML frontmatter、`title`、`content_source_url`、`cover_image`，正文图片只用 `{{imageN}}`。
- 默认先预览：

```bash
python3 src/article_pipeline.py upload --url '<article_url>' --markdown <generated.md> --dry-run --output <preview_dir>
```

- 用户确认后再真实上传：

```bash
python3 src/article_pipeline.py upload --url '<article_url>' --markdown <generated.md>
```

- Markdown 不合规时，先修正文稿，再上传。
