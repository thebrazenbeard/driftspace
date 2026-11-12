# Driftspace

Driftspace is a planned science-fiction world for [REALM](https://github.com/thebrazenbeard/REALM), a setting-neutral multiplayer roleplaying engine. **This repository is for the Driftspace world, not the REALM engine or a deployed server.**

## Current status

**Private synthetic pilot verified on VN2 (2026-11-12).** A separate, four-room Driftspace test world is running behind Tailscale with a game-only Telnet/Mudlet listener on port `7777`. On November 12, the listener was reachable from Lappy, the three Driftspace services and separate REALM pilot service were running, and Driftspace Draft [PR #4](https://github.com/thebrazenbeard/driftspace/pull/4) at `62b89662208785168e999632ce6f38ed7b6941c0` passed **67/67 tests** in both normal and optimized Python on VN2. This is a **private prototype**, not a release: the full station, six AI crew, public website/URL, model training, and general multiplayer readiness are not established. The REALM host security/privacy work remains held for review. The public `main` branch is orientation/documentation only; it is not the deployed pilot's source checkout. The unrelated REALM `siltglass-reach` pilot remains separate.

## Project boundaries

- **Driftspace** owns setting-specific worldpack proposals, locations, encounters, economy, and crew characterization, subject to creator review.
- **REALM** owns the generic game engine, networking, commands, authorization, persistence, and host-validated NPC actions.
- **Wreckforge Chronicles** is separate literary source material. Unpublished manuscripts and creator-private canon are not published here without explicit review and permission.

## Planned development

1. Prepare a canon- and rights-reviewed Driftspace worldpack with source provenance.
2. Exercise a synthetic worldpack in a fresh, isolated REALM world. Do not reuse another world's database, credentials, service, or endpoint.
3. Prototype six distinct AI crew identities—**Tessa, Calamar, Ghost, Kira, Bulwark, and Milo**—with separate character contexts and a shared, qualified small-model inference worker. **Captain Rylok remains player-controlled.**
4. Validate multiplayer security, host-authoritative world changes, persistence, hardware capacity, backup/recovery, and source permissions before any deployment claim.

Plans and prototype receipts are not proof of live integration. AI suggestions must be validated by the game host before changing world state.

## Tracking

- [#2 — Driftspace/REALM boundary and host contract](https://github.com/thebrazenbeard/driftspace/issues/2)
- [#3 — AI crew identities and runtime qualification](https://github.com/thebrazenbeard/driftspace/issues/3)

Both tracks remain open until their acceptance criteria are demonstrated.
