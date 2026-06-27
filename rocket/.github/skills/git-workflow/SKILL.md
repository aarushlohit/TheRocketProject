---
name: git-workflow
description: 'Manage Git workflows including conventional commits, branching strategies, rebasing, and conflict resolution. Use when: git, commit, branch, rebase, merge, pull request, conventional commits, git workflow.'
---

# Git Workflow

## Conventional Commits

Use the conventional commits specification:

| Prefix | When to use |
|--------|-------------|
| `feat:` | A new feature |
| `fix:` | A bug fix |
| `refactor:` | Code change that neither fixes a bug nor adds a feature |
| `docs:` | Documentation only changes |
| `test:` | Adding or correcting tests |
| `chore:` | Maintenance, dependencies, tooling |
| `perf:` | Performance improvement |
| `style:` | Formatting, linting (no code change) |

Format: `<type>(<scope>): <description>`

Examples:
```
feat(auth): add OAuth2 login flow
fix(api): handle null response from user endpoint
refactor(db): extract query builder into separate module
```

## Branch Strategy

- `main` — production-ready code. Protected, no direct pushes.
- `develop` — integration branch for features.
- `feat/<name>` — feature branches off `develop`.
- `fix/<name>` — bug fix branches.
- `chore/<name>` — maintenance branches.

## Workflow

1. Create a feature branch from `develop`: `git checkout -b feat/my-feature develop`
2. Make small, focused commits with conventional messages.
3. Keep branch up to date: `git rebase develop` (preferred) or `git merge develop`.
4. Push and create a pull request.
5. Squash-merge to `develop` after approval.

## Best Practices

- Rebase locally, merge remotely. Never rebase a shared branch.
- Write commit messages that explain *why*, not just *what*.
- Keep PRs small and focused — one feature or fix per PR.
- Use `git status` and `git diff` before committing to review your changes.
