# Driftspace pilot: discovered map qualification

Status: source-only candidate and private VN2 terminal preview, not production REALM fog-of-war, canonical worldpack approval, or multiplayer.

## Quorum hypothesis
A player-scoped discovered-room map should improve navigation in the four-room synthetic pilot without disclosing unvisited room names or changing world state.

## Definitions and evidence
- Discovered: room entered in that actor's REALM join/move event ledger, or currently occupied.
- Source: REALM rooms/exits and authenticated actor's persisted movement events.
- Inference: two-dimensional placement from authored north/south/east/west edges. This is a visual projection, not canonical coordinates.
- Display: current-room marker, previously visited names and passages; unknown destinations show only a direction and "unexplored".
- Authority: current private Rylok-only bridge authenticates the game access code, then binds the projection to Rylok. This Python function DOES NOT independently authorize arbitrary actors.
- Privacy: source-only actor-specific read-only URI SQLite query. The user-facing game cannot choose a different actor ID.
- Unknown: Mudlet window-width and actual human playability; only terminal protocol and Python tests are qualified.
- Not included: private 37-room source worldpack, full crew, live AI or hosted multiplayer.

## Falsifiers and checks
1. Initial map reveals an unvisited room name -> FAIL.
2. Movement by another actor changes Rylok's discoveries -> FAIL.
3. A move between already discovered rooms rearranges coordinates -> FAIL.
4. Map lookup creates a missing SQLite file, changes contents or item custody -> FAIL.
5. Real imported synthetic REALM Engine movements do not update map -> FAIL.
6. Actual private Telnet bridge does not render the map after game-only authentication -> FAIL.

Source: tests/test_discovered_map.py, tools/verify_realm_discovered_map.py, plus a private disposable authenticated Telnet/Gateway smoke test. See PR #4 comment for measured outcomes and exact code head; tests do not prove a production fog-of-war API.

## Authority boundary
REALM owns future host-bound discovery, world/account authorization, map visibility and GMCP or client-safe structured feed.
A production client must never directly read REALM SQLite or pass a claimed player name as evidence of identity.
Do not promote the private preview to a public service or assume other worlds share its geometry.

## Unanswered Quorum Bridge attack
Should an adjacent room visible through a doorway appear by name on the map before Rylok enters it? Options might include name, silhouette, or unexplored exit only. This remains a design question, not a reviewer determination.
