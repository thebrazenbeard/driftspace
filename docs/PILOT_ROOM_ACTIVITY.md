# Driftspace pilot: authenticated room activity

Scope: private Tailscale-only, Rylok-bound synthetic station preview. This does
not implement a public multiplayer system, a model NPC, or a push-based chat bus.

## What now works

The command "listen" polls REALM's existing authenticated HTTP room-event feed
for new events while Rylok remains in the current room. "history" or
"history N" (1-50) replays only messages actually received by that terminal
session since room entry. The old underlying REALM history/listen verb is NOT
called from the pilot bridge; malformed variants are rejected before fallback.

RoomActivity is an in-memory terminal-session view:
- Initializes its cursor from the REALM Gateway's join response, so there is no
  replay of events generated before login.
- When the player issues a movement command, takes a fresh Gateway cursor for
  the destination and clears previously buffered room messages.
- Filters echoes of Rylok's own actions; does not claim multi-client broadcast.
- Reads events through the Rylok bearer-authenticated REALM Gateway.
- Rejects stale, replayed, out-of-order or oversized events before cursor update,
  and strips terminal control bytes from rendered event text.
- Tracks at most 50 displayed other-actor events in this terminal session;
  reconnecting begins a new history. No new SQLite tables are created.

## Evidence and privacy tests

In tests/test_room_activity.py, normal and optimized Python runs check cursor
validation, recent event text, bounds, anti-replay, room transitions, own-echo
filtering, terminal control removal, and catching "listen N" bypass attempts.

The disposable two-player HTTP Gateway probe in
tools/verify_realm_room_activity.py creates a fresh imported four-room world,
temporary Rylok and Visitor credentials, and a distinct second world. It
checks:
- Visitor's speech before Rylok joined never appears.
- New same-room Visitor speech appears in a subsequent "listen".
- Speech in a destination room *before* Rylok enters stays hidden.
- Post-entry speech is received; previous room history is cleared.
- Rylok's own action is not re-echoed.
- Forged actor and cross-world bearer access are denied.

A separate private disposable authenticated Telnet bridge test repeated game
login, listen/history, early-message privacy, movement, denial of "listen 5"
legacy fallback, own-echo filtering, and disconnect. These are integration
tests with synthetic actors, NOT a deployed real-player multiplayer claim.

## Remaining boundaries

- Polling requires the human to type "listen"; there is no socket push, GMCP
  notification, or automatic event delivery while the user is idle.
- Only REALM "say" and host-generated room events are fetched. Driftspace
  emote/yell/ooc/crewchat remain separate pilot-local receipts, not deliveries.
- The private terminal allows only Rylok to log in; Visitor in tests is a
  disposable REALM HTTP actor, not a second live player account on VN2.
- This is a client-side privacy defense. REALM's generic Engine "history"
  command must receive a host-enforced entry-time privacy boundary before
  public multi-user release. The pilot's cursor does not solve that upstream.
- No private story source, credentials, other world databases, or service ports
  are imported or changed by the public source in this PR.

## Room-entry cursor race (source-only proposed REALM contract)

The generic REALM gateway currently reports a global `cursor` after `join`
or `command`. Another player can speak between the room-entry event and
the later global cursor sample, causing a client to skip post-entry speech.

The proposed backward-compatible `room_entry_cursor` field identifies the
actor's latest host-recorded entry into the current room, independently of
global feed traffic. On a successful join or movement, Driftspace's
`gateway_room_cursor(response)` prefers this value and rejects malformed
authoritative evidence. Older REALM servers lacking the field still use the
global cursor, including its known message-loss race. Fallback is not a
claim of lossless delivery.

`tools/verify_realm_entry_cursor.py` tests a disposable authenticated HTTP
Gateway and two actors, injecting speech between join/move and global cursor
sampling. The private Telnet adapter is prepared to prefer the new field
when a qualified REALM host supplies it; no running host upgrade is implied.

Limit: host entry lookup still runs after its original join/command
transaction. This fixes the tested other-actor speech race, not concurrent
sessions for one character, lost join responses, token revocation, or
exactly-once delivery.

## Windows SQLite connection ownership

Python's SQLite connection context manager commits or rolls back a
transaction but does not close the handle. Windows refuses to delete a
temporary SQLite file while any handle remains open. Read-only map and
inspection queries, scoped pilot social receipts, and synthetic test
fixtures now explicitly close their connections after use. This is
resource-lifecycle hardening; it does not alter game permissions,
character state, chat visibility or room discovery policy.
