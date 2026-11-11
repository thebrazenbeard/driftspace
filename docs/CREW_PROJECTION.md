# Crew projection — recovered source-only slice

This module is a **public-safe extraction and hardening** of an opt-in crew
projection prototype inspected on Lappy at
`D:\VERA\experiments\driftspace-crew-api-20261109\crew_api.py`.
The original Lappy source and its private Wreckforge roster were not moved.

## Demonstrated

- A host-private JSON roster is rejected if it has duplicate fields, the wrong
  world/schema, an asserted activation, a duplicate actor, or a mismatched
  human/AI control contract.
- All six AI-designated crew members must remain model-unbound and inactive;
  the captain remains controlled by a human player.
- A caller supplies the private actor IDs and an approved seven-handle mapping
  at runtime. Only the approved **public handles** and control types are
  projected. Private IDs, character records, titles, sources, and models are
  absent from the response.
- The projection is a detached value; changing one returned crew list cannot
  mutate later responses.
- Ordinary callers cannot construct a projection directly or rebind its
  attributes after validated loading. These are misuse guards, **not** a
  Python sandbox or proof of authenticated host custody. A caller executing
  arbitrary Python in the same process can bypass language-level protections.

No real private roster or private character ID appears in this repository.
The test fixtures use synthetic actor IDs, and do not call a model or live game.

## Local test

From the repository root:

```sh
python -m unittest discover -s tests -v
python -O -m unittest discover -s tests -q
```

This is **not** a working AI crew or an exposed HTTP endpoint. The separate
REALM engine must authenticate the player, reserve NPC identities against
player credential provisioning, validate actions, and mount any future route.
The historical Lappy private candidate is separate from this branch. This
branch's current REALM `main` smoke evidence appears below; held draft PR #180
and a deployed host remain unqualified.

## Opt-in host admission candidate

`driftspace/host_admission.py` binds the validated private roster to an
existing REALM `Gateway` and exact world identity. In this *host-only adapter*,
only the bound human captain can receive or rotate a crew credential, while
an already-provisioned AI crew identity causes the adapter to fail closed.
The private actor ID is never included in its public crew response; the result
uses `player_handle: Rylok` rather than mislabeling the handle as an Engine
`player_id`.

Using a **separate trusted REALM checkout**, run the integration proof:

```sh
python tools/verify_realm_crew_auth.py --realm-src /absolute/path/to/REALM/src
python -O tools/verify_realm_crew_auth.py --realm-src /absolute/path/to/REALM/src
```

This generates synthetic actor IDs and credentials inside disposable SQLite,
starts temporary loopback-only HTTP listeners on OS-selected ports, and tests
real bearer authentication, forged NPC claims, world separation, rotation,
revocation and public-view redaction. It also deliberately proves the
**remaining bypass**: generic REALM's privileged credential provisioner can
mint an AI-name bearer token outside the adapter, and its unmodified gateway
will accept that bearer. A passing probe is **not** a deployment approval.
This source-only adapter is not installed as a REALM CLI/HTTP provisioning
policy, not transactional with the game writer, and not qualified against
REALM's held PR #180. Future integration must prevent out-of-band issuance and
model control of human Rylok in the authoritative host.

## Importable synthetic station

`examples/driftspace-synthetic-demo.worldpack.v1.json` is a deliberately
non-canonical, four-room/two-item REALM v1 worldpack. It contains no protected
character records, mission spoilers, prompts, or live-world credentials.

Its four structural tests run with the same `unittest discover` command above.
For a **separately supplied and trusted** REALM source checkout, run:

```sh
python tools/verify_realm_worldpack.py --realm-src /absolute/path/to/REALM/src
```

This creates a disposable SQLite database, imports the synthetic worldpack,
joins a synthetic human, and exercises actual `look`, movement, `take`, and
`inventory` actions. It does not operate a listener or touch a played world.
Lappy's held historical REALM PR172 source passed this smoke test on
2026-11-11. A separate isolated checkout of current REALM `main` at
`d7cacb1c5eebf7fffe39d0dcc7913ff8bc397fae` passed the same importer and
five-action smoke test on 2026-11-11. This proves only the synthetic import
and command path, **not** credential integration, a running Driftspace gateway,
or AI crew behavior.

## Remaining gates before integration

1. Host admission and source-rights review of the private roster.
2. Current REALM version/contract compatibility review.
3. A credential-bound, loopback-only integration test with revoked and
   NPC-bound credentials as negative controls.
4. Model selection and separate memory per NPC, with host-only world changes.
5. Review of all private source before any public worldpack publication.
