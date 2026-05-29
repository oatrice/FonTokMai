# Edgetunnel Migration Task List

- [x] **Phase 1: Fetch and Prepare Edgetunnel**
  - [x] Fetch `_worker.js` from `cmliu/edgetunnel`.
  - [x] Save to `src/index.js`.
  - [x] Clean up old TS files (`src/index.ts`, `test/index.spec.ts`).

- [x] **Phase 2: Configuration Update**
  - [x] Update `wrangler.jsonc` to set `main: "src/index.js"`.
  - [x] Add `[vars]` for `ADMIN: "admin"` and `UUID: "d44e142d-b986-4981-899a-5d0ff80371c5"`.
  - [x] Add `[[kv_namespaces]]` for `binding: "KV"`.
  - [x] Create `.dev.vars` for local environment testing.

- [x] **Phase 3: Verification & Cleanup**
  - [x] Update `package.json` scripts if necessary.
  - [x] Update `README.md` to reflect Edgetunnel usage and Client connection instructions.
  - [x] Create walkthrough documentation.
