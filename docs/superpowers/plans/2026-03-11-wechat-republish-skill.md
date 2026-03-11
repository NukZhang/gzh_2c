# WeChat Republish Skill Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a generic repo-local skill plus a thin Codex/Claude Code adapter so external AI tools can generate Markdown themselves and use this project as the deterministic WeChat upload backend.

**Architecture:** Create one generic core skill under `skills/wechat-article-republish/` and one thin adapter skill under `skills/codex-wechat-article-republish/`. Keep the project CLI as the execution backend and avoid binding the workflow to a specific model provider.

**Tech Stack:** Markdown skill files, existing Python CLI, repo-local references

---

## File Map

- Create: `skills/wechat-article-republish/SKILL.md`
  - generic workflow definition
- Create: `skills/wechat-article-republish/references/markdown-contract.md`
  - exact Markdown requirements for generated article files
- Create: `skills/wechat-article-republish/references/workflow.md`
  - dry-run and real upload command flow
- Create: `skills/codex-wechat-article-republish/SKILL.md`
  - thin host-tool adapter
- Modify: `README.md`
  - add a short note pointing to the new skill workflow
- Modify: `spec/AI2AI/AI2AI.md`
  - record skill packaging facts and verification evidence

## Chunk 1: Generic Core Skill

### Task 1: Create the generic skill and references

**Files:**
- Create: `skills/wechat-article-republish/SKILL.md`
- Create: `skills/wechat-article-republish/references/markdown-contract.md`
- Create: `skills/wechat-article-republish/references/workflow.md`

- [ ] **Step 1: Draft the generic skill**

The skill must:

- trigger on WeChat article rewrite and draft-upload tasks
- state that the AI tool should use its own model for generation
- refer to the Markdown contract and workflow references

- [ ] **Step 2: Draft the Markdown contract reference**

Include:

- required frontmatter fields
- allowed placeholder format
- cover image rules
- dry-run artifact expectations

- [ ] **Step 3: Draft the workflow reference**

Include:

- generate Markdown with the host tool
- run `--dry-run`
- inspect output
- run real upload

- [ ] **Step 4: Review for duplication and portability**

Check:

- no hardcoded provider dependency
- no duplicated business logic from project code
- no host-specific instructions in the generic layer

## Chunk 2: Tool Adapter Skill

### Task 2: Create the thin Codex/Claude Code adapter

**Files:**
- Create: `skills/codex-wechat-article-republish/SKILL.md`

- [ ] **Step 1: Draft the adapter skill**

The adapter must:

- trigger on the right task phrasing
- tell the host tool to generate Markdown with its own model
- instruct the host tool to read the generic core skill
- point to the project CLI for dry-run and upload

- [ ] **Step 2: Ensure the adapter stays thin**

Check:

- no full Markdown schema duplication
- no copied workflow text that belongs in the core skill

## Chunk 3: Repo Wiring and Verification

### Task 3: Add discoverability and verify the workflow documentation

**Files:**
- Modify: `README.md`
- Modify: `spec/AI2AI/AI2AI.md`

- [ ] **Step 1: Add a concise README pointer**

Add one short section pointing users to:

- `skills/wechat-article-republish/`
- `skills/codex-wechat-article-republish/`

- [ ] **Step 2: Verify command references are accurate**

Run:

```bash
python3 src/article_pipeline.py upload --help
```

Expected:

- help output still shows the upload entrypoint needed by the skill workflow

- [ ] **Step 3: Verify the Markdown contract matches implementation**

Review against:

- `src/article_drafts.py`
- `src/article_pipeline.py`

Confirm:

- frontmatter rules match implementation
- placeholder rules match implementation
- dry-run behavior description is accurate

- [ ] **Step 4: Update `spec/AI2AI/AI2AI.md` with facts only**

Record:

- new skill directories
- generic-vs-adapter split
- verification commands
- verification outcomes

- [ ] **Step 5: Final verification**

Run:

```bash
python3 src/article_pipeline.py upload --help
python3 -m py_compile src/article_pipeline.py src/article_drafts.py src/article_source.py src/ai_rewrite.py
```

Expected:

- help output succeeds
- compilation succeeds
