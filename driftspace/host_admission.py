"""Opt-in host-side admission for the proposed Driftspace crew.

The REALM operator must use this adapter for captain credential issuance and
crew-facing reads. It is not installed in generic REALM routes or CLI, and
cannot restrict arbitrary privileged code in the same host process.
"""

from __future__ import annotations

from contextlib import closing
from pathlib import Path

from .crew_projection import CrewProjection


class CrewHostAdmission:
    """Bind a validated private crew proposal to one real REALM Gateway."""

    __slots__ = ("_gateway", "_world_id", "_human_id", "_npc_ids", "_projection")

    def __init__(self, *args, **kwargs):
        raise TypeError("Use CrewHostAdmission.load()")

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("CrewHostAdmission is read-only")

    @classmethod
    def load(
        cls, gateway: object, roster_path: str | Path, *, world_id: str,
        human_actor_id: str, public_handles: dict[str, str],
    ) -> "CrewHostAdmission":
        # Import only on opt-in use; pure projection tests need no REALM package.
        from realm.gateway import Gateway

        if not isinstance(gateway, Gateway) or gateway.world_id != world_id:
            raise ValueError("An exact-world REALM Gateway is required")
        if getattr(gateway, "scoped_credentials", None) is not None:
            raise ValueError("Scoped REALM credentials require separate admission qualification")
        projection = CrewProjection.load(
            roster_path, world_id=world_id,
            human_actor_id=human_actor_id, public_handles=public_handles,
        )
        admission = object.__new__(cls)
        object.__setattr__(admission, "_gateway", gateway)
        object.__setattr__(admission, "_world_id", world_id)
        object.__setattr__(admission, "_human_id", human_actor_id)
        object.__setattr__(admission, "_npc_ids", frozenset(
            key.casefold() for key in public_handles if key != human_actor_id
        ))
        object.__setattr__(admission, "_projection", projection)
        admission._check_world_and_reservations()
        return admission

    def _check_world_and_reservations(self) -> None:
        if self._gateway.world_id != self._world_id:
            raise ValueError("Crew admission world binding changed")
        with closing(self._gateway.engine._connect()) as db:
            row = db.execute(
                "SELECT value FROM world_meta WHERE key='world_id'"
            ).fetchone()
            if row is None or row[0] != self._world_id:
                raise ValueError("Stored world binding differs from crew admission")
            # Fail closed if a privileged generic provisioner bypassed us.
            names = db.execute("SELECT player_name FROM player_credentials").fetchall()
            if any(str(name[0]).casefold() in self._npc_ids for name in names):
                raise ValueError("A reserved AI crew identity has a player credential")

    def _human(self, actor_id: str) -> None:
        if type(actor_id) is not str or actor_id != self._human_id:
            raise ValueError("Only the bound human captain can receive a crew credential")

    def provision_captain(self, actor_id: str) -> str:
        """Host operator only; never expose credential issuance over HTTP."""
        self._check_world_and_reservations()
        self._human(actor_id)
        return self._gateway.credentials.provision(actor_id)

    def rotate_captain(self, actor_id: str) -> str:
        self._check_world_and_reservations()
        self._human(actor_id)
        return self._gateway.credentials.rotate(actor_id)

    def authenticate_captain(self, token: str) -> str | None:
        """Resolve the canonical private actor name without trusting claims."""
        self._check_world_and_reservations()
        actor = self._gateway.credentials.authenticate(token)
        return actor if actor == self._human_id else None

    def public_crew_for_token(self, token: str) -> dict:
        """Return public handles only after REALM credential verification."""
        if self.authenticate_captain(token) is None:
            raise ValueError("A valid human captain credential is required")
        view = self._projection.present("Rylok")
        # CrewProjection's generic `player_id` field would be misleading here:
        # the real Engine actor is a private ID, not the public handle Rylok.
        view.pop("player_id")
        view["player_handle"] = "Rylok"
        return view
