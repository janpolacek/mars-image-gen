# GitHub publication checklist

This repository is prepared for a public source release, but no GitHub repository has been created or published yet.

Before publishing:

1. Confirm that the repository should be **public**.
2. Inspect `git status --ignored` and confirm generated images, model weights, credentials, LAN addresses, and local ComfyUI paths are untracked.
3. Run `python3 -m py_compile scripts/*.py` and `jq empty workflows/*.json workflows/api/*.json`.
4. Review the initial commit with `git diff --cached --check`.
5. Create the GitHub repository, add the remote, push `main`, then verify the branch with `git ls-remote --heads origin main`.

The generated PNG story set lives locally under `stories/` and is intentionally ignored. It can be curated and licensed separately before any public image release.
