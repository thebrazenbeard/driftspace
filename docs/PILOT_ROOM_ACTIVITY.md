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

## Automatic room activity, opt-out private terminal preview

The authenticated, Rylok-only private Telnet bridge can poll the existing
REALM room-event feed on a socket idle tick (about every two seconds).
New other-actor room events appear automatically, followed by the ordinary
Driftspace prompt. There are no background worker threads writing to the
same Telnet socket. Partially typed commands are left uninterrupted.

Controls: `watch on`, `watch off`, `watch status`. Automatic updates begin
enabled for the private synthetic pilot. `listen` remains available to
fetch immediately and `history N` still shows only received session events.
`watch off` stops automatic HTTP polling but does not revoke access to
the current room or erase already buffered received events.

Three consecutive invalid/unavailable gateway polls pause automatic
updates and emit one generic warning without copying server error text
or bearer details. `watch on` retries. Every feed is requested through
the already-authenticated Rylok Gateway context, never a client-chosen
player identity. The current live REALM host still lacks the new explicit
entry cursor from draft PR #189; this preview retains the older cursor
fallback until a host upgrade is qualified.

`tools/verify_auto_room_bridge.py` requires explicit authorized bridge and
REALM source paths. It creates disposable credentials, Gateway, worldpack,
and private Telnet listener, then checks spontaneous new speech, watch
on/off, invalid commands, pre-join/pre-entry confidentiality, room movement,
typed-command preservation, scoped history, and disconnect. This is a
private **poll-to-terminal** prototype, not socket-push from REALM, public
multiplayer, or any live AI crew behavior.

## Private terminal command and gateway-failure qualification

The local `listen` and `history [N]` dispatcher now recognizes whitespace
between the verb and its optional count, including tabs and line breaks, so
these commands are never passed to the generic REALM fallback by accident.
An invalid `listen` argument or invalid `history` count fails locally.
The current REALM command parser also splits on literal spaces, so this
correction does **not** demonstrate an existing historical-message leak;
it enforces the pilot's private-history boundary across parser revisions.

Automatic `RoomWatch` fetches now count transient `OSError`/URL and HTTP
transport failures in the same three-attempt budget as malformed feed data.
The resulting pause text excludes network exception details and does not
advance the session feed cursor. HTTP **401/403 authentication denials** and local **PermissionError**
access denials are *not* downgraded into transient failures: they propagate to the authenticated
terminal owner to handle the revoked/forbidden credential. This wrapper does
not itself reauthenticate or authorize a player. Re-enabling a paused
watcher remains an explicit `watch on` operation.

`tests/test_room_activity.py` and `tests/test_room_watch.py` cover normal,
malformed, Unicode-whitespace, URL failure, 503, and 401/403 cases. This is
a source-only pilot change. A successful hosted source suite does not prove
that the separately deployed private VN2 Telnet bridge has incorporated it.

## Host-owned channel revision and local history invalidation

REALM main supplies a monotonic, host-issued `channel_revision` on each
authenticated `/api/v1/feed` response. Its value changes when the host grants,
alters or revokes that actor's private-group membership; this can happen with
**zero newly visible events**. The private Driftspace activity reader now
validates this revision and clears its session-local history whenever a
previously observed value changes or disappears. A backward revision or
malformed value fails closed without advancing the feed cursor. Direct HTTP
401/403 authorization denials and 409 host-channel epoch conflicts also
invalidate cached session text before the exception propagates.

A newly authorized crew-channel message may be displayed immediately from
REALM's authenticated feed, but it is **never cached** in the terminal's
offline `history N` buffer. That is deliberate: `history N` has no live
re-authorization callback, so caching crewchat would allow local replay
after role revocation and before the next network poll. Other ordinary
room activity remains session-only and is cleared on room transitions.

A legacy host that omits `channel_revision` continues to support normal
room text, but omission cannot establish private-channel history rights.
The same client limitation remains: once material has already been printed
to a terminal, a subsequent role change cannot retract those bytes.
An idle or disconnected client cannot learn of revocation until another
authenticated feed attempt or host-side connection termination. This is a
local privacy hardening of the **source candidate**, not proof that the
deployed VN2 terminal uses this reader or that public multiplayer is safe.

`tests/test_room_channel_revision.py` covers ordinary/legacy room history,
zero-event permission changes, non-retention of delivered crewchat, backward
and malformed access revisions, and direct HTTP denial/conflict paths.
