---
target: frontend/src/components/FinancialDashboard.tsx
total_score: 26
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 1
target_identity: "file:/Users/oatrice/Software Project/FonMaYang/frontend/src/components/FinancialDashboard.tsx"
target_fingerprint: "sha256:300069c8ec575eeed184fdb9483a74eac6f273af388c5a61b8c0a44c49483159"
target_path: /Users/oatrice/Software Project/FonMaYang/frontend/src/components/FinancialDashboard.tsx
timestamp: 2026-09-18T12-45-28Z
slug: frontend-src-components-financialdashboard-tsx
---
### Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Real-time SSE heartbeat and runway live math pulse cleanly, but SWR skeleton loaders flicker on sync without micro-transition dampening. |
| 2 | Match System / Real World | 3 | Metaphor of "Budget Jars" and "HP Decay" works nicely for gamified ops, but mixed bilingual descriptions ("Extended Lifespan Mode / โหมดต่ออายุระบบฉุกเฉิน") lack a clean locale toggle. |
| 3 | User Control and Freedom | 3 | Modals (Donation, Recovery) have clear dismiss escapes, but toggling "Extended Lifespan Mode" is an instant local state switch without confirmation or persistence feedback. |
| 4 | Consistency and Standards | 2 | Primary action buttons and badges mix styling patterns (`GlassButton`, raw HTML `<button>` for toggle, custom inline gradients). |
| 5 | Error Prevention | 3 | Token recovery explicitly enforces 3-point zero-PII matching; donation input constraints prevent invalid contributions. |
| 6 | Recognition Rather Than Recall | 3 | Distinct radar and infrastructure jar icons aid visual scanning; currency and metrics explicitly labeled with tabular numerals. |
| 7 | Flexibility and Efficiency | 2 | Lacks keyboard accelerators (e.g. Esc/shortcut to quick-donate or toggle views); touch targets on small header tabs are close to the 44px threshold. |
| 8 | Aesthetic and Minimalist Design | 2 | Saturated cyber-purple and cyan-on-dark palette triggers generic AI/crypto dashboard tropes; high visual noise from competing glowing card borders. |
| 9 | Error Recovery | 3 | Graceful fallbacks for missing/loading runway data and offline SSE state; recovery instructions are clear. |
| 10 | Help and Documentation | 2 | Contextual tooltips explaining how the runway days formula or dBZ threshold connects to server costs are absent. |
| **Total** | | **26/40** | **Acceptable** |

### Design Specificity Verdict

**LLM assessment**: The interface possesses genuine meteorological and financial engineering intent (Doppler radar ingest, Cloud Run infrastructure cost transparency, zero-PII token recovery). However, its visual expression leans heavily into boilerplate "crypto-telemetry / Web3 dashboard" tropes. The ubiquitous purple glows, cyan pills, and retro-arcade badge accents drown out FonMaYang's true regional identity: a high-trust, dependable tropical monsoon nowcasting tool for northeastern Thailand. Grounding the palette in authentic atmospheric Doppler and monsoon twilight tones—rather than hyper-saturated neon glows—will elevate it from generic AI slop to an authoritative civic radar console.

**Deterministic scan**: The deterministic detector identified 1 finding across the scanned surfaces:
- `antipattern: ai-color-palette` (`warning` / `slop`) in `frontend/src/components/FinancialDashboard.tsx:91` (`from-purple-500 gradient`).
The detector pinpointed the classic purple/violet + cyan-on-dark combination that signals AI-generated templates.

**Visual overlays**: Deterministic CLI scan executed directly against component source code. Browser overlays were not injected as no automated script injection pipeline was attached to the active terminal.

---

### Overall Impression
FonMaYang's financial dashboard has solid informational bones and remarkable architectural clarity: real-time burn rate, community transparency, and three-jar fund allocation are immediately intelligible. The critical weakness is aesthetic cliché: the neon cyan + purple glow aesthetic reads like an NFT/crypto staking panel rather than a vital public meteorological utility serving commuters and farmers.

---

### What's Working
1. **Clear Telemetry Hierarchy**: The 3-card hero row (Financial Runway, Total Reserve Vault, Resiliency Status) establishes an immediate top-level operational summary with tabular monospace numbers that prevent layout shift.
2. **Transparent Cost Decomposition**: Breaking operating costs into three tangible functional jars (Cloud Run, Radar APIs, Emergency Reserve) demystifies serverless infrastructure for donors.
3. **Resilient Loading States**: Pulse skeletons and graceful fallbacks ensure the UI never collapses into layout thrashing during API latency or SWR revalidation.

---

### Priority Issues

- **[P1] What: Generic AI/Crypto Palette Saturation**
  - **Why it matters**: The heavy use of vibrant purple gradients, cyan badges, and glowing borders conveys speculative Web3 aesthetics rather than civic meteorological reliability and public trust.
  - **Fix**: Rebalance color tokens toward authentic Doppler weather scales (Doppler deep blue, atmospheric storm slate, emergency warning amber) and eliminate decorative purple glows.
  - **Suggested command**: `$impeccable colorize`

- **[P2] What: Cluttered Dual-Language Strings**
  - **Why it matters**: Inlining full dual-language strings side-by-side ("Extended Lifespan Mode / โหมดต่ออายุระบบฉุกเฉิน") clutters status badges and forces text wrapping on mobile viewports.
  - **Fix**: Implement a concise localized terminology layer or secondary sub-label structure rather than slash-separated inline strings.
  - **Suggested command**: `$impeccable clarify`

- **[P3] What: Unstyled Custom Switch in Resiliency Card**
  - **Why it matters**: The Extended Lifespan toggle in `FinancialDashboard.tsx` uses raw markup rather than the unified `GlassButton` or accessible ARIA switch patterns with explicit screen-reader state.
  - **Fix**: Encapsulate the switch into a dedicated accessible component with proper `role="switch"`, `aria-checked`, and tactile micro-interactions conforming to the design system.
  - **Suggested command**: `$impeccable polish`

---

### Persona Red Flags

- **Alex (Power User / Tech Operator)**: The toggle for Extended Lifespan lacks keyboard focus indicators and shortcut bindings (`Cmd/Ctrl+Shift+E`). Refreshing the budget jars has no keyboard accelerator, forcing mouse traversal.
- **Jordan (First-Timer / Local Commuter)**: Confused by technical terms like "Active burn rate", "Zero-PII Tracked", and "HP decay". The primary donation CTA says "Contribute to Milestone" rather than plain-language "สนับสนุนเซิร์ฟเวอร์เรดาร์" (Support Radar Server).
- **Casey (Distracted Mobile User)**: On narrow viewports, the 3-jar grid stacks into a very long scroll; the primary donation button is buried deep below the fold past the arcade leaderboard.

---

### Minor Observations
- Missing `aria-live="polite"` on dynamic runway countdown values.
- Header anchor links (`/#runway`, `/#overview`) rely on page fragment hashes that are not fully wired to matching container IDs.
- The retro arcade grid in the Leaderboard card uses an inline CSS background string rather than a reusable token or utility class.

---

### Questions to Consider
- Should the dashboard adopt an explicit Thai/English toggle rather than displaying dual languages concatenated inline?
- Would elevating the "Support Radar" CTA to a sticky mobile floating action bar improve conversion for commuters during active rain events?
- Should the "Arcade Leaderboard" be visually separated into a dedicated tab to let the core financial transparency cards breathe?
