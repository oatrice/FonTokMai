# Product

<!-- impeccable:product-schema 1 -->

## Platform

adaptive

## Users

- **General Public & Commuters (Isan Region, Thailand):** Everyday people needing hyper-local, accurate rain nowcasting (15–90+ minutes in advance) to plan travel, commute, and daily routines without getting caught in sudden downpours.
- **Agricultural & Outdoor Workers:** Farmers, market vendors, and field workers who rely on storm and rain cloud tracking to protect crops, produce, and outdoor operations.

## Product Purpose

FonMaYang (ฝนมายัง) is a real-time rain prediction and cloud tracking system specifically tailored for the Isan (Northeastern) region of Thailand. It eliminates the guesswork of sudden storms by processing TMD (Thai Meteorological Department) Doppler radar scans with optical flow computer vision to predict rainfall ETA, intensity, and cloud trajectories up to 90+ minutes in advance.

Success means delivering actionable, timely, and trusted notifications and visual insights before rain hits, with zero notification fatigue and clear confidence.

## Positioning

Unlike generic worldwide weather apps that rely on coarse mathematical models or delayed satellite predictions, FonMaYang uses direct local TMD radar imagery (Khon Kaen, Sakon Nakhon) augmented with optical flow cloud vectoring and multi-provider fallback. It provides exact storm vectors, cloud locking, and transparent operational resilience.

## Operating Context

- **Channels & Surfaces:**
  - Web dashboard (Next.js 16, React 19, Tailwind CSS v4, Framer Motion) featuring real-time radar mapping, retro-arcade glassmorphic leaderboard, and SSE broadcaster (`/api/v1/events/stream`).
  - Automated bots via Telegram & LINE with rich media cards (nowcast GIFs, tracking radar vectors, and timeline graphs).
  - Admin & financial transparency interfaces (Runway Engine, GCP cost metrics, Milestone progress, and donation tracking).
- **Network & Hardware:** Runs in mobile environments with fluctuating 4G/5G connections; fast responses and low-latency feedback are vital.

## Capabilities and Constraints

- **Core Capabilities:**
  - Real-time TMD Doppler radar ingestion and optical flow cloud tracking (`kkn120`, `kkn240`, `skn240`).
  - Rain cloud manual target locking (`/lock <grid>`).
  - Real-time leaderboard and SSE streaming with 15s heartbeats.
  - Multi-provider fallback (Tomorrow.io, Rainbow API, Xweather, Open-Meteo).
  - Dynamic circuit breaker and Emergency Overdrive (`INVINCIBLE` status).
  - Zero-PII Stripe payments, anonymous authentication, and auto-payout handling.
- **Constraints:**
  - Serverless execution requirements: Webhook immediate 200 OK acknowledgment; heavy processing offloaded to Cloud Tasks.
  - TMD radar image availability and upstream latency.

## Brand Commitments

- **Tone & Voice:** Practical, dependable, delightfully prompt, and transparent. Clear Thai and bilingual communication without jargon.
- **Identity Assets:** Name "FonMaYang" (ฝนมายัง 🌧️), retro-arcade accents for gamified milestones/leaderboard, clean radar visualization aesthetics.

## Evidence on Hand

- Live radar feeds from TMD stations (`kkn120`, `kkn240`, `skn240`).
- Comprehensive bot command suite and automated verification test suite.
- Financial transparency metrics (`/api/v1/metrics/gcp-costs`, `/api/milestones`).

## Product Principles

1. **Hyper-Local Truth Over Generic Models:** Always prioritize direct local radar scans and verified ground truth over broad statistical forecasts.
2. **Immediate Feedback, Zero Blockers:** Every interaction—bot command or web UI—must provide instant visual acknowledgment and responsive progress indication.
3. **Transparent & Resilient:** Display clear confidence levels, fallback states, and system health openly without hiding degraded conditions.
4. **Focused Utility:** Deliver clear, scanable information at a glance; avoid decorative clutter that obscures rain arrival ETAs.
