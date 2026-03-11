# WeChat Article Republish Skills

这个仓库专门用于“公众号链接二创并进入公众号草稿箱”。

仓库职责很明确：

- 读取公众号原文和图片
- 校验二创 Markdown 是否符合上传约定
- 生成 dry-run 预览产物
- 上传图片并创建公众号草稿
- 为多种 AI 宿主提供统一的 skill / adapter 入口

创作本身由宿主 AI 完成；这个仓库负责确定性的处理、校验和上传。

## Supported Adapters

- 通用核心 skill：`skills/wechat-article-republish/`
- Codex / Claude Code：`skills/codex-wechat-article-republish/`
- Trae：`skills/trae-wechat-article-republish/`
- iFlow CLI：`IFLOW.md`

## Quick Start

1. 安装依赖：

   ```bash
   python3 -m pip install -r requirements.txt
   ```

2. 准备 `wechat.yml`，写入公众号 `appid`、`secret`，可选 `author`。
3. 让宿主 AI 先产出符合约定的 Markdown，或直接使用自动改写模式。

## Core Commands

分析原文图片：

```bash
python3 src/article_pipeline.py analyze \
  --url '<article_url>' \
  --output .tmp/article_analysis
```

用已有 Markdown 做 dry-run 预览：

```bash
python3 src/article_pipeline.py upload \
  --url '<article_url>' \
  --markdown <generated.md> \
  --dry-run \
  --output .tmp/preview
```

确认预览后真实上传：

```bash
python3 src/article_pipeline.py upload \
  --url '<article_url>' \
  --markdown <generated.md>
```

使用本地 AI CLI 自动生成草稿：

```bash
python3 src/article_pipeline.py upload \
  --url '<article_url>' \
  --thought '这里写你的观点' \
  --ai-command 'codex exec --skip-git-repo-check --color never' \
  --dry-run \
  --output .tmp/preview
```

自动改写模式默认使用的人设文件在 `skills/wechat-article-republish/references/persona.md`。

## Directory Map

- `src/`: CLI、Markdown 校验、原文抓取、图片处理、上传逻辑
- `tests/`: pipeline、draft、source、AI rewrite 相关测试
- `skills/`: 通用 skill 与适配器
- `iflow/examples/`: iFlow 对话示例
- `tools/package.sh`: 打包脚本
- `docs/superpowers/`: 本仓库内部保留的设计和计划记录

## Main Entry Files

- 通用 skill：`skills/wechat-article-republish/SKILL.md`
- Markdown 约定：`skills/wechat-article-republish/references/markdown-contract.md`
- 命令流程：`skills/wechat-article-republish/references/workflow.md`
- iFlow 入口：`IFLOW.md`
- iFlow 示例：`iflow/examples/wechat-article-republish.md`

## License

MIT，见 `LICENSE`。
