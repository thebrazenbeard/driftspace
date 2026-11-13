# Driftspace

Driftspace is a planned science-fiction world for [REALM](https://github.com/thebrazenbeard/REALM), a setting-neutral multiplayer roleplaying engine. **This repository is for the Driftspace world, not the REALM engine or a deployed server.**

## Current status

**Private synthetic pilot verified on VN2 (2026-11-13).** The separate four-room Driftspace test world continues to run behind Tailscale with a game-only Telnet/Mudlet listener on port `7777`. Three Driftspace services were active and the private listener was accepting connections during the most recent host check. The separate REALM `siltglass-reach` pilot remains outside this world. **The live game and its saved Rylok state were not upgraded or modified by the source work described below.**

**Draft source qualification — not a game release.** [Driftspace PR #4](https://github.com/thebrazenbeard/driftspace/pull/4) at `c274e54265afc1556b19a9591ddb459c9aeeffee` passed **76/76 unit tests** and **118/118 synthetic crew-integration assertions**, each in normal and optimized Python on VN2/Linux and Lappy/Windows. In addition, 47/47 synthetic NPC credential tests passed on VN2. These tests used an isolated checkout of **unmerged REALM Draft [PR #193](https://github.com/thebrazenbeard/REALM/pull/193)** at `6dcf5a545e69c58dd5188194f13e502070a31f32`; its NPC identity reservations are **not installed in the private pilot**. REALM's earlier consolidated core changes merged in [PR #190](https://github.com/thebrazenbeard/REALM/pull/190) at `77e46517b5ea5d44e2dcbc408211dadc7c7808a1`, but that is likewise not proof of a host upgrade.

An existing VN2 CPU-only Granite model has generated **genuine** speech proposals committed through REALM to **disposable synthetic SQLite**, with replay-bound receipts and no player/captain automation. A six-actor real-model run exposed **six identical Tessa-specific lines**; later tests proved that name-swapped copies were not distinct voices. The source now rejects such obvious template reuse and allows at most one explicitly opted-in quality retry, but a post-fix real two-actor trial still had **only one accepted character**, correctly holding the second after repeated copied dialogue. The six planned AI crew **are not active or voice-qualified**. The full station, public website, production multiplayer, memory/training rights, session controls and live deployment remain unqualified. The public `main` branch is orientation/documentation only, not the deployed host source.

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
