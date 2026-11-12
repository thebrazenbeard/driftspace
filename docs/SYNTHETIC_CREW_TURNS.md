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

## Opt-in real-model canary (not a character evaluation)

The separate `tools/qualify_real_crew_model.py` is a **real-model, single-
NPC** canary against an already-running, loopback-bound local chat-completions
server. It requires explicit `--allow-existing-loopback-model`, an explicit
pinned/trusted REALM source directory, a host-selected model identifier, and
a host-selected literal loopback endpoint. It refuses to request inference
when available system memory is below 2 GiB. No model, service or weight is
installed or started. All actions remain in disposable synthetic SQLite.
The script prints elapsed time, model-request count, memory observations,
a synthetic NPC's accepted/rejected speech and durable host receipt. A
rejected model action exits nonzero (status 2) rather than silently appearing
as a passing test. No credentials, raw private Wreckforge canon or user
messages are sent.

Example on a host with an **already-running**, independently approved model:

```sh
python tools/qualify_real_crew_model.py \
  --allow-existing-loopback-model \
  --realm-src /trusted/REALM/src \
  --endpoint http://127.0.0.1:LOCAL_PORT/v1/chat/completions \
  --model approved-local-model-id \
  --timeout 45 --max-tokens 96
```

One bounded VN2 experiment on 2026-11-12 used an existing CPU llama-server
with a Granite 3.3 2B instruct Q4_K_M GGUF (1,545,303,616 bytes, observed
SHA-256 `555b91485955bc96eb445b57dd4bbf8809aa7d8cce7c313f4f8bc5b2340896b4`).
At first the server produced a model-authored command outside the permitted
`say` verb, correctly rejected without game effects. A stricter prompt
still yielded an invalid `say,` command, correctly rejected. After clarifying
the exact `say ` syntax, **one genuine neural proposal was accepted** and
committed to disposable SQLite as SyntheticTessa speech; one host receipt was
replayed without second inference. Observed successful single-turn latency
was ~5.8s on this CPU host. It is a *single observed sample*, not a latency
distribution, six-voice quality benchmark, production resource budget,
licensing endorsement, or an indication the actual crew is activated.
