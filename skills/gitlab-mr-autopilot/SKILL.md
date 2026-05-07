---
name: gitlab-mr-autopilot
description: >
  End-to-end GitLab delivery loop for coding agents: commit, push, open or update a Merge Request,
  babysit CI until green, and triage every MR comment (human or bot)—reply in-thread, fix issues, and
  resolve discussions when done. Use this skill whenever the user says ship, finish, open an MR,
  create a merge request, push for review, CI failed, fix the pipeline, green the MR, address review
  comments, resolve threads, or wants work merge-ready on GitLab. Prefer the GitLab MCP server for
  MR/pipeline/job discovery; use glab CLI for logs, discussion lists, resolving threads, and API
  calls MCP does not expose. Default to autonomous execution (commit/push/MR/CI loop) without asking
  permission for each step unless the user restricts you.
---

# GitLab MR Autopilot

Turn finished implementation work into a **merge-ready** GitLab Merge Request: local git hygiene, **commit + push**, **MR creation or linkage**, **CI babysitting** until the latest pipeline succeeds, and a **review-comments loop** until every thread is answered and resolvable threads are **resolved**.

**Bundled resources:**
- `evals/evals.json` — example prompts to validate the skill behavior (optional).

## When this skill applies

Activate for any of these intents (and similar phrasing):

- Shipping: “ship it”, “finish”, “wrap up”, “open MR”, “create merge request”, “push for review”.
- CI: “pipeline failed”, “fix CI”, “green the MR”, “wait for pipeline”, “retry job”.
- Review: “address comments”, “resolve threads”, “reply to the bot”, “MR feedback”.

If the user only asked for a **description** or **draft text** without git actions, do that part only—do not commit unless they asked to ship.

## Mode detection (important for DRY-RUN and focused requests)

Pick the narrowest mode that satisfies the user’s request:

1. **Full ship mode (default):** commit → push → MR → CI loop → comments loop.
2. **CI-only mode:** focus on pipelines/jobs/logs and the minimal fix loop. Mention comment handling only if relevant.
3. **Comments-only mode:** focus on discussions/threads/replies/resolution. Do **not** require pipeline tooling unless the thread explicitly references CI.

In **DRY-RUN** requests, output a concrete **execution plan** (commands + MCP calls) and avoid claiming that CI is green or threads are resolved.

## Principles

1. **Autonomy (default):** After you start the delivery flow, keep going through commit → push → MR → CI → comments until stop conditions are met. Do not ask for permission before each push unless the user said to stop or the change is unusually risky (see **Escalate**).
2. **Evidence before claims:** Never say CI is green or comments are resolved without having checked the latest pipeline and discussion state.
3. **Smallest fix:** Prefer minimal, scoped commits that directly address the failing job or the comment.
4. **No secrets:** Do not commit tokens, `.env`, private keys, or credential-bearing files. If a failure is due to missing secrets in CI, document that in an MR comment and stop—do not fake credentials.
5. **No destructive git without explicit user consent:** Avoid `git push --force` to shared branches; prefer normal commits. If a rebase/force-push is truly required, ask once with a clear reason.

## Compatibility

- **Git** and a GitLab **remote** on the working copy.
- **GitLab MCP** (authenticated): `create_merge_request`, `get_merge_request`, `get_merge_request_pipelines`, `get_pipeline_jobs`, `get_merge_request_diffs`, `get_merge_request_commits`, `manage_pipeline`, etc.
- **`glab`** installed and authenticated (`glab auth status`). Use `glab` for job logs, MR discussions, resolving threads, and REST calls the MCP does not cover.

If `glab` is missing, tell the user to install it and run `glab auth login`; still use MCP where possible.

## 0) Resolve context

Collect and keep handy:

| Value | How |
|--------|-----|
| **Project id** | URL-encoded path from remote (e.g. `group/subgroup/repo`) or numeric id via `glab api projects/:fullpath` |
| **Source branch** | `git branch --show-current` |
| **Target branch** | Default: `main` or `master` or `develop`—use `git remote show origin` / repo convention / `get_merge_request.target_branch` if MR exists |
| **MR IID** | From MCP `get_merge_request` after you know the branch, or `glab mr view -F json`, or MR URL the user pasted |

**Project id for MCP:** MCP tools expect `id` as the project path or id string (see tool schemas).

## 1) Preflight (git + auth)

1. `git status` — working tree must be intentional. If unrelated changes exist, split commits or ask once whether to include them.
2. **Never commit on the default branch** for feature work. If you are on default, create `feat/` or `fix/` branch: `git checkout -b <branch>`.
3. `glab auth status` — must show a valid host and user. If not, instruct login.
4. Confirm remote: `git remote -v` matches the GitLab project you will open the MR against.

## 2) Commit and push

1. Inspect: `git diff` / `git diff --cached`.
2. **Commit message convention:** Follow repo docs (e.g. `AGENTS.md`); otherwise **Conventional Commits** (`feat:`, `fix:`, `chore:`, `ci:`, `docs:`, `test:`).
3. Stage deliberately (prefer explicit paths; avoid blind `git add -A` unless the change set is truly all related).
4. Commit. If multiple unrelated concerns exist, use 2–3 commits max; otherwise one commit is fine.
5. Push: `git push -u origin HEAD` (set upstream if missing).

## 3) Merge Request — create or attach

**If the user gave an MR URL or IID:** fetch it with MCP `get_merge_request` and align your branch to that MR’s `source_branch` if needed.

**If no MR exists yet:**

- **Preferred (MCP):** `create_merge_request` with:
  - `id`: project path
  - `title`: concise, conventional style
  - `source_branch` / `target_branch`
  - `description`: short summary, **what changed**, **how tested**, **risk**, link to issue if any
- **Alternate (`glab`):** `glab mr create --fill` or explicit flags if MCP is unavailable.

**If MR already exists for this branch:** update title/description only if stale (MCP may not expose update—use `glab mr update` if needed).

Record: **MR IID**, **MR web URL**, **project id**.

## 4) CI babysitting loop

**Goal:** Latest pipeline for the MR’s latest commit is **success** (respect allowed failures per project policy—if unsure, treat unexpected red as failure).

### CI-only / DRY-RUN output contract

If you are in **CI-only mode** (or the user explicitly asked about a failing job) and especially in **DRY-RUN**, your output must include:

- The **exact MCP calls** you would run (`get_merge_request_pipelines`, `get_pipeline_jobs`).
- The **exact log command** you would run (`glab ci trace <job-id>`).
- An explicit **commit/push loop** snippet, even if the code change is not shown:

```bash
git status
git diff
git add <paths>
git commit -m "fix(test): <short reason>"
git push -u origin HEAD
```

Do not claim the pipeline is green in DRY-RUN; describe how you would verify it and what you would comment on the MR.

### 4.1 Discover pipeline and jobs

Repeat until green or blocked:

1. MCP `get_merge_request_pipelines` with `id` + `merge_request_iid`.
2. Identify the pipeline for the **latest** MR commit (newest relevant pipeline; prefer MR-detached pipeline if that’s what GitLab reports).
3. MCP `get_pipeline_jobs` with `id` + `pipeline_id`.
4. If any job failed / canceled unexpectedly:
   - Note **job id**, **job name**, **stage**.

### 4.2 Get logs and classify failure

- **`glab ci trace <job-id>`** or **`glab ci view`** on the branch to follow logs.
- Bucket: **lint/format**, **tests**, **build**, **infra/secrets**, **flaky**.

### 4.3 Fix and push

1. Implement the **smallest** fix.
2. Run the **most local equivalent** when cheap (e.g. project’s `make lint` / `make test`)—follow repo docs.
3. Commit and push again.

### 4.4 Wait and poll

- Wait for the new pipeline (sleep/backoff; avoid hammering APIs).
- **`glab ci status`** can summarize current pipeline on the branch.
- Optionally MCP `manage_pipeline` **retry** only for confirmed flakes—do not mask real failures.

### 4.5 Escalate (stop looping)

Stop and post an MR comment if:

- Failure needs **secrets**, **infrastructure**, or **product decision**.
- The same job fails **repeatedly** after two focused fix attempts—summarize findings and ask the user for direction.

## 5) Review comments and discussions loop

**Goal:** Every item on the MR has a **human-readable response**, and every **resolved** issue has its discussion **resolved** in GitLab.

### 5.1 List discussions

Use **`glab`** (MCP work-item notes are not MR-specific in all setups):

```bash
glab mr note list [<mr-iid>] --state unresolved -F json
```

Also scan general comments:

```bash
glab mr view [<mr-iid>] --comments
```

Treat **bots** (SAST, dependency scanning, Code Quality, AI reviewers) like humans: read, fix or justify.

### 5.2 Triage each thread

For each discussion:

1. **Understand** the ask (code change, explanation, test, nit).
2. If you **agree** → implement fix in code, push, wait for CI if the change is non-trivial.
3. If you **disagree** or **cannot reproduce** → reply politely with reasoning; do not argue—cite code or logs.
4. If it’s **informational** (“thanks”, “LGTM”) → reply briefly.

### 5.3 Reply in thread

- Prefer **`glab mr note create`** only when starting a **new** top-level comment if no thread exists.
- For **replies inside an existing discussion**, GitLab needs a note on that discussion. If `glab` in your version does not support inline reply flags, use:

```bash
glab api --method POST \
  "projects/<project_id>/merge_requests/<mr_iid>/discussions/<discussion_id>/notes" \
  --raw-field "body=<your markdown reply>"
```

Use `glab mr note list -F json` to read `discussion_id` / ids from the payload (field names follow GitLab’s JSON; adjust jq paths as printed).

**Always @mention sparingly**; use plain text. Include **commit SHA** when you claim a fix: `Fixed in <short-sha>.`

### 5.4 Resolve threads

When the discussion is **fully addressed** (fix merged on the branch and CI relevant to the change is not worse):

```bash
glab mr note resolve <discussion-id> [<mr-iid>]
```

If the reviewer must re-review a subjective point, leave unresolved with a clear question.

### 5.5 Work-item notes (optional)

If the team tracks MR as a **work item** and the user wants notes there, MCP `create_workitem_note` / `get_workitem_notes` may apply—mirror the same discipline: reply and close the loop.

## 6) Stop conditions (“ready for review”)

You may declare the MR **ready for human review** when:

1. **Latest pipeline** for the MR is **success** (or only allowed failures per policy).
2. **No unresolved discussions** remain **unless** each open thread has an explicit follow-up agreed with the reviewer.
3. MR description is **accurate** relative to the final diff.

Post a short **summary comment** on the MR:

- What shipped
- How CI was validated
- What you intentionally did **not** change (if any)

## Quick command reference

| Task | Command / tool |
|------|----------------|
| Open MR (API) | MCP `create_merge_request` |
| Pipelines | MCP `get_merge_request_pipelines` |
| Jobs | MCP `get_pipeline_jobs` |
| Job log | `glab ci trace <job-id>` |
| List unresolved threads | `glab mr note list --state unresolved -F json` |
| Resolve thread | `glab mr note resolve <discussion-id>` |
| Pipeline retry (flake) | MCP `manage_pipeline` + `retry: true` + `pipeline_id` |

## Mental checklist before you say “done”

- [ ] Pushed all commits?
- [ ] MR exists and points at this branch?
- [ ] Latest pipeline green (verified)?
- [ ] All MR threads answered?
- [ ] Resolved threads marked resolved where appropriate?
- [ ] No secrets in diff?
