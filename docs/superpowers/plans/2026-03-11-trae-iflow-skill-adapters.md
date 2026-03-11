# Trae And iFlow Skill Adapter Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a native iFlow project-memory adapter and a thin Trae skill adapter on top of the existing generic WeChat republish skill system.

**Architecture:** Use root-level `IFLOW.md` for iFlow because the official docs define it as the CLI memory file, and use a thin `skills/trae-wechat-article-republish/SKILL.md` adapter for Trae because there is not enough official evidence for a single canonical Trae root config filename. Keep the generic core skill as the only business-rule source.

**Tech Stack:** Markdown skill files, repo-local references, existing Python CLI

---

## File Map

- Create: `IFLOW.md`
- Create: `skills/trae-wechat-article-republish/SKILL.md`
- Modify: `README.md`
- Modify: `spec/AI2AI/AI2AI.md`

## Chunk 1: Add Adapters

### Task 1: Add the iFlow adapter

**Files:**
- Create: `IFLOW.md`

- [ ] **Step 1: Draft a thin iFlow memory file**

Include:

- short scope statement
- `@` imports of the generic core skill and references
- command flow for dry-run and upload
- explicit instruction that iFlow uses its own model for generation

- [ ] **Step 2: Review for duplication**

Check:

- business rules remain in the core skill
- iFlow-specific content stays limited to memory-file behavior

### Task 2: Add the Trae adapter

**Files:**
- Create: `skills/trae-wechat-article-republish/SKILL.md`

- [ ] **Step 1: Draft the thin Trae adapter**

Include:

- trigger conditions
- instruction to read the generic core skill
- instruction to generate Markdown with Trae itself
- repository CLI commands for preview and upload

- [ ] **Step 2: Review for unsupported assumptions**

Check:

- no invented Trae-specific root filename
- no duplicated Markdown contract

## Chunk 2: Repo Wiring And Verification

### Task 3: Update discoverability and record facts

**Files:**
- Modify: `README.md`
- Modify: `spec/AI2AI/AI2AI.md`

- [ ] **Step 1: Add README pointers**

Add:

- `IFLOW.md`
- `skills/trae-wechat-article-republish/`

- [ ] **Step 2: Verify adapter files exist**

Run:

```bash
find skills -maxdepth 3 -type f | sort
test -f IFLOW.md
```

Expected:

- both new adapter files exist

- [ ] **Step 3: Verify CLI contract is still accurate**

Run:

```bash
python3 src/article_pipeline.py upload --help
```

Expected:

- upload help still matches the documented `--markdown` entrypoint

- [ ] **Step 4: Update AI2AI facts**

Record:

- new adapter files
- official-basis split between iFlow and Trae
- verification commands and outcomes
