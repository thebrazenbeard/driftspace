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

## Accelerated Red-Team Review — determination

Patrick delegated resolution of the Quorum's design questions rather than
participating in an interactive defense. This is an **internal Quorum-method
review**, not a separately executed independent reviewer.

**Hypothesis:** An actor may learn a room before physically entering it, but
its name may appear only when the authoritative game has recorded an
observation that identifies that room for that actor.

**Purist Logic — question and resolution:** Does line of sight imply the
room's identity? No. Seeing inside a space can reveal geometry, occupants,
light, or hazards without establishing its canonical name. An exit alone
proves a navigable direction, not permission to reveal a database room ID.

**Pragmatism — question and resolution:** Does withholding names until entry
make exploration needlessly opaque? Sometimes. A posted sign, an authorized
sensor scan, recognized landmarks, an explicit narrative reveal, or an
approved shared chart may establish identity. Each needs host-validated
evidence and its own privacy rule. A client guess is not one.

**Bridge — question and resolution:** If an open doorway makes a room
visually identifiable, should the map show it? **Yes, when the host has
adjudicated that identification for Rylok**, even before entry. If only a
passage is visible, show a known direction / unidentified room, never an
invented name. A partial view could eventually use a silhouette marker.

**Determination: REFINE** the visited-only discovery model, without changing
the deployed pilot's disclosure behavior. A future host design should
distinguish: visited (physically entered), observed (authorized view/report),
identified (authorized evidence establishes the name), and unknown (only a
passage/direction is known).

These are proposed states, not an implemented REALM database schema.
They must be scoped to the actor and world and derive from host-adjudicated
observations rather than AI guesses, player text, politics or exit adjacency.

**Current decision:** The four-room synthetic worldpack has no authoritative
line-of-sight or identification events. Keep the live map conservative:
visited names plus unexplored directions only. Do not treat prose about
windows, doors or exits as an authorization to disclose a new room. This is
a safe default, not a canon requirement to enter each room before learning
its name.

**Future falsifiers:** (1) Unvisited name leaked through a bare exit;
(2) another actor's observations contaminate the current actor's map;
(3) revoked or cross-world scanner output grants identification;
(4) an authorized view of a posted room name fails to identify it;
(5) client prose alone changes game-state discovery.

The smallest useful host contract is a credential-bound discovery event with
actor, world, room, method, evidence class, and time, plus a safe projection.
REALM owns host adjudication; Driftspace controls setting-specific inputs.
