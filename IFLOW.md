# WeChat Article Republish For iFlow CLI

@./skills/wechat-article-republish/SKILL.md
@./skills/wechat-article-republish/references/markdown-contract.md
@./skills/wechat-article-republish/references/workflow.md

Use this repository as the deterministic upload backend for WeChat article republishing.

When the user asks to rewrite a WeChat article from a URL and save it to the WeChat draft box:

1. Use your own model to generate the rewritten article as a local Markdown file.
2. Follow the imported Markdown contract exactly.
3. Prefer a dry-run first:

```bash
python3 src/article_pipeline.py upload \
  --url '<article_url>' \
  --markdown <generated.md> \
  --dry-run \
  --output <preview_dir>
```

4. If the preview is acceptable, run the real upload:

```bash
python3 src/article_pipeline.py upload \
  --url '<article_url>' \
  --markdown <generated.md>
```

Do not delegate the rewrite back into this repository when using iFlow through this memory file. The rewrite belongs to iFlow. The repository handles validation, image processing, and draft upload.
