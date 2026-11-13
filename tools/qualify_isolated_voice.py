"""Research-only two voice probes in separately created synthetic worlds.

Each actor sees identical four-room geometry and same synthetic captain line,
but not earlier NPC speech. All model actions are host-gated and disposable.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import json
import re
from pathlib import Path
import sys
import tempfile
from time import monotonic
from verify_realm_crew_auth import WORLD, HUMAN, HANDLES, _roster
from qualify_real_crew_model import _mem_available_kib, _rss_kib

STYLES = {
    "SyntheticTessa": "Synthetic test-only clipped navigator. One terse statement about gyroscope alignment. No greetings, berths or cargo.",
    "SyntheticCalamar": "Synthetic test-only curious medic. One precise question about a sterile flask. No greetings, berths or cargo.",
}
DIRECTIVE_STYLES = {
    "SyntheticTessa": "SYNTHETIC ONLY. Write in first person as terse nav tech. Describe your gyroscope alignment. No greeting, no self-name, no cargo.",
    "SyntheticCalamar": "SYNTHETIC ONLY. Write in first person as a med tech. Ask a question about your sterile flask. No greeting, no self-name, no cargo.",
}


def score_synthetic_style(actor: str, utterance: str) -> dict:
    text = utterance.strip().strip("\"'").strip().lower()
    requested = "gyroscope" if actor == "SyntheticTessa" else "flask"
    return {
        "required_topic": requested in text,
        "no_generic_greeting": not any(x in text for x in ("welcome", "greetings", "cargo", "berth")),
        "no_self_address": actor.lower() not in text,
        "first_person": bool(re.search(r"\b(?:i|my|we|our)\b", text)),
        "requested_question_form": text.endswith("?") if actor == "SyntheticCalamar" else not text.endswith("?"),
    }


def run(args):
    if not args.allow_existing_loopback_model:
        raise ValueError("Existing approved loopback worker only; no new service")
    free = _mem_available_kib()
    if free is not None and free < 2 * 1024**2:
        raise RuntimeError("RAM below 2 GiB available; no inference")
    if not (args.realm_src/"realm"/"principal_roles.py").is_file():
        raise ValueError("REALM host reservation missing")
    sys.path.insert(0,str(args.realm_src.resolve()))
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from realm.gateway import Gateway
    from realm.worldpack import import_worldpack
    from realm.npc_local_model import LocalChatConfig,LocalChatProposer
    from realm.principal_roles import reserve_npc
    from driftspace.crew_turns import CrewTurnCoordinator

    class WitnessedProposer(LocalChatProposer):
        def __init__(self,config):
            super().__init__(config)
            self.views=[]
            self.responses=[]
        def propose(self,view):
            self.views.append(json.loads(view))
            output=super().propose(view)
            self.responses.append(output)
            return output
    options = LocalChatConfig(endpoint=args.endpoint,model=args.model,
                              timeout_seconds=35,max_tokens=96)
    response=[]
    for actor in ("SyntheticTessa","SyntheticCalamar"):
        with tempfile.TemporaryDirectory(prefix="driftspace-isolated-voice-") as t:
            root=Path(t); db=root/"world.sqlite3";roster=root/"roster.json"
            _roster(roster)
            import_worldpack(db,Path(__file__).resolve().parents[1]/"examples/driftspace-synthetic-demo.worldpack.v1.json")
            host=Gateway(db,world_id=WORLD)
            host.join(HUMAN)
            for a in HANDLES:
                if a!=HUMAN:
                    host.join(a);reserve_npc(host.engine,a)
            host.engine.act(HUMAN,"say SYNTHETIC CAPTAIN REQUESTS STATUS")
            style_seed = DIRECTIVE_STYLES if args.variant == "directive" else STYLES
            profile={a:style_seed.get(a,"Synthetic test-only station bystander.")
                     for a in HANDLES if a!=HUMAN}
            proposer=WitnessedProposer(options)
            crew=CrewTurnCoordinator(host,roster,world_id=WORLD,
                 human_actor_id=HUMAN,public_handles=HANDLES,styles=profile,
                 proposer=proposer,synthetic_trial=True)
            start=monotonic()
            item={"actor":actor,"style":profile[actor]}
            try:
                (result,)=crew.run_speech_turns(((actor,"isolated-voice-01"),))
                with closing(host.engine._connect()) as conn:
                    spoken=conn.execute("SELECT payload_json FROM events WHERE actor=? AND kind='say'",(actor,)).fetchall()
                item["status"]="accepted"
                item["speech"]=[json.loads(e["payload_json"])["text"] for e in spoken]
                item["rubric"]=score_synthetic_style(actor, item["speech"][0])
                item["rubric_pass"]=all(item["rubric"].values())
                item["replay"]=crew.run_speech_turns(((actor,"isolated-voice-01"),))[0].replayed
            except (ValueError,RuntimeError,TimeoutError,OSError) as exc:
                item["status"]="rejected";item["reason"]=str(exc)[:220]
            item["seconds"]=round(monotonic()-start,3)
            item["model_requests"]=len(proposer.views)
            if proposer.views:
                item["view_digest"]=hashlib.sha256(json.dumps(proposer.views[0],sort_keys=True).encode()).hexdigest()
                item["observed_prior_speakers"]=[v["speaker"] for v in proposer.views[0]["authorized_room_scene"]["recent_speech"]]
            if proposer.responses: item["proposal"]=proposer.responses[-1]["command"]
            response.append(item)
    both_pass = all(x.get("rubric_pass") is True for x in response)
    print(json.dumps({"trial":"two separate disposable worlds identical geometry",
      "variant":args.variant, "model":args.model,
      "model_pid_rss_kib":_rss_kib(args.model_pid),
      "both_styles_pass":both_pass,
      "model_results":response},sort_keys=True))
    if not both_pass:
        raise SystemExit(2)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--allow-existing-loopback-model",action="store_true")
    p.add_argument("--realm-src",required=True,type=Path)
    p.add_argument("--endpoint",required=True)
    p.add_argument("--model",required=True)
    p.add_argument("--model-pid",type=int,default=0)
    p.add_argument("--variant",choices=("baseline","directive"),default="baseline")
    run(p.parse_args())
