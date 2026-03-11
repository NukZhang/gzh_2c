# AI CLI Article Rewrite Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an automatic rewrite path that accepts a WeChat article URL plus optional user thoughts, invokes a local AI CLI to generate Markdown, and reuses the current draft upload pipeline.

**Architecture:** Introduce one module for source article extraction and one module for AI CLI orchestration, then extend `src/article_pipeline.py` to support a second upload input mode. Keep Markdown parsing, image handling, and WeChat upload behavior in the existing modules.

**Tech Stack:** Python, pytest, requests, existing WeChat upload helpers, local shell AI CLI

---

## File Map

- Create: `src/article_source.py`
  - Extract title and body blocks from article HTML
  - Build rewrite-ready source payload with `{{imageN}}` placeholders
- Create: `src/ai_rewrite.py`
  - Read persona text
  - Build prompt
  - Invoke AI CLI
  - Validate generated Markdown
- Modify: `src/article_pipeline.py`
  - Add new CLI flags
  - Add automatic rewrite branch
  - Preserve current Markdown branch
- Modify: `tests/test_article_pipeline.py`
  - Cover new CLI branch and arg validation
- Create: `tests/test_article_source.py`
  - Cover source extraction
- Create: `tests/test_ai_rewrite.py`
  - Cover prompt building and AI CLI invocation
- Modify: `spec/AI2AI/AI2AI.md`
  - Record implementation facts and verification evidence after code is complete

## Chunk 1: Source Article Extraction

### Task 1: Add failing tests for title and body extraction

**Files:**
- Create: `tests/test_article_source.py`
- Create: `src/article_source.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_extract_source_article_prefers_msg_title_and_body_blocks():
    html = """
    <script>var msg_title = '示例标题'.html(false);</script>
    <div id="js_content">
      <p>第一段</p>
      <h2>小标题</h2>
      <figure><img class="rich_pages wxw-img" data-src="https://mmbiz.qpic.cn/1"/></figure>
      <p>第二段</p>
    </div>
    """

    source = article_source.extract_source_article(html)

    assert source["title"] == "示例标题"
    assert source["body_markdown"] == "第一段\n\n## 小标题\n\n{{image1}}\n\n第二段"
```

```python
def test_extract_source_article_falls_back_to_og_title():
    html = '''
    <meta property="og:title" content="后备标题" />
    <div id="js_content"><p>正文</p></div>
    '''

    source = article_source.extract_source_article(html)

    assert source["title"] == "后备标题"
```

```python
def test_extract_source_article_requires_real_text():
    html = '<div id="js_content"><figure><img class="rich_pages wxw-img" data-src="https://mmbiz.qpic.cn/1"/></figure></div>'

    with pytest.raises(ValueError, match="source body"):
        article_source.extract_source_article(html)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_article_source.py -q`
Expected: FAIL because `article_source.py` does not exist yet

- [ ] **Step 3: Write minimal implementation**

Implement:

- `extract_source_article(html)`
- title helpers for `msg_title` then `og:title`
- `#js_content` extraction
- block normalization for paragraphs, `h2`, and rich-pages images
- `body_markdown` assembly with ordered `{{imageN}}` placeholders

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_article_source.py -q`
Expected: PASS

## Chunk 2: AI CLI Prompting and Validation

### Task 2: Add failing tests for prompt composition and command execution

**Files:**
- Create: `tests/test_ai_rewrite.py`
- Create: `src/ai_rewrite.py`

- [ ] **Step 1: Write the failing tests**

```python
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
```

```python
def test_run_ai_command_reads_stdout_markdown(monkeypatch):
    class Result:
        returncode = 0
        stdout = "---\\ntitle: 新标题\\n---\\n\\n正文"
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Result())

    markdown = ai_rewrite.run_ai_command("codex exec", "prompt")

    assert markdown.startswith("---")
```

```python
def test_validate_generated_markdown_requires_title():
    with pytest.raises(ValueError, match="title"):
        ai_rewrite.validate_generated_markdown("---\\ncontent_source_url: x\\n---\\n\\n正文")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_ai_rewrite.py -q`
Expected: FAIL because `ai_rewrite.py` does not exist yet

- [ ] **Step 3: Write minimal implementation**

Implement:

- `build_rewrite_prompt(...)`
- `run_ai_command(command, prompt_text)`
- `validate_generated_markdown(markdown_text, fallback_source_url=None)`
- command parsing with `shlex.split`
- stdin/stdout shell contract
- generated draft validation by reusing `article_drafts.load_markdown_draft`

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_ai_rewrite.py -q`
Expected: PASS

## Chunk 3: CLI Rewrite Orchestration

### Task 3: Add failing tests for automatic rewrite dry-run and upload

**Files:**
- Modify: `tests/test_article_pipeline.py`
- Modify: `src/article_pipeline.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_upload_dry_run_generates_markdown_via_ai_cli(tmp_path, monkeypatch):
    import article_pipeline

    captured = {}
    monkeypatch.setattr(article_tools, "fetch_article_html", lambda *args, **kwargs: "<html>...</html>")
    monkeypatch.setattr(article_source, "extract_source_article", lambda html: {"title": "原文标题", "body_markdown": "原文\\n\\n{{image1}}"})
    monkeypatch.setattr(ai_rewrite, "generate_markdown_draft", lambda **kwargs: captured.setdefault("called", kwargs) or "---\\ntitle: 新标题\\n---\\n\\n正文\\n\\n{{image1}}")
    monkeypatch.setattr(article_tools, "prepare_article_images", lambda *args, **kwargs: processed_result)

    exit_code = article_pipeline.main([
        "upload",
        "--url", "https://mp.weixin.qq.com/s/example",
        "--thought", "我的思考",
        "--dry-run",
        "--output", str(tmp_path / "preview"),
    ])

    assert exit_code == 0
    assert (tmp_path / "preview" / "generated.md").exists()
```

```python
def test_upload_mode_rejects_markdown_and_thought_together():
    import article_pipeline

    with pytest.raises(SystemExit):
        article_pipeline.main([
            "upload",
            "--url", "https://mp.weixin.qq.com/s/example",
            "--markdown", "draft.md",
            "--thought", "x",
        ])
```

```python
def test_upload_mode_submits_generated_draft(tmp_path, monkeypatch):
    import article_pipeline

    # mock source extraction, AI output, image processing, and WeChat uploads
    # assert final uploaded article title/content come from generated Markdown
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_article_pipeline.py::test_upload_dry_run_generates_markdown_via_ai_cli tests/test_article_pipeline.py::test_upload_mode_rejects_markdown_and_thought_together tests/test_article_pipeline.py::test_upload_mode_submits_generated_draft -q`
Expected: FAIL because the CLI does not support the automatic rewrite path yet

- [ ] **Step 3: Write minimal implementation**

Implement in `src/article_pipeline.py`:

- new flags:
  - `--thought`
  - `--thought-file`
  - `--ai-command`
- input mode validation
- helper to read thought text
- automatic rewrite branch:
  - fetch source HTML
  - extract source article
  - generate Markdown draft
  - optionally write `source.json`, `prompt.txt`, and `generated.md`
  - reuse existing upload path behavior after draft generation

- [ ] **Step 4: Run targeted tests to verify they pass**

Run: `python3 -m pytest tests/test_article_pipeline.py::test_upload_dry_run_generates_markdown_via_ai_cli tests/test_article_pipeline.py::test_upload_mode_rejects_markdown_and_thought_together tests/test_article_pipeline.py::test_upload_mode_submits_generated_draft -q`
Expected: PASS

## Chunk 4: Full Verification and Fact Updates

### Task 4: Run the complete verification suite

**Files:**
- Modify: `spec/AI2AI/AI2AI.md`

- [ ] **Step 1: Run the new focused tests**

Run: `python3 -m pytest tests/test_article_source.py tests/test_ai_rewrite.py -q`
Expected: PASS

- [ ] **Step 2: Run the full relevant suite**

Run: `python3 -m pytest tests/test_article_pipeline.py tests/test_article_drafts.py tests/test_draft_upload.py tests/test_article_source.py tests/test_ai_rewrite.py -q`
Expected: PASS

- [ ] **Step 3: Run compile verification**

Run: `python3 -m py_compile src/article_pipeline.py src/article_drafts.py src/article_tools.py src/draft_upload.py src/article_source.py src/ai_rewrite.py`
Expected: PASS

- [ ] **Step 4: Run a dry-run smoke check with the provided article URL**

Run:

```bash
ARTICLE_AI_COMMAND='your-ai-cli-command' \
python3 src/article_pipeline.py upload \
  --url 'https://mp.weixin.qq.com/s/101JT4crNZbak8zF9g2rdA' \
  --thought '' \
  --dry-run \
  --output .tmp/ai_cli_article_rewrite_smoke
```

Expected:

- `generated.md` exists
- `article.json` exists
- no WeChat upload API calls are made

- [ ] **Step 5: Update `spec/AI2AI/AI2AI.md` with facts only**

Record:

- implementation status
- new modules and CLI behavior
- verification commands
- verification outcomes
- known limits around AI CLI command availability

- [ ] **Step 6: Final review**

Confirm:

- current Markdown upload path still works
- automatic rewrite path is dry-run capable without WeChat writes
- AI output is validated before any upload calls
