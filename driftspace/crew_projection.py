"""Project only approved public crew handles from a host-private roster.

Adapted from a local Driftspace crew API candidate. This pure validation layer
does not authenticate players, launch a server, schedule a model, or authorize
world mutations; those responsibilities stay with the REALM host.
"""

from __future__ import annotations

import json
from pathlib import Path
import re


APPROVED_HANDLES = frozenset({
    "Rylok", "Tessa", "Calamar", "Ghost", "Kira", "Bulwark", "Milo",
})
_ACTOR_ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")


def _reject_duplicate_fields(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Ambiguous private roster JSON")
        result[key] = value
    return result


class CrewProjection:
    """A frozen public view of an inactive, precisely validated crew proposal."""

    def __init__(self, *, world_id: str, public_crew: tuple[tuple[str, str], ...]):
        self._world_id = world_id
        self._crew = public_crew

    @classmethod
    def load(
        cls, roster_path: str | Path, *, world_id: str,
        human_actor_id: str, public_handles: dict[str, str],
    ) -> "CrewProjection":
        if not isinstance(world_id, str) or not world_id.strip():
            raise ValueError("Invalid host world binding")
        if not isinstance(human_actor_id, str) or not _ACTOR_ID.fullmatch(human_actor_id):
            raise ValueError("Invalid human actor binding")
        if not isinstance(public_handles, dict) or len(public_handles) != 7:
            raise ValueError("Seven approved public handles required")
        if any(not isinstance(k, str) or not _ACTOR_ID.fullmatch(k) for k in public_handles):
            raise ValueError("Invalid private actor binding")
        handles = list(public_handles.values())
        if (any(not isinstance(h, str) for h in handles)
                or frozenset(handles) != APPROVED_HANDLES
                or len({h.casefold() for h in handles}) != 7
                or public_handles.get(human_actor_id) != "Rylok"):
            raise ValueError("Unapproved or ambiguous public handle mapping")

        try:
            raw = json.loads(
                Path(roster_path).read_text(encoding="utf-8"),
                object_pairs_hook=_reject_duplicate_fields,
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("Private roster cannot be read") from exc
        if (not isinstance(raw, dict)
                or raw.get("schema") != "realm.private_crew_proposal.v1"
                or raw.get("world_id") != world_id
                or raw.get("classification") != "private_proposed"
                or raw.get("activated") is not False):
            raise ValueError("Private roster schema, world, or activation mismatch")

        actors = raw.get("actors")
        if not isinstance(actors, list) or len(actors) != 7:
            raise ValueError("Private roster must contain seven actors")
        by_id: dict[str, dict] = {}
        for actor in actors:
            if not isinstance(actor, dict):
                raise ValueError("Invalid private actor record")
            actor_id = actor.get("actor_id")
            if not isinstance(actor_id, str) or not _ACTOR_ID.fullmatch(actor_id):
                raise ValueError("Invalid private actor identity")
            if actor_id.casefold() in by_id:
                raise ValueError("Duplicate private actor identity")
            by_id[actor_id.casefold()] = actor
        if set(by_id) != {k.casefold() for k in public_handles}:
            raise ValueError("Private roster does not match approved actor bindings")

        public_crew = []
        for actor_id, handle in public_handles.items():
            actor = by_id[actor_id.casefold()]
            human = actor_id == human_actor_id
            expected_control = "human_pc" if human else "ai_npc"
            if (actor["actor_id"] != actor_id
                    or actor.get("control") != expected_control
                    or actor.get("ai_control_allowed") is not (not human)
                    or actor.get("model_binding", "missing") is not None
                    or actor.get("runtime_state") != "not_activated"
                    or (not human and actor.get("action_authority") != "host_validated_proposal_only")):
                raise ValueError("Private actor control or activation mismatch")
            public_crew.append((handle, "human" if human else "ai"))

        return cls(world_id=world_id, public_crew=tuple(public_crew))

    def present(self, authenticated_principal: str) -> dict:
        """Render an approved projection *after* the caller authenticates a human.

        This method does not itself verify bearer tokens or make API decisions.
        """
        if not isinstance(authenticated_principal, str) or not authenticated_principal.strip():
            raise ValueError("Authenticated player principal required")
        return {
            "ok": True,
            "world_id": self._world_id,
            "player_id": authenticated_principal,
            "status": "proposed_not_activated",
            "crew": [{"handle": handle, "control_type": control}
                     for handle, control in self._crew],
        }
