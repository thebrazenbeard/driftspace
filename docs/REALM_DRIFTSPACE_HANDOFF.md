# REALM ↔ Driftspace integration notes

Status: source-level tested pilot candidate, not approved integration, deployment,
canon release, multiplayer implementation, or NPC authority proof.

## Authority boundaries

- REALM owns generic engine, authenticated player/session identity, transactional
  item ownership, world data, networking, map visibility, host NPC reservations.
- Driftspace owns setting proposals and creator-approved fiction, client presentation,
  and non-authoritative game-specific command conveniences.
- Semantic Atlas (https://github.com/thebrazenbeard/semanticatlas) is separate,
  source-visible proprietary research. Its architecture distinguishes source,
  interpretation, currentness, adjudication and provenance. This handoff uses
  those principles conceptually, not its code or historical personal archives.

## Source-qualified overlap

1. REALM accepts 'take <item>' and 'drop <item>'. The private Rylok pilot expects
   classic MUD 'get', 'pickup', 'pick up', 'obtain', 'grab' and 'examine' forms.
   New source-only 'driftspace/pilot_actions.py' routes mutation to authenticated
   REALM /api/v1/command; SQLite reads do not change item state.
2. Item examination currently reads the authenticated pilot actor's room or held
   items using SQLite query-only mode. This is NOT a generic host authorization
   boundary. For production, item inspection must be host-owned and credentialed.
3. 'tools/verify_realm_pilot_commands.py' uses a disposable worldpack/database,
   temporary credential and actual Gateway HTTP command handling, verifying
   aliases, item reachability, movement, pickup/drop, and forged actor rejection.
4. REALM /api/v1/map exists, but its source explicitly states fog-of-war is not
   implemented; the private terminal cannot claim a usable player map without
   authored content plus a qualified authorization model.
5. The VN2 game-only Telnet bridge has pilot-local emote, yell, ooc and crewchat
   receipts. They are NOT delivered to other players or AI NPCs. REALM must
   implement authenticated generic subscription scopes and delivery.

## Semantic presentation and evidence

- The client can use explicit cues like 'steel edge' or 'faint floor lights'
  for display colors without creating canonical object properties.
- Bare 'table' does not imply wood. 'Wooden or steel table' is ambiguous.
- Authored material, illumination, and condition would take precedence over
  inferred colors if a future worldpack schema supports those properties.
- These color heuristics are not authority for collision, lighting visibility,
  hazards, pressure, or game rules. No new REALM worldpack v1 fields are implied.
- Wreckforge private drafts and unapproved canon must not be published here.

## Release blockers and requests to REALM

- Host-enforced reserved NPC principals, including privileged provisioning.
- Host-owned actor-authorized item inspection and consistent world binding.
- Authenticated multiplayer chat and OOC, crew, faction scopes with rate limits.
- Safe structured map/room feeds and visibility rules.
- Cross-interface Telnet/browser tests and deployment isolation.
- Review and explicit acceptance before merging either repository.

## References

- Driftspace draft: https://github.com/thebrazenbeard/driftspace/pull/4
- REALM generic terminal draft: https://github.com/thebrazenbeard/REALM/pull/184
- REALM NPC host gate: https://github.com/thebrazenbeard/REALM/issues/20
- Tests: tests/test_pilot_actions.py and tools/verify_realm_pilot_commands.py

These claims are source/version scoped. Fresh verification is needed when either
repository changes; no PR in either repository is promoted by this note.
