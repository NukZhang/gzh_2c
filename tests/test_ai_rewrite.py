from pathlib import Path
import subprocess

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import ai_rewrite


def test_default_persona_path_uses_kept_skill_reference():
    path_text = str(ai_rewrite.DEFAULT_PERSONA_PATH)

    assert "skills/wechat-article-republish/references/persona.md" in path_text
    assert ai_rewrite.DEFAULT_PERSONA_PATH.exists()


def test_build_prompt_includes_persona_source_and_thought(tmp_path):
    persona = tmp_path / "persona.md"
    persona.write_text("人设规则", encoding="utf-8")

    prompt = ai_rewrite.build_rewrite_prompt(
        source_article={"title": "原文标题", "body_markdown": "正文\n\n{{image1}}"},
        thought_text="我的看法",
        source_url="https://mp.weixin.qq.com/s/example",
        persona_path=persona,
    )

    assert "人设规则" in prompt
    assert "原文标题" in prompt
    assert "我的看法" in prompt
    assert "{{image1}}" in prompt
    assert "https://mp.weixin.qq.com/s/example" in prompt


def test_run_ai_command_reads_stdout_markdown(monkeypatch):
    class Result:
        returncode = 0
        stdout = "---\ntitle: 新标题\n---\n\n正文"
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Result())

    markdown = ai_rewrite.run_ai_command("codex exec -", "prompt")

    assert markdown.startswith("---")


def test_run_ai_command_reads_codex_output_file(monkeypatch, tmp_path):
    def fake_run(args, input=None, text=None, capture_output=None, cwd=None):
        output_path = args[args.index("-o") + 1]
        Path(output_path).write_text("---\ntitle: 新标题\n---\n\n正文", encoding="utf-8")

        class Result:
            returncode = 0
            stdout = "OpenAI Codex header"
            stderr = ""

        return Result()

    monkeypatch.setattr(subprocess, "run", fake_run)

    markdown = ai_rewrite.run_ai_command("codex exec --skip-git-repo-check", "prompt", cwd=tmp_path)

    assert markdown.startswith("---")


def test_run_ai_command_raises_on_non_zero_exit(monkeypatch):
    class Result:
        returncode = 1
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Result())

    with pytest.raises(RuntimeError, match="boom"):
        ai_rewrite.run_ai_command("codex exec -", "prompt")


def test_validate_generated_markdown_requires_title():
    with pytest.raises(ValueError, match="title"):
        ai_rewrite.validate_generated_markdown(
            "---\ncontent_source_url: https://example.com\ncover_image: image1\n---\n\n正文",
            available_image_keys=["image1"],
        )


def test_validate_generated_markdown_rejects_unavailable_images():
    with pytest.raises(ValueError, match="unavailable"):
        ai_rewrite.validate_generated_markdown(
            "---\ntitle: 新标题\ncontent_source_url: https://example.com\ncover_image: image2\n---\n\n正文\n\n{{image2}}",
            available_image_keys=["image1"],
        )
