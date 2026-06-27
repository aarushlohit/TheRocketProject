---
name: code-review
description: 'Review code changes for correctness, security, performance, and code quality. Use when: review code, code review, review this change, review diff, check my code, code quality review, review my PR.'
---

# Code Review

Expert code reviewer combining rigorous analysis with deep expertise in clarity, consistency, and maintainability. Prioritize readable, explicit code over overly compact solutions while ensuring correctness and security.

## When to Use

- User asks to review a diff, code changes, commits, or perform a code review
- Input can be: (1) a text diff pasted directly, (2) one or more git commit hashes, or (3) a git range like abc123..def456

## Workflow

### Step 1: Obtain the diff

- If the user provided a text diff, use it directly.
- If the user provided commit hashes, extract the diff with git:
  ```bash
  git diff "<commit>^..<commit>"
  git diff "<commit1>..<commit2>"
  git diff "<range>"
  ```

### Step 2: Analyze the diff

Focus on these dimensions in order:

1. **Correctness** — Does the code do what it's supposed to? Any logic errors, race conditions, or edge cases missed?
2. **Security** — Any injection risks, data exposure, auth bypasses, or dependency vulnerabilities?
3. **Performance** — Any N+1 queries, unnecessary allocations, or blocking operations in async paths?
4. **Code quality** — Is the code readable, well-named, and maintainable? Are functions small and focused?
5. **Test coverage** — Are there tests for the new code? Do they cover the failure modes?

### Step 3: Provide feedback

- Categorize issues: **Blocking** (must fix), **Should fix** (recommended), **Nitpick** (optional).
- Explain the *why* behind each comment.
- Suggest specific fixes for blocking issues.
- Be respectful — assume good intent.

## Review Checklist

- [ ] No hardcoded secrets, tokens, or credentials
- [ ] Input validation on all external data
- [ ] Proper error handling (no silent failures)
- [ ] No commented-out code or debug artifacts
- [ ] Functions are single-purpose and reasonably sized
- [ ] Naming is descriptive and consistent
- [ ] Tests cover the new/changed behavior
