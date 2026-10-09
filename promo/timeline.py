"""Build the edit timeline from the script and measured voice durations.

Every time value here is on the final output clock, so the same numbers drive
the shot cuts, the voice placement and the card animation — that is what keeps
voice, picture and on-screen text in sync.
"""
from dataclasses import dataclass, field


@dataclass
class Shot:
    id: str
    start: float          # cut time on the output clock
    length: float         # visible length (excluding the outgoing dissolve)


@dataclass
class Card:
    style: str            # "line" | "title"
    t_in: float
    t_out: float
    voice_in: float = 0.0
    voice_out: float = 0.0
    tag: str = ""
    text: str = ""
    title: str = ""
    subtitle: str = ""
    index: int = 0
    total: int = 0


@dataclass
class Voice:
    file: str
    start: float
    duration: float


@dataclass
class Timeline:
    duration: float
    shots: list = field(default_factory=list)
    cards: list = field(default_factory=list)
    voices: list = field(default_factory=list)


def build(script, voices):
    v = script["video"]
    lead, tail = v["lead_in"], v["tail"]
    segments = []

    op = script.get("opening")
    if op:
        segments.append(("title", op["duration"], op, None))
    for line in script["lines"]:
        dur = lead + voices[line["id"]]["duration"] + tail
        segments.append(("line", dur, line, voices[line["id"]]))
    end = script.get("ending")
    if end:
        segments.append(("title", end["duration"], end, None))

    tl = Timeline(duration=0.0)
    n_lines = len(script["lines"])
    t = 0.0
    line_no = 0
    raw_shots = []
    for kind, dur, seg, voice in segments:
        ids = seg["shots"]
        each = dur / len(ids)
        for i, sid in enumerate(ids):
            raw_shots.append((sid, t + i * each, each))

        card = seg.get("card", {})
        if kind == "line":
            line_no += 1
            vin, vout = t + lead, t + lead + voice["duration"]
            tl.voices.append(Voice(voice["file"], vin, voice["duration"]))
            tl.cards.append(Card(
                style="line", t_in=vin - 0.15, t_out=min(vout + 0.3, t + dur - 0.02),
                voice_in=vin, voice_out=vout, tag=card.get("tag", ""),
                text=card.get("text", seg["voice"]), index=line_no, total=n_lines))
        else:
            tl.cards.append(Card(
                style="title", t_in=t + 0.6, t_out=t + dur - 0.35,
                title=card.get("title", ""), subtitle=card.get("subtitle", "")))
        t += dur

    # Consecutive uses of the same clip play on continuously as one shot.
    for sid, start, length in raw_shots:
        if tl.shots and tl.shots[-1].id == sid:
            tl.shots[-1].length += length
        else:
            tl.shots.append(Shot(sid, start, length))

    tl.duration = t
    return tl


def describe(tl):
    rows = [f"总时长 {tl.duration:.2f}s，镜头 {len(tl.shots)} 个，卡片 {len(tl.cards)} 张"]
    for s in tl.shots:
        rows.append(f"  {s.start:6.2f}s  +{s.length:4.2f}s  {s.id}")
    for c in tl.cards:
        label = c.text or c.title
        rows.append(f"  卡片 {c.t_in:6.2f} → {c.t_out:6.2f}s  {label}")
    return "\n".join(rows)
