---
name: doc-version-updater
description: Automatically audit, update, and bump documentation (CHANGELOG.md, README.md) and version files (VERSION, package.json, pyproject.toml, build.gradle) following Luma core patterns. Trigger when preparing a release, completing an MR/PR, or updating project documentation.
---

# Documentation & Version Updater Skill (Luma Engine Pattern)

Use this skill whenever completing a major feature, MR, or release to audit and synchronize project documentation (`CHANGELOG.md`, `README.md`) and version files (`VERSION`, `package.json`, `pyproject.toml`, etc.).

---

## 🎯 Purpose & Capabilities

Based on the Luma release management engine (`luma_core/tools.py`), this skill automates:
1. **Incremental Changelog Entry**: Prepend new release entries in [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.
2. **README Synchronization**: Audit and update setup instructions, API endpoints, or architecture diagrams based on actual code diffs.
3. **Semantic Version Bumping**: Detect current version, propose SemVer (PATCH / MINOR / MAJOR), update version files, and ensure `VERSION` matches `CHANGELOG.md`.

---

## 🛑 STRICT RULE: PER-MR ISOLATED UPDATES
- **NO BATCHED DOCUMENTATION**: Never generate documentation or version updates for multiple MRs/branches in a single commit.
- **ISOLATED MR SCOPE**: Each MR/PR branch MUST modify `CHANGELOG.md`, `README.md`, and `VERSION` strictly and exclusively for the changes introduced within **that specific MR's scope**.
- **INCREMENTAL VERSIONING PER MR**: Increment the version number per MR (e.g. `v0.59.0` for MR 5, `v0.60.0` for MR 6) so that each merged MR carries its own version bump and changelog section independently.

---

## 📋 Standard Workflow Procedure

### Step 1: Gather Git & Code Diff Data
Examine commit history and changed files since the last release/tag:
```bash
git log $(git describe --tags --abbrev=0 2>/dev/null || echo "HEAD~10")..HEAD --oneline
git diff --stat $(git describe --tags --abbrev=0 2>/dev/null || echo "HEAD~10")..HEAD
```

### Step 2: Update `CHANGELOG.md`
- Locate or create `CHANGELOG.md` with standard header if missing.
- Format new entry under `## [X.Y.Z] - YYYY-MM-DD` or `## [Unreleased]`.
- Categorize changes into:
  - `### Added`: New features
  - `### Changed`: Changes in existing functionality
  - `### Fixed`: Bug fixes
  - `### Security`: Security hardening / vulnerabilities

### Step 3: Synchronize `README.md`
- Inspect if modified files introduce new environment variables, new endpoints, or CLI options.
- Update `README.md` sections without modifying existing formatting or unrelated text.

### Step 4: Version Bumping (`VERSION` & Source Files)
1. Read current version from `VERSION`, `package.json`, or `pyproject.toml`.
2. Determine SemVer bump:
   - **PATCH** (`X.Y.Z+1`): Backward-compatible bug fixes
   - **MINOR** (`X.Y+1.0`): Backward-compatible new features
   - **MAJOR** (`X+1.0.0`): Breaking changes
3. Update `VERSION` file and sync the exact version string across `CHANGELOG.md` header.

---

## 🛠️ Checklist Before Finalizing
- [ ] Version in `VERSION` file strictly matches `CHANGELOG.md` header.
- [ ] No version number collision with existing released tags.
- [ ] `README.md` reflects any new CLI flags, endpoints, or environment variables introduced.
