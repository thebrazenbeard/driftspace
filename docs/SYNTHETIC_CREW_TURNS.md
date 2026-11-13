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

## Six-person real-model hostile voice test

`tools/qualify_real_six_crew.py` separately supports an operator-initiated
sequence of 1–6 real requests to an **already-running** literal loopback
model endpoint. Its `--max-actors` scope is bounded, its input contains
only disposable synthetic world context, and it never starts or installs
a worker. It records per-character host identity, distinct prompt digests,
model-only latency, acceptance/rejection, receipt replay and whether the
model copied a previous NPC's scene dialogue. It **exits 2** when all
selected synthetic voices are not accepted and distinct; an HTTP 200 or
six actor-bound receipts is not a voice-quality success.

On 2026-11-12, **before the echo-safety correction**, an existing CPU Granite
3.3 2B worker returned an identical Tessa-specific sentence for all **six**
separately submitted synthetic actors. Host principal/receipt ownership was
correct for all six, but **six-way voice distinctness failed**. Observed
model-only latencies for that run were 14.600, 15.909, 16.688, 17.913,
18.420 and 19.155 seconds (six-sample median 17.3 seconds); timings were
substantially faster in another small run, so this is not a production
p50/p95 guarantee. Do not advertise it as six working AI personalities.

A later two-actor experiment verified the **actual prompts were different**:
Tessa and Calamar were correctly bound to their own source identities and had
different SHA-256 scene digests; Calamar's newly built scene included Tessa's
recent spoken line, and the model parroted it. The newly implemented setting
guard rejected Calamar's duplicate rather than commit the wrong voice.
It also denies duplicate proposals **inside a single batch**, where REALM
snapshots each scene before any speech is committed. Regression tests first
reproduced both defects (RED), then passed after the quality guard (GREEN).
The guard normalizes case and surrounding quotes only for equality and does
not rewrite an illegal command into an allowed one. It is a conservative
synthetic dialogue-quality hold, not a guarantee of convincing personalities,
a model-security proof, or a reason to relax REALM host permissions.

A later actor's rejected model proposal does **not** roll back an earlier
already-committed resident turn. Caller recovery must use each stable
action receipt, not assume all-or-nothing six-actor transactions. A server
replay, prompt injection, secret leakage, cross-world memory and poor dialogue
remain independent failure modes to test. None of this has been installed in
the running private VN2 Driftspace world.

## Next hostile trial: single-flight, retries and real voice falsifiers (2026-11-13)

All changes in this section are **synthetic-only**, opt-in, and source-level.
They do not change the actual Rylok world or activate any Wreckforge character.

**Same-process inference admission:** a shared local model endpoint can have
only one outstanding Driftspace crew batch at a time, even if two independent
coordinators use different `LocalChatProposer` objects pointing at it. A
simultaneous second request fails closed with a retryable busy error. The
first batch retains its exact host receipt and releases the lock on success
*or failure*. This is *not* cross-process admission, a distributed lease,
or a scheduler. The test first proved the pre-fix concurrency defect with
two actual overlapping loopback HTTP requests, then passed after the change.

**Optional quality retry:** `max_quality_retries=0` is the conservative
default. The trusted synthetic host may opt in to **one** additional proposal
if a candidate repeats a room/batch dialogue template. No rejected draft
is committed, copied into the next prompt, or granted authority. The second
proposal is held to the same host actor, scene, `say`-only permission and
stable action receipt. A second echo fails. Malformed and forbidden verbs
are *not* retried and never become authorized by this mechanism. At most
two model requests can occur for the one attempted turn, which may double
CPU latency.

**Name-substitution falsifier:** in a real shared-room two-character test,
a one-retry policy initially produced two different strings but the exact
same greeting template, substituting `SyntheticCalamar` for
`SyntheticTessa`. The earlier exact-string uniqueness counter would
have misclassified this as two voices. A synthetic-only, conservative
name-masking comparison now detects this obvious template reuse both in
recent authorized room dialogue and between pre-snapshotted same-batch
proposals. The associated game-effect regression **failed before** and
passed after the correction. This matcher may reject legitimate repeated
boilerplate and cannot prove literary distinctiveness; it is a bounded
negative control, not a classifier for approved canon characters.

**Real post-fix observation:** the two-character shared-room trial with
`--max-quality-retries 1 --max-actors 2` made **three** local Granite
model requests. Tessa's speech committed and replayed; Calamar's initial
echo and subsequent renamed copy were rejected, leaving **one accepted**
speaker. The script correctly reported an unsuccessful two-voice trial.
The model inputs remained actor-bound and distinct. No dropped rejection
was converted into a success record.

**Isolated context experiment:** `tools/qualify_isolated_voice.py` constructs
two entirely separate synthetic SQLite worlds, each with identical geometry
and the same captain message. Neither actor receives the other's dialogue.
An existing Granite 3.3 2B worker generated different sentences for Tessa
and Calamar in this condition, identifying earlier room speech as a
material contributor to the observed echoing. But it still ignored parts
of the synthetic persona instructions. A second, explicit first-person
style variant caused Tessa to mention a gyroscope and Calamar a sterile
flask, yet Tessa spoke without first-person phrasing and Calamar made a
statement rather than the required question. Under the full typed
synthetic style rubric (topic, greeting avoidance, self-address, first-person
voice, sentence form), **neither response passes**. These are two single
samples, not blinded character evaluation, and the styles are invented
experimental prompts rather than the author's real crew personalities.

Rerun the isolated test only with an operator-approved already-running
literal-loopback model and sufficient available host RAM:

```sh
python tools/qualify_isolated_voice.py \
  --allow-existing-loopback-model --variant directive \
  --realm-src /trusted/REALM/src \
  --endpoint http://127.0.0.1:LOCAL_PORT/v1/chat/completions \
  --model approved-local-model-id
```

The stand-alone script reports proposals, actor-bound input hashes,
status, elapsed time and explicit rubric flags; it **exits 2** unless both
requested synthetic styles pass the declared rubric, so an HTTP 200 or
accepted host receipt cannot be silently counted as voice success. It does
not train, fine-tune, install a service, publish character source, or
classify real Wreckforge speech as canon.

**Release ceiling:** one shared 2B CPU inference endpoint is technically
usable for a disposable real speech turn; the **six-character identity,
memory, voice and throughput acceptance criteria remain unmet**. The game
host must continue to reject unauthorized effects. REALM NPC reservation,
credential/session race holds, continuity custody, approved character
dialogue sources, public transport, memory privacy and deployment approval
are independent gates.
