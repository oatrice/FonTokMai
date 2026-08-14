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

## 🛑 STRICT RULE: PER-MR ISOLATED UPDATES (ONE VERSION BUMP PER MR)
- **NO MULTIPLE VERSION BUMPS WITHIN THE SAME MR**: When working within an active feature branch or Merge Request (MR), **DO NOT** bump the version number repeatedly for minor commits or follow-ups. All commits and changes made inside the **SAME branch/MR MUST share a single Version and Changelog section**.
- **ONE VERSION BUMP PER MR**: The version bump (e.g. `v0.70.0`) happens **once per MR**. Subsequent updates within the same branch/MR should simply append or update bullet points under the existing MR's release header in `CHANGELOG.md` without incrementing `VERSION` again.
- **ISOLATED MR SCOPE**: Each MR/PR branch MUST modify `CHANGELOG.md`, `README.md`, and `VERSION` strictly and exclusively for the changes introduced within **that specific MR's scope**.

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

### Step 4: Version Bumping & Impact Assessment (`VERSION` & Source Files)
1. Read current version from `VERSION`, `backend/VERSION`, and `frontend/package.json`.
2. Analyze code diffs to assess SemVer impact:
   - **PATCH** (`X.Y.Z+1`): Backward-compatible bug fixes or minor refactors
   - **MINOR** (`X.Y+1.0`): Backward-compatible new features, API endpoints, or UI screens
   - **MAJOR** (`X+1.0.0`): Breaking API changes, major architecture refactors, or milestone launches
3. **User Confirmation on Major/Scope Shift**:
   - If the code diff indicates a **MAJOR** bump or a significant scope shift (e.g. changing from `0.71.0` to `1.0.0`), **MUST ask/confirm with the USER** (or state recommended version in the evaluation summary) before finalizing the version bump.
4. Update `VERSION`, `backend/VERSION`, `frontend/package.json` (`"version"`), and sync the exact version string across `CHANGELOG.md` header.


---

## 🛠️ Checklist Before Finalizing
- [ ] Version in `VERSION` file strictly matches `CHANGELOG.md` header.
- [ ] No version number collision with existing released tags.
- [ ] `README.md` reflects any new CLI flags, endpoints, or environment variables introduced.
