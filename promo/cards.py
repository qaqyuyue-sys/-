"""Card-style text overlays (frosted-glass cards).

Produces two lossless layers on the output clock:
  overlay.mkv  RGBA  card face: shadow, tinted glass, rim light, tag pill,
                     text and a voice progress bar that fills while the line
                     is being spoken
  mask.mkv     GRAY  card silhouette; the renderer blurs the footage through
                     it so the card reads as frosted glass over moving video
"""
import subprocess
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from .common import FONT_DIR, log

GOLD = (233, 185, 73)
WHITE = (255, 255, 255)
SHADOW_PAD = 48
RADIUS = 26
FALLBACK_FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
FONTS = {
    "serif": "SourceHanSerifCN-Bold.otf",
    "serif_heavy": "SourceHanSerifCN-Heavy.otf",
    "sans": "SourceHanSansCN-Medium.otf",
    "sans_bold": "SourceHanSansCN-Bold.otf",
}


@lru_cache(maxsize=None)
def font(kind, size):
    path = FONT_DIR / FONTS[kind]
    if not path.exists():
        path = FALLBACK_FONT
    return ImageFont.truetype(str(path), size)


def text_w(txt, fnt, tracking=0):
    if not txt:
        return 0
    return int(fnt.getlength(txt) + tracking * (len(txt) - 1))


def draw_text(draw, xy, txt, fnt, fill, tracking=0, shadow=True):
    x, y = xy
    for ch in txt:
        if shadow:
            draw.text((x, y + 2), ch, font=fnt, fill=(0, 0, 0, 90))
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += fnt.getlength(ch) + tracking


def wrap(txt, fnt, max_w):
    """Split into balanced lines, preferring breaks after punctuation."""
    if text_w(txt, fnt) <= max_w:
        return [txt]
    fits = [i for i in range(1, len(txt))
            if max(text_w(txt[:i], fnt), text_w(txt[i:], fnt)) <= max_w]
    # Never split a phrase when a punctuation break fits; otherwise balance.
    punct = [i for i in fits if txt[i - 1] in "，、；：—"]
    pool = punct or fits
    if not pool:
        return [txt]
    i = min(pool, key=lambda i: abs(len(txt[:i]) - len(txt[i:])))
    return [txt[:i], txt[i:]]


def rounded_mask(w, h, r=RADIUS):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255)
    return m


def glass_body(w, h, tint_alpha):
    """Tinted glass face with soft drop shadow, top sheen and rim light."""
    W, H = w + 2 * SHADOW_PAD, h + 2 * SHADOW_PAD
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [SHADOW_PAD, SHADOW_PAD + 14, SHADOW_PAD + w, SHADOW_PAD + h + 14],
        RADIUS, fill=(0, 0, 0, 120))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(22)))

    face = Image.new("RGBA", (w, h), (12, 20, 16, tint_alpha))
    sheen = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    sd = ImageDraw.Draw(sheen)
    for y in range(int(h * 0.55)):
        a = int(30 * (1 - y / (h * 0.55)) ** 2)
        sd.line([(0, y), (w, y)], fill=(255, 255, 255, a))
    face.alpha_composite(sheen)
    face.putalpha(ImageChops.multiply(face.getchannel("A"), rounded_mask(w, h)))
    # The face covers the shadow; cut the shadow out underneath so the glass
    # stays see-through to the blurred footage.
    hole = Image.new("L", (W, H), 255)
    hole.paste(ImageChops.invert(rounded_mask(w, h)), (SHADOW_PAD, SHADOW_PAD))
    img.putalpha(ImageChops.multiply(img.getchannel("A"), hole))
    img.alpha_composite(face, (SHADOW_PAD, SHADOW_PAD))

    rim = ImageDraw.Draw(img)
    rim.rounded_rectangle([SHADOW_PAD, SHADOW_PAD, SHADOW_PAD + w - 1, SHADOW_PAD + h - 1],
                          RADIUS, outline=(255, 255, 255, 70), width=2)
    rim.arc([SHADOW_PAD + 1, SHADOW_PAD + 1, SHADOW_PAD + 2 * RADIUS, SHADOW_PAD + 2 * RADIUS],
            180, 270, fill=(255, 255, 255, 150), width=2)
    span = int(w * 0.5)
    for i in range(span):
        a = int(150 * (1 - i / span) ** 1.5)
        rim.line([(SHADOW_PAD + RADIUS + i, SHADOW_PAD), (SHADOW_PAD + RADIUS + i, SHADOW_PAD + 1)],
                 fill=(255, 255, 255, a))
    return img


class LineCard:
    """Lower-left subtitle card: tag pill, index, narration text, progress bar."""

    PAD_X, PAD_TOP, PAD_BOTTOM = 52, 30, 30

    def __init__(self, card, W, H):
        self.card = card
        f_tag, f_idx, f_txt = font("sans_bold", 26), font("sans", 24), font("serif", 54)
        lines = wrap(card.text, f_txt, int(W * 0.72))
        line_h = int(54 * 1.42)
        tag_w = text_w(card.tag, f_tag, 3) + 32
        idx = f"{card.index:02d} / {card.total:02d}"
        row_w = tag_w + 20 + text_w(idx, f_idx)
        body_w = max([text_w(l, f_txt, 2) for l in lines] + [row_w])
        w = max(560, body_w + 2 * self.PAD_X)
        pill_h = 42
        h = self.PAD_TOP + pill_h + 18 + line_h * len(lines) + 22 + 4 + self.PAD_BOTTOM

        img = glass_body(w, h, 118)
        d = ImageDraw.Draw(img)
        ox, oy = SHADOW_PAD, SHADOW_PAD
        d.rounded_rectangle([ox + 20, oy + 28, ox + 25, oy + h - 28], 3, fill=GOLD + (255,))

        x, y = ox + self.PAD_X, oy + self.PAD_TOP
        d.rounded_rectangle([x, y, x + tag_w, y + pill_h], pill_h // 2, fill=GOLD + (235,))
        draw_text(d, (x + 16, y + 4), card.tag, f_tag, (28, 24, 16, 255), 3, shadow=False)
        draw_text(d, (x + tag_w + 20, y + 7), idx, f_idx, (255, 255, 255, 150), 0, shadow=False)
        y += pill_h + 18
        for l in lines:
            draw_text(d, (x, y), l, f_txt, WHITE + (255,), 2)
            y += line_h
        y += 22
        self.bar = (x, y, x + body_w, y + 4)
        d.rounded_rectangle(self.bar, 2, fill=(255, 255, 255, 55))

        self.face = img
        self.mask = rounded_mask(w, h)
        self.pos = (110, H - 118 - h)

    def frame_face(self, t):
        c = self.card
        p = min(1.0, max(0.0, (t - c.voice_in) / max(0.01, c.voice_out - c.voice_in)))
        if p <= 0:
            return self.face
        img = self.face.copy()
        x0, y0, x1, y1 = self.bar
        ImageDraw.Draw(img).rounded_rectangle(
            [x0, y0, x0 + max(4, int((x1 - x0) * p)), y1], 2, fill=GOLD + (255,))
        return img


class TitleCard:
    """Centred title card for the opening and ending."""

    def __init__(self, card, W, H):
        self.card = card
        f_t, f_s = font("serif_heavy", 150), font("sans", 34)
        title = card.title.replace(" ", "")
        tw, sw = text_w(title, f_t, 46), text_w(card.subtitle, f_s, 10)
        w = max(tw, sw) + 2 * 110
        h = 70 + 170 + 34 + 2 + 34 + 46 + 70
        img = glass_body(w, h, 96)
        d = ImageDraw.Draw(img)
        ox, oy = SHADOW_PAD, SHADOW_PAD
        y = oy + 52
        draw_text(d, (ox + (w - tw) / 2, y), title, f_t, WHITE + (255,), 46)
        y += 170 + 34
        cx = ox + w / 2
        d.line([(cx - 150, y), (cx - 16, y)], fill=GOLD + (230,), width=2)
        d.line([(cx + 16, y), (cx + 150, y)], fill=GOLD + (230,), width=2)
        d.polygon([(cx, y - 7), (cx + 7, y), (cx, y + 7), (cx - 7, y)], fill=GOLD + (255,))
        y += 34
        draw_text(d, (ox + (w - sw) / 2, y), card.subtitle, f_s, (255, 255, 255, 225), 10)
        self.face = img
        self.mask = rounded_mask(w, h)
        self.pos = ((W - w) // 2, int(H * 0.46) - h // 2)

    def frame_face(self, t):
        return self.face


def _ease_out(x):
    return 1 - (1 - x) ** 3


def envelope(card, t):
    """(opacity, y-offset) for a card at time t; None when hidden."""
    if t < card.t_in or t > card.t_out:
        return None
    a_in = _ease_out(min(1.0, (t - card.t_in) / 0.45))
    a_out = _ease_out(min(1.0, (card.t_out - t) / 0.3))
    return min(a_in, a_out), int((1 - a_in) * 28 - (1 - a_out) * 10)


def _fade(img, alpha):
    if alpha >= 0.999:
        return img
    out = img.copy()
    out.putalpha(out.getchannel("A").point(lambda v: int(v * alpha)))
    return out


def render_layers(timeline, W, H, fps, out_dir):
    out_dir = Path(out_dir)
    overlay, mask = out_dir / "overlay.mkv", out_dir / "mask.mkv"
    cards = [(LineCard if c.style == "line" else TitleCard)(c, W, H) for c in timeline.cards]
    for i, c in enumerate(cards):
        c.face.save(out_dir / f"card_{i:02d}.png")

    def enc(path, pix):
        return subprocess.Popen(
            ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", pix,
             "-s", f"{W}x{H}", "-r", str(fps), "-i", "pipe:0",
             "-c:v", "ffv1", "-pix_fmt", "bgra" if pix == "rgba" else "gray", str(path)],
            stdin=subprocess.PIPE)

    p_ov, p_mk = enc(overlay, "rgba"), enc(mask, "gray")
    empty_ov = bytes(W * H * 4)
    empty_mk = bytes(W * H)
    n = int(round(timeline.duration * fps))
    log(f"生成卡片图层 {n} 帧 …")
    for f in range(n):
        t = f / fps
        live = [(c, envelope(c.card, t)) for c in cards]
        live = [(c, e) for c, e in live if e]
        if not live:
            p_ov.stdin.write(empty_ov)
            p_mk.stdin.write(empty_mk)
            continue
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        mk = Image.new("L", (W, H), 0)
        for c, (alpha, dy) in live:
            x, y = c.pos
            ov.alpha_composite(_fade(c.frame_face(t), alpha),
                               (x - SHADOW_PAD, y - SHADOW_PAD + dy))
            mk.paste(c.mask.point(lambda v: int(v * alpha)), (x, y + dy), c.mask)
        p_ov.stdin.write(ov.tobytes())
        p_mk.stdin.write(mk.tobytes())
    for p in (p_ov, p_mk):
        p.stdin.close()
        if p.wait() != 0:
            raise RuntimeError("card layer encode failed")
    return overlay, mask
