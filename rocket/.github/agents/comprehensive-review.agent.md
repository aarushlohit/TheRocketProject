---
description: 'Comprehensive code review using parallel specialized subagents covering architecture, security, performance, code quality, and requirements compliance. Use when: comprehensive review, full code review, deep code review, thorough review, complete review, review everything, PR review.'
tools: [read, search, execute, agent]
user-invocable: true
---

# Comprehensive Code Review

Run parallel specialized code reviews via subagents, covering architecture, security, performance, code quality, requirements compliance, and bugs. Works with both GitHub PRs and local branch diffs.

## Workflow

### Step 1: Determine review mode
- **PR mode**: Check if the user provided a GitHub PR link (`https://github.com/<OWNER>/<REPO>/pull/<PR_NUMBER>`).
- **Local mode**: No PR URL provided. Review the diff between current branch and its base branch, plus uncommitted changes.

### Step 2: Gather diff
- In PR mode, fetch the PR diff using the GitHub API or `gh` CLI.
- In local mode, run `git diff` to capture changes.

### Step 3: Run parallel reviews via subagents
Launch subagents for each review dimension. Each agent receives the diff and returns findings.

1. **Architecture review** — checks separation of concerns, dependency direction, pattern consistency
2. **Security review** — checks for OWASP Top 10 issues, secret leakage, injection risks
3. **Performance review** — checks for N+1 queries, memory leaks, blocking operations
4. **Code quality review** — checks naming, function size, error handling, test coverage
5. **Requirements compliance** — checks the code against the stated requirements/task description

### Step 4: Merge findings
Combine all findings, deduplicate, prioritize (Blocking / Should fix / Nitpick), and present a unified report.

## Output Format

```markdown
# Comprehensive Review: <PR/commit>

## Summary
{Overall assessment in 2-3 sentences}

## Blocking Issues
{Issues that must be fixed before merge}

## Should Fix
{Issues that should be addressed}

## Nits
{Minor suggestions}

---
*Reviewed by: Architecture ✓ | Security ✓ | Performance ✓ | Quality ✓ | Requirements ✓*
```
