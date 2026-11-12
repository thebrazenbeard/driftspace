# Six-crew synthetic turns — source-only qualification

The opt-in `driftspace.crew_turns.CrewTurnCoordinator` is a setting-owned
adapter around REALM's **existing**, authority-preserving
`ResidentTurnHost.run_scoped_tick`. It deliberately does **not** create its
own inference service, drive scheduler, database, role authority, or memory
system.

This candidate requires **`synthetic_trial=True`** *and* the exact
`driftspace-synthetic-demo` world ID and synthetic captain + six synthetic
crew actor IDs. Normal construction is refused. This prevents the proposed
but inactive Wreckforge crew roster from being treated as live activation.
Captain Rylok remains strictly a player character, not a model actor.

## One shared client, six isolated identities

A trusted host supplies a private validated seven-character roster, the six
public handles, six **host-authored synthetic profile cues**, and at most one
REALM `LocalChatProposer` instance. A missing proposer is a safe
`NO_MODEL_BOUND` hold. No model weight is downloaded, loaded, trained or
claimed to be present.

For an explicit single batch, the adapter:

1. Rejects the captain, unknown or duplicate actors, wrong world, missing
   host-reserved NPC principal, unjoined actors, or requests with no model.
   It validates every chosen actor before issuing *any* inference.
2. Uses REALM's existing same-world `ResidentSceneBuilder`: current-room
   data and room speech only after that actor's provable arrival. Actor IDs
   and recent player speech are **model context**, not commands or consent.
3. Adds only that NPC's host-authorized *synthetic* handle/profile to its
   bounded scene; it does not retrieve another character's profile or
   independent private memory. The same local proposal client is called
   sequentially for every selected actor, not cloned six times.
4. Permits only the pre-approved `say` verb through REALM's
   `ResidentController`. The host fixes actor and action receipt; model
   output cannot choose the player, teleport, command, rank or authority.
5. REALM rechecks scene arrival inside the writer transaction and maintains
   replay-bound host receipts; restarting the coordinator or retrying a
   committed receipt must not infer or commit the same speech again.

## Reproducible test

Run against a pinned, **isolated and trusted** REALM source candidate
containing host-only principal reservation, currently reviewed in
[REALM draft #193](https://github.com/thebrazenbeard/REALM/pull/193):

```sh
python tools/verify_realm_crew_turns.py --realm-src /path/to/REALM/src
python -O tools/verify_realm_crew_turns.py --realm-src /path/to/REALM/src
python -m unittest discover -s tests -q
```

The probe starts a disposable **loopback-only** chat-completion fixture,
imports only the public synthetic four-room worldpack into isolated SQLite
files, and checks six distinct style inputs, same-room history and
world isolation, rejection of human/Rylok automation and model-forged actor
identity, pre-reservation denial, speech-only permissions, model absence,
stale-scene movement during inference, receipt replay without reinference,
and no cross-world speech contamination. The responses are **fixed test
strings**, not measured neural output or six credible fictional voices.

This is not an independently qualified live NPC experience. Required before
deployment: accepted REALM NPC reservation and other session/clock security
holds; explicit host authorization for real crew actors; protected Wreckforge
canon and training-rights review; actor-scoped durable episodic memory;
inference worker resource/latency/timeout measurement on Lappy or VN2;
private migration and rollback; prompt-injection, abuse, and multiplayer
hostile testing; review of all real-character dialogue. No network port,
existing player save, deployed services or private source is changed.
