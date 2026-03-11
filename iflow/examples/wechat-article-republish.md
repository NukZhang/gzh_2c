# iFlow Example

User:

```text
请根据这篇公众号文章链接做一篇二创，加入我对 AI 工具工作流的看法，先预览，确认后再发到公众号草稿箱。
链接：https://mp.weixin.qq.com/s/101JT4crNZbak8zF9g2rdA
```

Expected iFlow flow:

1. Read `IFLOW.md`.
2. Use iFlow 自己的模型生成合规 Markdown，例如 `.tmp/generated_article.md`。
3. 先预览：

```bash
python3 src/article_pipeline.py upload --url 'https://mp.weixin.qq.com/s/101JT4crNZbak8zF9g2rdA' --markdown .tmp/generated_article.md --dry-run --output .tmp/iflow_preview
```

4. 用户确认后再上传：

```bash
python3 src/article_pipeline.py upload --url 'https://mp.weixin.qq.com/s/101JT4crNZbak8zF9g2rdA' --markdown .tmp/generated_article.md
```
