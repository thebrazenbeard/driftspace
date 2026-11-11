"""Public-safe color, help and scoped social receipts for Driftspace's terminal pilot.

Social receipts are pilot-local; they do NOT imply multiplayer delivery or AI crew.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re
import sqlite3

ROOMS = frozenset({"Arrival Platform", "Exchange Hall", "Service Bay", "Viewing Gallery"})
_SGR = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_CTRL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_SOCIAL = {
    "emote": "room",
    "yell": "world",
    "ooc": "world",
    "crewchat": "crew",
}
# Named colors and explicit scene cues in non-canonical room prose, never player speech.
# A black-on-light background keeps "black" visible on dark MUD themes.
PROSE_COLORS = {
    # Classic ANSI family, tuned for readability on a dark MUD background.
    "black": "30;47",                 # black on pale background
    "red": "38;2;255;105;97",
    "green": "38;2;90;200;130",
    "yellow": "38;2;255;225;80",
    "blue": "38;2;100;160;255",
    "magenta": "38;2;255;0;255",
    "cyan": "38;2;0;255;255",
    "white": "38;2;245;245;245",
    "bright black": "38;2;144;144;144",
    "bright red": "38;2;255;85;85",
    "bright green": "38;2;120;255;140",
    "bright yellow": "38;2;255;240;120",
    "bright blue": "38;2;98;187;255",
    "bright magenta": "38;2;255;125;255",
    "bright cyan": "38;2;120;255;255",
    "bright white": "38;2;255;255;255",
    # Extended color words and UK/US spellings used in descriptive prose.
    "copper": "38;2;184;115;51",
    "amber": "38;2;255;191;0",
    "silver": "38;2;192;192;192",
    "gold": "38;2;255;215;0",
    "orange": "38;2;255;160;65",
    "purple": "38;2;187;134;252",
    "violet": "38;2;186;145;255",
    "pink": "38;2;255;105;180",
    "light pink": "38;2;255;182;193",
    "dark pink": "38;2;225;100;150",
    "teal": "38;2;0;180;170",
    "turquoise": "38;2;64;224;208",
    "aqua": "38;2;0;255;255",
    "navy": "38;2;106;148;220",
    "indigo": "38;2;140;118;238",
    "lime": "38;2;170;255;90",
    "olive": "38;2;175;177;90",
    "brown": "38;2;173;112;70",
    "crimson": "38;2;230;50;80",
    "scarlet": "38;2;255;64;64",
    "maroon": "38;2;185;95;116",
    "cream": "38;2;245;232;190",
    "beige": "38;2;226;208;175",
    "slate": "38;2;150;165;180",
    "grey": "38;2;170;170;170",
    "gray": "38;2;170;170;170",
    "light grey": "38;2;211;211;211",
    "light gray": "38;2;211;211;211",
    "light-grey": "38;2;211;211;211",
    "light-gray": "38;2;211;211;211",
    "dark grey": "38;2;144;144;144",
    "dark gray": "38;2;144;144;144",
    "dark-grey": "38;2;144;144;144",
    "dark-gray": "38;2;144;144;144",
    "light blue": "38;2;150;205;255",
    "light green": "38;2;144;238;144",
    "light cyan": "38;2;165;243;252",
}
# Longest phrases first: "light grey" must be a single semantic span.
_PROSE_WORD = re.compile(
    r"\b(?:" + "|".join(
        re.escape(name) for name in sorted(PROSE_COLORS, key=len, reverse=True)
    ) + r")\b",
    re.IGNORECASE,
)



def terminal_palette() -> str:
    """ANSI swatches suitable for Mudlet's text console."""
    groups = (
        ("Classic", ("black", "red", "green", "yellow", "blue", "magenta", "cyan", "white")),
        ("Bright", ("bright black", "bright red", "bright green", "bright yellow",
                    "bright blue", "bright magenta", "bright cyan", "bright white")),
        ("Extended", ("pink", "light grey", "dark grey", "copper", "amber", "silver",
                      "gold", "teal", "turquoise", "purple", "orange")),
    )
    output = ["Driftspace ANSI color palette"]
    for title, names in groups:
        samples = "   ".join(
            "\x1b[" + PROSE_COLORS[name] + "m" + name + "\x1b[0m"
            for name in names
        )
        output.append(title + ": " + samples)
    output.append("Color words, material cues, and lighting intensity are styled in room descriptions only.")
    return "\n".join(output)


# Contextual spans are deliberately bounded to explicit scene cues.
# A bare "table" has no known material; only specified wood/metal gets color.
_MATERIAL_COLOR = {
    "wooden": "38;2;159;103;58",
    "wood": "38;2;159;103;58",
    "oak": "38;2;159;103;58",
    "pine": "38;2;159;103;58",
    "mahogany": "38;2;159;103;58",
    "steel": "38;2;157;173;185",
    "iron": "38;2;157;173;185",
    "metal": "38;2;157;173;185",
    "aluminum": "38;2;157;173;185",
    "aluminium": "38;2;157;173;185",
    "titanium": "38;2;157;173;185",
}
_MATERIAL = "|".join(_MATERIAL_COLOR)
_FURNISHING = (
    r"tables?|desks?|benches?|chairs?|doors?|panels?|crates?|"
    r"shelves?|lockers?|bulkheads?|edges?|racks?|frames?|stools?"
)
# Match material->furnishing and furnishing->material, but not ambiguous nouns.
_MATERIAL_BEFORE = re.compile(
    rf"\b(?:weathered\s+|polished\s+|rusted\s+)?(?P<material>{_MATERIAL})"
    rf"\s+(?:{_FURNISHING})\b", re.IGNORECASE,
)
_MATERIAL_AFTER = re.compile(
    rf"\b(?:{_FURNISHING})\s+(?:(?:made|built|crafted)\s+(?:of|from)\s+|of\s+)"
    rf"(?P<material>{_MATERIAL})\b", re.IGNORECASE,
)
_LIGHTING = re.compile(
    r"\b(?P<level>faint|dim|weak|low|flickering|bright|brilliant|blinding|harsh)"
    r"\s+(?:white\s+|amber\s+|yellow\s+|blue\s+|orange\s+)?"
    r"(?:floor\s+|overhead\s+|ceiling\s+|warning\s+|status\s+|work\s+|emergency\s+)?"
    r"(?:lights?|lamps?|beacons?|glows?|bulbs?)\b",
    re.IGNORECASE,
)
_DIM_LIGHT = frozenset({"faint", "dim", "weak", "low", "flickering"})


# A disjunction like "wooden or steel table" is NOT evidence of steel.
_AMBIGUOUS_MATERIAL_PREFIX = re.compile(
    rf"\b(?:{_MATERIAL})\s+or\s+$", re.IGNORECASE,
)
_AMBIGUOUS_LIGHT_PREFIX = re.compile(
    r"\b(?:faint|dim|weak|low|bright|brilliant|blinding|harsh)"
    r"\s+or\s+$", re.IGNORECASE,
)


def _semantic_prose_spans(line: str) -> list[tuple[int, int, str]]:
    """Prioritize grounded lighting/material phrases over individual color words.

    Return non-overlapping spans; no inferred material for unspecified objects.
    Every ANSI sequence resets before the next literal character.
    """
    proposals = []
    for pattern in (_MATERIAL_BEFORE, _MATERIAL_AFTER):
        for match in pattern.finditer(line):
            if _AMBIGUOUS_MATERIAL_PREFIX.search(line[max(0, match.start() - 36):match.start()]):
                continue
            color = _MATERIAL_COLOR[match.group("material").casefold()]
            proposals.append((match.start(), match.end(), color))
    for match in _LIGHTING.finditer(line):
        if _AMBIGUOUS_LIGHT_PREFIX.search(line[max(0, match.start() - 36):match.start()]):
            continue
        dim = match.group("level").casefold() in _DIM_LIGHT
        proposals.append((
            match.start(), match.end(),
            "38;2;154;129;54" if dim else "38;2;255;248;215",
        ))
    for match in _PROSE_WORD.finditer(line):
        proposals.append((
            match.start(), match.end(),
            PROSE_COLORS[match.group(0).casefold()],
        ))
    # Earlier cue wins; for tied start prefer the full phrase over a color word.
    proposals.sort(key=lambda span: (span[0], -(span[1] - span[0])))
    chosen = []
    stop = 0
    for start, end, color in proposals:
        if start >= stop:
            chosen.append((start, end, color))
            stop = end
    return chosen


def _color_room_prose(line: str) -> str:
    pieces = []
    previous = 0
    for start, end, ansi in _semantic_prose_spans(line):
        pieces.append(line[previous:start])
        pieces.append("\x1b[" + ansi + "m" + line[start:end] + "\x1b[0m")
        previous = end
    pieces.append(line[previous:])
    return "".join(pieces)


MUD_HELP = (
    "Movement: north/south/east/west (n/s/e/w), look, where\n"
    "Items: take/get/pickup/obtain <item>, drop/discard <item>, inventory, items\n"
    "Inspect: examine/inspect <item>, look at <item>; map (discovered rooms only)\n"
    "Comms: say <text>, emote <action>, yell <text>, ooc <text>, crewchat <text>\n"
    "Information: who, listen, history [1-50], socials, palette/colors, help, quit\n"
    "This is a synthetic private pilot. Socials are saved locally; AI crew"
    " and live multiplayer channel delivery are NOT online."
)

@dataclass(frozen=True)
class Social:
    scope: str
    kind: str
    text: str


def _clean(text: str) -> str:
    return _CTRL.sub("", _SGR.sub("", text)).strip()


def parse_social(raw: str) -> Social | None:
    verb, _, text = raw.strip().partition(" ")
    kind = verb.casefold()
    if kind not in _SOCIAL:
        return None
    clean = _clean(text)
    if not clean:
        raise ValueError(f"{kind}: message required")
    if len(clean) > 280:
        raise ValueError("Social messages must be 280 characters or fewer")
    return Social(_SOCIAL[kind], kind, clean)


def render_terminal(text: str, *, ansi: bool = True) -> str:
    if not ansi:
        return text
    def color(line: str) -> str:
        clean = _SGR.sub("", line)
        if clean in ROOMS:
            return "\x1b[1;36m" + clean + "\x1b[0m"
        # Labels remain neutral; only the values carry semantic color.
        for label, value_color in (
            ("Exits:", "1;33"),          # accessible directions: yellow
            ("Items:", "1;32"),          # visible items: green
            ("You carry:", "1;32"),      # held items: green
            ("You take ", "1;32"),
            ("You drop ", "1;32"),
            ("You say:", "1;35"),        # messages: magenta
            ("You yell:", "1;35"),
            ("[OOC]", "1;35"),
            ("[Wreckforge]", "1;35"),
        ):
            if clean.startswith(label):
                value = clean[len(label):].strip()
                colored_label = "\x1b[37m" + label.rstrip() + "\x1b[0m"
                if not value:
                    return colored_label
                return colored_label + " \x1b[" + value_color + "m" + value + "\x1b[0m"
        if clean.startswith(("Unknown command", "Access denied", "Command rejected")):
            return "\x1b[1;31m" + clean + "\x1b[0m"
        return clean
    rendered = []
    inside_description = False
    for line in text.split("\n"):
        clean = _SGR.sub("", line)
        if clean in ROOMS:
            inside_description = True
            rendered.append(color(clean))
        elif clean.startswith("Exits:"):
            inside_description = False
            rendered.append(color(clean))
        elif inside_description:
            rendered.append(_color_room_prose(clean))
        else:
            rendered.append(color(clean))
    return "\n".join(rendered)


def terminal_prompt() -> str:
    return "\x1b[1;36mDriftspace>\x1b[0m "

class SocialStore:
    """Scoped single-player pilot receipts, kept OUT of host/public feed."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(mode=0o600, exist_ok=True)
        os.chmod(self.path, 0o600)
        with self._db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT NOT NULL,
                kind TEXT NOT NULL,
                scope TEXT NOT NULL,
                message TEXT NOT NULL
            )""")

    def _db(self):
        return sqlite3.connect(self.path, timeout=5)

    def append(self, actor: str, social: Social) -> None:
        if actor != "Rylok" or social.scope not in {"room", "world", "crew"}:
            raise ValueError("This pilot only supports Captain Rylok")
        with self._db() as db:
            db.execute(
                "INSERT INTO events (actor,kind,scope,message) VALUES (?,?,?,?)",
                (actor, social.kind, social.scope, social.text)
            )

    def count(self) -> int:
        with self._db() as db:
            return int(db.execute("SELECT COUNT(*) FROM events").fetchone()[0])

    def recent(self, scope: str) -> list[tuple[str, str, str]]:
        if scope not in {"room", "world", "crew"}:
            raise ValueError("Invalid pilot social scope")
        with self._db() as db:
            return list(db.execute(
                "SELECT actor,kind,message FROM events WHERE scope=? ORDER BY id DESC LIMIT 12",
                (scope,)
            ))
