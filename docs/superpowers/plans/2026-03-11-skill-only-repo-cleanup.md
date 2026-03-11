# Skill-Only Repo Cleanup Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce this repository to a WeChat article republish skill product repo while keeping all supported adapters.

**Architecture:** Keep only product code, tests, adapter files, and a minimal packaging script. Rewrite the root README as the main entrypoint, then delete generic SDAC assets and repair any remaining references.

**Tech Stack:** Python, pytest, Markdown docs, shell packaging script

---

## Chunk 1: Rewrite Product Entry Docs

### Task 1: Replace the root README

**Files:**
- Modify: `README.md`
- Reference: `IFLOW.md`
- Reference: `skills/wechat-article-republish/SKILL.md`

- [ ] **Step 1: Rewrite `README.md` as the product entrypoint**

Include:
- repository purpose
- supported adapters
- core CLI commands
- minimal directory map

- [ ] **Step 2: Run reference scan for deleted SDAC paths**

Run:

```bash
rg -n "docs/zh|docs/whitepaper|spec/|spec-team|tools/README|CHANGELOG" README.md IFLOW.md skills iflow src tests tools -S
```

Expected:
- only intentional matches outside kept files, or no matches

## Chunk 2: Delete Generic Template Assets

### Task 2: Remove non-product directories and files

**Files:**
- Delete: `.claude/`
- Delete: `CHANGELOG.md`
- Delete: `docs/README.md`
- Delete: `docs/whitepaper.md`
- Delete: `docs/zh/`
- Delete: `examples/`
- Delete: `res/`
- Delete: `spec/`
- Delete: `spec-team/`
- Delete: `tools/README.md`
- Delete: `tools/checklists/`
- Delete: `tools/templates/`

- [ ] **Step 1: Delete the approved non-product paths**

Use a targeted filesystem command or script that removes only the listed paths.

- [ ] **Step 2: Inspect repository status**

Run:

```bash
git status --short
```

Expected:
- deletions only for the approved paths
- modifications only for keep files touched by the cleanup

## Chunk 3: Repair References and Verify

### Task 3: Fix any broken references in kept files

**Files:**
- Modify: `README.md`
- Modify: any kept file still pointing at deleted paths

- [ ] **Step 1: Scan kept paths for deleted references**

Run:

```bash
rg -n "docs/zh|docs/whitepaper|spec/|spec-team|tools/README|examples/README|res/README|CHANGELOG" README.md IFLOW.md skills iflow src tests tools -S
```

Expected:
- no matches

- [ ] **Step 2: Verify the package script**

Run:

```bash
bash -n tools/package.sh
```

Expected:
- exit code 0

- [ ] **Step 3: Run the test suite**

Run:

```bash
python3 -m pytest -q
```

Expected:
- exit code 0

- [ ] **Step 4: Final repository review**

Run:

```bash
find . -maxdepth 2 \( -path './.git' -o -path './docs/superpowers' \) -prune -o -type f | sed 's#^\./##' | sort
```

Expected:
- only the kept product files remain outside `.git` and `docs/superpowers`
