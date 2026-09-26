---
name: FonMaYang
description: Luminous Isan Monsoon — Translucent frosted glassmorphism, storm-glow neon telemetry, and tactile weather interfaces.
colors:
  primary: "#2563eb"
  primary-hover: "#3b82f6"
  accent-cyan: "#06b6d4"
  accent-emerald: "#10b981"
  accent-amber: "#f59e0b"
  accent-rose: "#f43f5e"
  accent-purple: "#a855f7"
  bg-main: "#060913"
  surface-glass: "rgba(15, 23, 42, 0.65)"
  surface-glass-hover: "rgba(30, 41, 59, 0.75)"
  surface-glass-active: "rgba(30, 41, 59, 0.85)"
  border-glass: "rgba(255, 255, 255, 0.12)"
  border-glass-hover: "rgba(255, 255, 255, 0.25)"
  text-main: "#f8fafc"
  text-muted: "#94a3b8"
typography:
  display:
    fontFamily: "var(--font-sans), ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(2rem, 5vw, 3.25rem)"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "var(--font-sans), ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.01em"
  title:
    fontFamily: "var(--font-sans), ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "normal"
  body:
    fontFamily: "var(--font-sans), ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "var(--font-mono), ui-monospace, SFMono-Regular, monospace"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.05em"
rounded:
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.text-main}"
    rounded: "{rounded.md}"
    padding: "10px 16px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
---

# Design System: FonMaYang

## Overview

**Creative North Star: "Luminous Isan Monsoon"**

FonMaYang’s visual identity evokes the dramatic arrival of tropical monsoon clouds over the Isan plateau at twilight. The environment combines deep night atmospheric tones (`#060913`) with multi-layered, frosted glass panels that mimic wet condensation and translucent storm shields. High-voltage neon conduits (Cyan, Emerald, Amber, Rose, Purple) cut through the gloom like radar beams and lightning strikes, giving telemetry and live event streams unmistakable visual priority.

The aesthetic blends hyper-local meteorological utility with retro-arcade excitement. Data visualizations, storm tracks, and community financial milestones feel tactile, live, and rewarding.

**Key Characteristics:**
- **Atmospheric Depth:** Deep-space navy foundation with fixed radial gradients in blue, purple, and cyan.
- **Translucent Layering:** Frosted glass panels (`backdrop-filter: blur(16px)`) with crisp hairline borders (`rgba(255, 255, 255, 0.12)`).
- **Storm-Glow Accents:** High-saturation status lights and glowing silhouettes that react dynamically to state changes.
- **Tactile Feedback:** Crisp hover micro-lifts (`translateY(-2px)`), expanding borders, and spring physics for live updates.

## Colors

The palette derives from wet night radars: saturated chromatic indicators glowing against deep twilight glass.

### Primary
- **Deep Doppler Blue** (`#2563eb` / `#3b82f6`): Primary interaction signals, main actions, active navigation anchors, and radar range vectors.

### Secondary
- **Lightning Cyan** (`#06b6d4`): Real-time SSE heartbeats, active streaming links, and precipitation ETA indicators.

### Tertiary
- **Arcade Purple** (`#a855f7`): Leaderboard champion standings, gamified milestone tokens, and celebration highlights.

### Status Accents
- **Radar Green / Invincible Emerald** (`#10b981`): Healthy connections, verified radar sync, and positive runway cashflow.
- **Storm Warning Amber** (`#f59e0b`): Warning thresholds, pending verifications, and moderate dBZ rain cells.
- **Heavy Downpour Rose** (`#f43f5e`): Severe storm cells, circuit breaker warnings, and danger actions.

### Neutral
- **Isan Night** (`#060913`): Canvas background base.
- **Slate Glass Base** (`rgba(15, 23, 42, 0.65)`): Resting surface for cards, panels, and modals.
- **Slate Glass Active** (`rgba(30, 41, 59, 0.85)`): Elevated surfaces and active states.
- **Monsoon Mist White** (`#f8fafc`): Crisp primary text and icons.
- **Rain Slate** (`#94a3b8`): Secondary telemetry labels and descriptions.

### Named Rules
**The Luminescence Rule.** Bright saturated neon colors (Cyan, Emerald, Amber, Rose, Purple) are reserved strictly for data states, telemetry badges, and live changes—never as vast background fills.

## Typography

**Display Font:** System Sans / Inter / Geek Sans fallback (`var(--font-sans)`)  
**Body Font:** System Sans (`var(--font-sans)`)  
**Label/Mono Font:** System Monospace (`var(--font-mono)`)

**Character:** Clean, technical, and instantly readable under outdoor glare, paired with high-contrast monospace metrics for numerical weather readings and timestamps.

### Hierarchy
- **Display** (700, `clamp(2rem, 5vw, 3.25rem)`, 1.1): Hero headlines, main title cards, milestone announcements.
- **Headline** (700, `1.5rem` / 24px, 1.25): Card headers, modal titles, section dividers.
- **Title** (600, `1.125rem` / 18px, 1.35): Component group headers, location names.
- **Body** (400, `0.875rem` / 14px, 1.5): Descriptive text, financial explanations, bot guides. Max line length: 65ch.
- **Label** (600, `0.75rem` / 12px, 1.2, uppercase, tracking +0.05em): Telemetry badges, dBZ values, timestamps, and live connection status.

### Named Rules
**The Telemetry Monospace Rule.** Any dynamic numerical measurement (time ETA, dBZ intensity, budget percentages, server heartbeat latency) must use monospace figures to prevent layout jitter during live updates.

## Layout

- **Container Model:** Max-width 7xl (1280px) centered canvas with responsive padding (`px-4 sm:px-6 lg:px-8`).
- **Rhythm & Grid:** 12-column responsive grid or modular flex layouts using a base-4 spatial scale (4px, 8px, 16px, 24px, 32px).
- **Density:** Medium-dense operational telemetry layout. Essential metrics remain visible above the fold on mobile viewports.

## Elevation & Depth

FonMaYang rejects artificial drop shadows in favor of **luminous translucent glass layering** and **glow diffusion**.

### Shadow Vocabulary
- **Glass Rest** (`0 8px 32px 0 rgba(0, 0, 0, 0.37)`): Resting card elevation with backdrop blur.
- **Interactive Lift** (`0 12px 40px 0 rgba(0, 0, 0, 0.45)`): Hover state elevation accompanied by `-translate-y-0.5`.
- **Neon Glow** (`0 0 25px rgba(var(--accent-rgb), 0.25)`): Ambient back-light cast by interactive cards onto the canvas.

### Named Rules
**The Edge-Before-Depth Rule.** Glass depth is primarily defined by the hairline border contrast (`border-white/10` to `border-white/25`), not heavy dark drop shadows.

## Shapes

- **Corners:** High border radius throughout. Small buttons (`rounded-lg` / 8px), cards & panels (`rounded-2xl` / 16px to 24px), status pills & badges (`rounded-full`).
- **Specular Highlights:** Radial highlight gradients positioned at card corners (`bg-white/5 blur-2xl`) simulating light glancing across wet glass.

## Components

### Buttons (`GlassButton`)
- **Shape:** Rounded-xl (12px) for medium; rounded-2xl for large.
- **Primary:** Deep blue with translucent blur (`bg-blue-600/80 hover:bg-blue-500/90 text-white backdrop-blur-md border border-blue-400/30`).
- **Interactive States:** `-translate-y-0.5` micro-lift, expanded border glow on hover, active reset to `translate-y-0`.

### Badges & Pills (`GlassBadge`)
- **Shape:** Rounded-full pill with `px-2.5 py-1 text-xs`.
- **Style:** Subtle colored glass background (15% opacity), saturated text (300 weight), matching border (30% opacity).
- **Pulse Dot:** Optional 6px animated pulsing indicator for live streaming connections.

### Cards & Panels (`GlassCard`)
- **Shape:** `rounded-2xl`, overflow-hidden with ambient internal specular highlight.
- **Variants:** Subtle (`bg-zinc-900/40`), Medium (`bg-zinc-900/60`), Heavy modal (`bg-zinc-950/80`).
- **Hover Glow:** Contextual neon glow corresponding to the card's domain (Purple for Leaderboard, Blue for Radar, Emerald for Runway).

### Live Telemetry Indicators
- **Streaming Indicator:** Triple-state LED dot (Green = connected, Amber = connecting, Red = disconnected) with radar ping animation.

## Do's and Don'ts

### Do:
- **Do** wrap all major content groups in frosted `GlassCard` containers with subtle border contrasts.
- **Do** provide instant visual feedback on buttons (micro-lift and border illumination) within 200ms.
- **Do** format all weather readings and countdown ETAs with tabular monospace numerals.
- **Do** test high contrast against dark mode—ensure text contrast exceeds WCAG AA (4.5:1).

### Don't:
- **Don't** use opaque solid white or grey card backgrounds; always maintain the frosted glass aesthetic.
- **Don't** use neon colors for body text or large background areas.
- **Don't** hide degraded system states or offline radar feeds; use warning badges prominently.
- **Don't** introduce sharp 90-degree square corners on interactive controls.
