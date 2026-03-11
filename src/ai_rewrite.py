import os
import re
import shlex
import subprocess
import tempfile
from pathlib import Path

import article_drafts


ARTICLE_AI_COMMAND_ENV = "ARTICLE_AI_COMMAND"
DEFAULT_PERSONA_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "wechat-article-republish"
    / "references"
    / "persona.md"
)
REPO_ROOT = Path(__file__).resolve().parents[1]


def load_persona_text(persona_path=DEFAULT_PERSONA_PATH):
    return Path(persona_path).read_text(encoding="utf-8").strip()


def build_rewrite_prompt(source_article, thought_text, source_url, persona_path=DEFAULT_PERSONA_PATH):
    persona_text = load_persona_text(persona_path)
    available_images = ", ".join(source_article.get("image_keys") or []) or "无"
    normalized_thought = thought_text if thought_text != "" else "用户未提供额外思考，请仅基于原文完成二次创作。"

    return """你要把一篇公众号文章改写成新的公众号草稿，输出必须是可直接上传的 Markdown。

【写作人设与约束】
{persona_text}

【硬性要求】
1. 只能基于原文事实，不得虚构原文没有的信息。
2. 输出必须只有 Markdown，不要解释，不要代码块围栏。
3. Markdown 必须以 YAML frontmatter 开头。
4. frontmatter 至少要有 `title`。
5. `content_source_url` 必须写成：{source_url}
6. 正文里如需插图，只能使用这些占位符：{available_images}
7. 占位符格式必须是 `{{{{imageN}}}}`，不要改名。
8. 如果使用图片，封面图必须能对应到正文中的某个占位符。
9. 正文必须有真实文字内容，不能只输出标题和图片。

【用户思考】
{normalized_thought}

【原文标题】
{title}

【原文正文（已按 source 顺序插入图片占位符）】
{body_markdown}

【输出格式示例】
---
title: 新标题
content_source_url: {source_url}
cover_image: image1
---

正文第一段。

{{{{image1}}}}

正文第二段。
""".format(
        persona_text=persona_text,
        source_url=source_url,
        available_images=available_images,
        normalized_thought=normalized_thought,
        title=source_article["title"],
        body_markdown=source_article["body_markdown"],
    )


def resolve_ai_command(ai_command=None, env=None):
    environment = env or os.environ
    command = ai_command if ai_command is not None else environment.get(ARTICLE_AI_COMMAND_ENV)
    if not command or not command.strip():
        raise ValueError(
            "AI command is required; pass --ai-command or set {}".format(ARTICLE_AI_COMMAND_ENV)
        )
    return command.strip()


def _is_codex_exec(args):
    if len(args) < 2:
        return False
    return Path(args[0]).name == "codex" and args[1] == "exec"


def _find_output_file_arg(args):
    for index, value in enumerate(args[:-1]):
        if value in {"-o", "--output-last-message"}:
            return args[index + 1]
    return None


def _prepare_command_args(command):
    args = shlex.split(command)
    if not args:
        raise ValueError("AI command is empty")

    output_file_path = _find_output_file_arg(args)
    cleanup_output_file = False

    if _is_codex_exec(args) and output_file_path is None:
        handle = tempfile.NamedTemporaryFile(prefix="codex-last-message-", suffix=".txt", delete=False)
        handle.close()
        output_file_path = handle.name
        args[2:2] = ["-o", output_file_path]
        cleanup_output_file = True

    return args, output_file_path, cleanup_output_file


def run_ai_command(command, prompt_text, cwd=REPO_ROOT):
    args, output_file_path, cleanup_output_file = _prepare_command_args(command)

    result = subprocess.run(
        args,
        input=prompt_text,
        text=True,
        capture_output=True,
        cwd=str(cwd),
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError("AI command failed: {}".format(detail or result.returncode))

    markdown_text = ""
    if output_file_path:
        output_file = Path(output_file_path)
        if output_file.exists():
            markdown_text = output_file.read_text(encoding="utf-8").strip()
            if cleanup_output_file:
                output_file.unlink()

    if not markdown_text:
        markdown_text = result.stdout.strip()
    if not markdown_text:
        raise RuntimeError("AI command returned empty output")
    return markdown_text


def validate_generated_markdown(markdown_text, fallback_source_url=None, available_image_keys=None):
    draft = article_drafts.load_markdown_draft_text(
        markdown_text,
        fallback_source_url=fallback_source_url,
    )

    if available_image_keys is None:
        return draft

    allowed_keys = set(available_image_keys)
    placeholders = set(re.findall(r"\{\{(image\d+)\}\}", draft["body"]))
    invalid = sorted(placeholders - allowed_keys)
    if invalid:
        raise ValueError(
            "generated markdown references unavailable images: {}".format(", ".join(invalid))
        )

    cover_image = draft["meta"].get("cover_image")
    if cover_image and cover_image not in allowed_keys:
        raise ValueError(
            "generated markdown references unavailable cover image: {}".format(cover_image)
        )

    return draft


def generate_markdown_draft(
    source_article,
    source_url,
    thought_text="",
    ai_command=None,
    persona_path=DEFAULT_PERSONA_PATH,
    env=None,
    cwd=REPO_ROOT,
):
    prompt_text = build_rewrite_prompt(
        source_article=source_article,
        thought_text=thought_text,
        source_url=source_url,
        persona_path=persona_path,
    )
    command = resolve_ai_command(ai_command=ai_command, env=env)
    markdown_text = run_ai_command(command, prompt_text, cwd=cwd)
    draft = validate_generated_markdown(
        markdown_text,
        fallback_source_url=source_url,
        available_image_keys=source_article.get("image_keys"),
    )
    return {
        "command": command,
        "prompt": prompt_text,
        "markdown": markdown_text,
        "draft": draft,
    }
