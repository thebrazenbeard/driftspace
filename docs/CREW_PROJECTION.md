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
The private candidate tested against historical REALM source on Lappy; that
is not evidence of integration with current REALM main or its held draft PR.

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
2026-11-11, but the current engine and a live deployment are still unverified.

## Remaining gates before integration

1. Host admission and source-rights review of the private roster.
2. Current REALM version/contract compatibility review.
3. A credential-bound, loopback-only integration test with revoked and
   NPC-bound credentials as negative controls.
4. Model selection and separate memory per NPC, with host-only world changes.
5. Review of all private source before any public worldpack publication.
