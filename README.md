# Driftspace

Driftspace is a planned science-fiction world for [REALM](https://github.com/thebrazenbeard/REALM), a setting-neutral multiplayer roleplaying engine. **This repository is for the Driftspace world, not the REALM engine or a deployed server.**

## Current status

Early development and coordination. The public `main` branch currently contains project orientation only. A playable Driftspace instance, public URL, imported worldpack, operational AI crew, and character-model training **have not been verified**. Existing REALM host pilots are separate and are not evidence of a Driftspace deployment.

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
