# Product and Engineering Rules

## Delivery workflow
- Never push directly to main.
- Each Linear issue gets exactly one branch and one pull request.
- Include the Linear issue ID in the branch name and PR title.
- Keep changes limited to the assigned issue.
- Do not start blocked work.

## Quality requirements
- Run tests, lint, and build before opening a PR.
- Add or update tests when behavior changes.
- Do not add secrets, API keys, or private credentials to the repository.
- Explain any untested or incomplete work in the PR.

## Pull request format
Every PR description must include:
- Linear issue ID
- What changed
- How it was tested
- Risks or follow-up work
