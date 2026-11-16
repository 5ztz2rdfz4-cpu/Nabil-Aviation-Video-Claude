"""Render all frames of EP01 Flying Tiger Line Flight 66 (flat 2D style, simple top-view icons).
usage: python3 comp/render.py [--test t1,t2,...]
"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from gfx import *

TL = json.load(open(os.path.join(ROOT, "build", "vo", "timeline.json")))
LINES = TL["lines"]
LN = {l["key"]: l for l in LINES}
END = TL["end"]
OUT = os.path.join(ROOT, "build", "frames")
CHUNKS = [c for l in LINES for c in l["chunks"]]


def st(k):
    return LN[k]["start"]


def wd(k, i):  # start time of word i of line k
    return LN[k]["words"][i][0]


IMPACT = wd("a3", 9) + 0.55  # just after "Puchong"

# ------------------------------------------------------------------ common overlays
def tag(d, text, kind="ilu"):
    col = {"ilu": ORANGE, "arkib": (230, 230, 230), "tx": (230, 90, 80)}[kind]
    f = F("mono_b", 24)
    w = text_w(text, f, 3)
    d.rounded_rectangle([60, 150, 60 + w + 58, 196], radius=23, fill=(0, 0, 0, 130), outline=(*col, 200), width=2)
    d.ellipse([78, 166, 92, 180], fill=(*col, 255))
    draw_text(d, (104, 173), text, f, (*col, 255), 3, "lm")


def brand(d):
    draw_text(d, (W - 60, 173), "NABIL AVIATION", F("mono_b", 22), (255, 255, 255, 120), 4, "rm")


def subtitle(d, t):
    for a, b, txt in CHUNKS:
        if a - 0.05 <= t <= b:
            al = clamp((t - a + 0.05) / 0.1) * clamp((b - t) / 0.1)
            f = F("inter_sb", 50)
            lines = wrap(txt, f, 900)
            y0 = 1450 - 33 * (len(lines) - 1)
            for i, s in enumerate(lines):
                w = f.getlength(s); y = y0 + i * 66
                d.rounded_rectangle([W / 2 - w / 2 - 22, y - 35, W / 2 + w / 2 + 22, y + 33], radius=12, fill=(0, 0, 0, int(160 * al)))
                d.text((W / 2, y), s, font=f, fill=(255, 255, 255, int(255 * al)), anchor="mm")
            return


def headline(d, text, y, size=120, a=1.0, col=(255, 255, 255), font="bebas", tracking=2):
    draw_text(d, (W / 2, y), text, F(font, size), rgba(col, a), tracking, "mm")


def finish(arr, t, overlay, grain=0.03, vign=0.5):
    lum = arr.mean(axis=2, keepdims=True)
    arr = arr * 0.88 + lum * 0.12
    arr = arr * np.array([0.97, 1.0, 1.04], np.float32)
    yy, xx = np.ogrid[0:H, 0:W]
    v = 1 - vign * (((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    arr = arr * np.clip(v, 0, 1)[..., None]
    rng = np.random.default_rng(int(t * FPS))
    g = rng.standard_normal((H // 2, W // 2)).astype(np.float32)
    g = np.repeat(np.repeat(g, 2, 0), 2, 1)
    arr = arr + g[..., None] * grain
    im = to_im(arr).convert("RGBA")
    im.alpha_composite(overlay)
    return im.convert("RGB")


def composite(arr, layer):
    return to_f(Image.alpha_composite(to_im(arr).convert("RGBA"), layer).convert("RGB"))


def bg_night(t, k=1):
    arr = vgrad(H, (8, 14, 26), (22, 34, 52))
    return fog_over(arr, t, 0.3, k=k, color=(40, 56, 76))


def hills(arr, t, y=1250, col=(14, 20, 30), amp=1.0, seed=0, drift=6):
    """layered hill silhouettes along the bottom."""
    im = Image.new("RGBA", (W, H)); d = ImageDraw.Draw(im)
    for j, (yy, c, s) in enumerate([(y - 60, (30, 40, 56), 0.6), (y, col, 1.0)]):
        pts = [(0, H)]
        for x in range(0, W + 20, 20):
            xx = x + t * drift * s
            h = 80 * math.sin(xx * 0.004 + seed + j) + 45 * math.sin(xx * 0.011 + 2 + j) + 20 * math.sin(xx * 0.03 + j)
            pts.append((x, yy - h * amp))
        pts.append((W, H))
        d.polygon(pts, fill=(*c, 255))
    return composite(arr, im)


# ------------------------------------------------------------------ map
MAP = json.load(open(os.path.join(A, "sea_map.json")))
SUBANG = (101.549, 3.131)
SIN = (103.99, 1.36)
HKG = (114.20, 22.32)


def draw_map(arr, cen, zoom, cy=860, hl="Malaysia"):
    cl = math.cos(math.radians(cen[1]))
    def P(lon, lat):
        return (W / 2 + (lon - cen[0]) * cl * zoom, cy - (lat - cen[1]) * zoom)
    im = Image.new("RGBA", (W, H)); md = ImageDraw.Draw(im)
    step = 5 if zoom < 120 else 1
    for lon in range(80, 141, step):
        md.line([P(lon, -15), P(lon, 40)], fill=(40, 70, 100, 90), width=1)
    for lat in range(-15, 41, step):
        md.line([P(80, lat), P(140, lat)], fill=(40, 70, 100, 90), width=1)
    for poly in MAP:
        if len(poly["p"]) > 2:
            c = (78, 96, 104, 255) if poly["name"] == hl else (48, 62, 70, 255)
            md.polygon([P(*p) for p in poly["p"]], fill=c, outline=(120, 140, 150, 255))
    return composite(arr, im), P


def sc_map_hook(t, d, t0, t1):
    k = t - t0
    arr = vgrad(H, (10, 22, 36), (14, 30, 48))
    u = ease(k / (t1 - t0 - 0.3))
    zoom = 42 * (230 / 42) ** u
    cen = (lerp(108, SUBANG[0], u), lerp(10, SUBANG[1], u))
    arr, P = draw_map(arr, cen, zoom)
    a0 = clamp(k / 0.6)
    x, y = P(*SUBANG)
    for i in range(3):
        ph = ((k * 0.9 + i / 3) % 1); r = 10 + ph * 80
        d.ellipse([x - r, y - r, x + r, y + r], outline=rgba(RED, (1 - ph) * a0), width=4)
    d.ellipse([x - 11, y - 11, x + 11, y + 11], fill=rgba(RED, a0))
    b = clamp((k - 1.3) / 0.5)
    headline(d, "MALAYSIA", 420, 170, b, tracking=10)
    draw_text(d, (W / 2, 520), "SEBUAH TRAGEDI YANG RAMAI TAK TAHU", F("mono_b", 28), rgba(ORANGE, b), 4, "mm")
    c = clamp((k - 2.6) / 0.5)
    d.rounded_rectangle([x - 190, y + 50, x + 190, y + 150], radius=12, fill=(0, 0, 0, int(180 * c)), outline=rgba(RED, c), width=2)
    draw_text(d, (x, y + 84), "SUBANG", F("oswald_b", 40), rgba(INK, c), 3, "mm")
    draw_text(d, (x, y + 126), "SELANGOR", F("mono", 22), rgba(MUTED, c), 3, "mm")
    tag(d, "PETA ILUSTRASI", "ilu")
    return arr


def sc_jumbo(t, d, t0, t1):
    k = t - t0
    arr = bg_night(t, 2)
    # cloud streaks passing (speed feel)
    im = Image.new("RGBA", (W, H)); g = ImageDraw.Draw(im)
    rng = np.random.default_rng(3)
    for i in range(26):
        y = rng.uniform(250, 1350); L = rng.uniform(120, 420); sp = rng.uniform(500, 1100)
        x = (rng.uniform(0, W + 600) - k * sp) % (W + 600) - 300
        g.line([x, y, x + L, y], fill=(150, 170, 190, int(rng.uniform(25, 70))), width=int(rng.uniform(2, 6)))
    draw_plan(g, lerp(-250, W / 2, ease_out(k / 1.2)), 760 + 10 * math.sin(t * 1.3), 90, 9.5, "tiger")
    arr = composite(arr, im)
    a = clamp((k - 0.5) / 0.4)
    headline(d, "BOEING 747", 1110, 180, a, tracking=6)
    draw_text(d, (W / 2, 1215), "\"JUMBO JET\" · VERSI KARGO", F("mono_b", 30), rgba(ORANGE, a), 4, "mm")
    tag(d, "ILUSTRASI IKON", "ilu")
    return arr


def sc_approach(t, d, t0, t1):
    k = t - t0
    arr = runway_view(t, 2000 + k * 70, vis=900, cam_h=lerp(140, 100, ease(k / (t1 - t0))), horizon=760,
                      sky=(60, 70, 90), fog_col=(70, 78, 92), light_scale=1.6, darkness=0.15)
    arr = fog_over(arr, t, 0.35, k=0, speed=(18, 2), color=(80, 88, 100))
    arr = bloom(arr, 0.75, 0.9)
    a = clamp((k - 0.4) / 0.5)
    headline(d, "LAPANGAN TERBANG", 380, 110, a, tracking=6)
    headline(d, "SUBANG", 500, 190, a, ORANGE, tracking=10)
    draw_text(d, (W / 2, 610), "KUALA LUMPUR · WMSA", F("mono_b", 28), rgba(INK, a), 4, "mm")
    tag(d, "ILUSTRASI", "ilu")
    return arr


def sc_title(t, d, t0, t1):
    k = t - t0
    arr = bg_night(t, 1)
    arr = hills(arr, t, 1330, drift=10)
    im = Image.new("RGBA", (W, H)); g = ImageDraw.Draw(im)
    x = lerp(W + 150, -150, k / (t1 - t0 + 1.5))
    draw_plan(g, x, 1150, 270, 3.0, "tiger", 0.9)
    add = composite(arr, im)
    add_glow(add, x - 105, 1150, 14, (255, 230, 190), 0.9)
    a = clamp(k / 0.5)
    headline(d, "1989", 520, 300, a, tracking=14)
    b = clamp((k - 0.9) / 0.5)
    headline(d, "FLYING TIGER LINE", 760, 120, b, tracking=4)
    d.rectangle([150, 830, W - 150, 930], fill=rgba((150, 20, 20), 0.9 * b))
    headline(d, "FLIGHT 66", 882, 100, b, tracking=8)
    draw_text(d, (W / 2, 990), "AIR DISASTER CHRONICLES · EPISODE 01", F("mono_b", 26), rgba(ORANGE, b), 3, "mm")
    tag(d, "ILUSTRASI", "ilu")
    return add


def sc_card(t, d, t0, t1):
    k = t - t0
    arr = vgrad(H, (10, 20, 34), (18, 34, 54))
    arr = fog_over(arr, t, 0.25, k=1, color=(40, 60, 80))
    im = Image.new("RGBA", (W, H)); g = ImageDraw.Draw(im)
    draw_plan(g, lerp(W + 350, W / 2, ease_out(k / 1.0)), 470 + 6 * math.sin(t * 1.2), 90, 7.0, "tiger")
    arr = composite(arr, im)
    a = clamp((k - 0.3) / 0.5)
    headline(d, "FLIGHT 66", 790, 160, a, tracking=4)
    draw_text(d, (W / 2, 875), "FLYING TIGER LINE · AMERIKA SYARIKAT", F("mono_b", 28), rgba(MUTED, a), 4, "mm")
    rows = [(0.0, "TARIKH", "19 Februari 1989"),
            (wd("f1", 14) - t0, "PESAWAT", "Boeing 747-249F"),
            (wd("f1", 14) - t0 + 0.8, "JENIS", "Pesawat kargo (freighter)"),
            (wd("f1", 22) - t0, "REGISTRASI", "N807FT"),
            (wd("f1", 22) - t0 + 0.8, "DI DALAM PESAWAT", "4 anak kapal")]
    y = 930
    for (ts, kk, vv) in rows:
        b = clamp((k - max(ts, 0.8)) / 0.4)
        d.line([140, y + 72, W - 140, y + 72], fill=rgba((255, 255, 255), 0.15 * b), width=1)
        draw_text(d, (140, y + 30), kk, F("mono", 24), rgba(MUTED, b), 2, "lm")
        draw_text(d, (W - 140, y + 30), vv, F("inter_sb", 34), rgba(INK, b), 0, "rm")
        y += 78
    # hide the rows under subtitles area is fine: rows end ~1440 -> subtitles sit on top with box
    tag(d, "ILUSTRASI IKON", "ilu")
    return arr


def route_pt(pts, u):
    return lerp(pts[0][0], pts[1][0], u), lerp(pts[0][1], pts[1][1], u)


def sc_route(t, d, t0, t1):
    k = t - t0
    arr = vgrad(H, (10, 22, 36), (14, 30, 48))
    cen = (lerp(107.5, 106.0, ease(k / 6)), lerp(12.0, 10.5, ease(k / 6)))
    arr, P = draw_map(arr, cen, lerp(50, 56, ease(k / 6)), cy=900, hl="Malaysia")
    s, kl, hk = P(*SIN), P(*SUBANG), P(*HKG)
    a0 = clamp(k / 0.4)
    # leg 1 SIN -> KUL (solid, animated) ; leg 2 KUL -> HKG (dashed, planned)
    u1 = ease(clamp((k - 0.4) / 2.4))
    d.line([s, route_pt((s, kl), u1)], fill=rgba(ORANGE, a0), width=6)
    u2 = clamp((k - (wd("f1", 39) - t0)) / 1.8)
    n = 30
    for i in range(0, int(n * u2), 2):
        d.line([route_pt((kl, hk), i / n), route_pt((kl, hk), (i + 1) / n)], fill=rgba(INK, 0.8), width=4)
    def city(p, name, sub, col, a, dx=0, anchor="lm"):
        d.ellipse([p[0] - 12, p[1] - 12, p[0] + 12, p[1] + 12], fill=rgba(col, a))
        draw_text(d, (p[0] + 30 + dx, p[1] - 14), name, F("oswald_b", 40), rgba(col, a), 2, anchor)
        draw_text(d, (p[0] + 30 + dx, p[1] + 26), sub, F("mono", 22), rgba(MUTED, a), 2, anchor)
    city(s, "SINGAPURA", "BERLEPAS", INK, a0)
    city(kl, "KUALA LUMPUR", "SUBANG", ORANGE, clamp((k - 2.2) / 0.4))
    city(hk, "HONG KONG", "DESTINASI SETERUSNYA", INK, u2, dx=-60, anchor="rm")
    im = Image.new("RGBA", (W, H)); g = ImageDraw.Draw(im)
    px, py = route_pt((s, kl), u1)
    hd = math.degrees(math.atan2(kl[0] - s[0], -(kl[1] - s[1])))
    draw_plan(g, px, py, hd, 1.6, "tiger")
    arr = composite(arr, im)
    draw_text(d, (W / 2, 330), "LALUAN FLIGHT 66 · 19 FEB 1989", F("mono_b", 30), rgba(MUTED, a0), 5, "mm")
    tag(d, "PETA ILUSTRASI", "ilu")
    return arr


# ------------------------------------------------------------------ approach diagram (plan view)
RWY_HDG = 330.0


def sc_plan(t, d, t0, t1):
    k = t - t0
    arr = vgrad(H, (14, 26, 40), (12, 22, 34))
    im = Image.new("RGBA", (W, H)); g = ImageDraw.Draw(im)
    g.rectangle([0, 0, W, H], fill=(22, 36, 40, 255))
    sc = lerp(0.055, 0.065, ease(k / 4))  # px per metre
    th = math.radians(RWY_HDG)
    fwd = (math.sin(th), -math.cos(th))  # landing direction on screen
    thr = (W / 2 - 40, 560)  # threshold 33 position
    def Pm(along, lat):  # along: metres from threshold along landing dir (negative = on approach), lat: right
        rx, ry = -fwd[1], fwd[0]
        return (thr[0] + (fwd[0] * along + rx * lat) * sc, thr[1] + (fwd[1] * along + ry * lat) * sc)
    # hills (contours) south-east on the approach
    rng = np.random.default_rng(5)
    for (al, la, r) in [(-9500, 1500, 2200), (-12500, -1800, 2600), (-6500, -2600, 1500), (-15000, 2500, 2400)]:
        cx, cy = Pm(al, la)
        for j in range(4):
            rr = r * sc * (1 - j * 0.22)
            g.ellipse([cx - rr * 1.3, cy - rr, cx + rr * 1.3, cy + rr], fill=(34 + j * 10, 52 + j * 8, 44 + j * 6, 255), outline=(70, 96, 80, 255))
    hx, hy = 150, 1010
    g.text((hx + 140, hy + 40), "KAWASAN BERBUKIT", font=F("mono_b", 24), fill=(170, 200, 170, 255), anchor="mm")
    g.text((hx + 140, hy + 72), "PUCHONG", font=F("oswald_b", 34), fill=(200, 230, 200, 255), anchor="mm")
    # runway
    rl = 3780
    c = [Pm(0, -30), Pm(rl, -30), Pm(rl, 30), Pm(0, 30)]
    g.polygon(c, fill=(58, 62, 66, 255))
    for a_ in range(100, rl - 100, 160):
        g.line([Pm(a_, 0), Pm(a_ + 90, 0)], fill=(220, 220, 220, 220), width=2)
    g.text(Pm(-260, 0), "33", font=F("oswald_b", 34), fill=(240, 240, 240, 255), anchor="mm")
    g.text(Pm(rl + 260, 0), "15", font=F("oswald_b", 34), fill=(240, 240, 240, 255), anchor="mm")
    # extended centreline (approach path)
    for a_ in range(-16000, -200, 700):
        g.line([Pm(a_, 0), Pm(a_ + 350, 0)], fill=(*ORANGE, 160), width=3)
    # NDB marker
    nx, ny = Pm(-5500, 0)
    g.ellipse([nx - 12, ny - 12, nx + 12, ny + 12], outline=(240, 200, 60, 255), width=3)
    g.text((nx - 30, ny), "NDB", font=F("mono_b", 22), fill=(240, 200, 60, 255), anchor="rm")
    arr = to_f(im.convert("RGB"))
    # aircraft icon moving along approach
    u = ease(clamp(k / (t1 - t0)))
    ax, ay = Pm(lerp(-17500, -12500, u), lerp(900, 0, ease(clamp(k / 1.5))))
    ic = Image.new("RGBA", (W, H)); gi = ImageDraw.Draw(ic)
    draw_plan(gi, ax, ay, RWY_HDG, 2.2, "tiger")
    gi.rounded_rectangle([ax - 300, ay - 24, ax - 80, ay + 24], radius=8, fill=(0, 0, 0, 190), outline=(*ORANGE, 255), width=2)
    gi.text((ax - 190, ay), "TIGER 66", font=F("mono_b", 24), fill=(*ORANGE, 255), anchor="mm")
    arr = composite(arr, ic)
    arr = fog_over(arr, t, 0.25, k=0, speed=(20, 4), color=(110, 118, 126))
    a = clamp((k - 0.3) / 0.4)
    headline(d, "RUNWAY 33", 330, 140, a, tracking=6)
    draw_text(d, (W / 2, 420), "PENDEKATAN NDB · AWAL PAGI", F("mono_b", 28), rgba(ORANGE, a), 4, "mm")
    tx, ty = Pm(rl / 2, 0)
    draw_text(d, (tx + 120, ty), "SUBANG", F("oswald_b", 36), rgba(INK, a), 2, "lm")
    tag(d, "ILUSTRASI · SUSUN ATUR DIPERMUDAH", "ilu")
    return arr


# ------------------------------------------------------------------ radio transcript
def sc_radio(t, d, t0, t1):
    k = t - t0
    arr = vgrad(H, (8, 12, 18), (16, 22, 30))
    ws = Image.new("RGBA", (W, H)); wdr = ImageDraw.Draw(ws)
    pts = []; rng = np.random.default_rng(int(t * 24)); y0 = 1290
    for i in range(0, W, 6):
        amp = 30 + 40 * abs(math.sin(i * 0.02 + t * 5)) * (0.6 + 0.4 * rng.random())
        pts.append((i, y0 + amp * math.sin(i * 0.3 + t * 30)))
    wdr.line(pts, fill=(120, 200, 255, 90), width=2)
    arr = composite(arr, ws)
    draw_text(d, (80, 420), "06:3x · RADIO · PENDEKATAN SUBANG", F("mono_b", 28), rgba(MUTED, clamp(k / 0.4)), 3, "lm")
    d.line([80, 455, W - 80, 455], fill=rgba((255, 255, 255), 0.2), width=1)
    items = [(0.2, "MENARA KAWALAN", "\"Tiger 66, descend two four zero zero...\"", "\"Tiger 66, turun ke 2,400 kaki...\"", (240, 200, 60)),
             (1.9, "TIGER 66 (BACAAN SEMULA)", "\"Okay, four zero zero.\"", "\"Okay, 400.\"", (230, 230, 230)),
             (3.2, "MASALAHNYA", "\"two\" kedengaran seperti \"to\"", None, RED)]
    y = 520
    for (ts, who, txt, tr, col) in items:
        a = clamp((k - ts) / 0.35)
        if a <= 0:
            continue
        draw_text(d, (80, y + 20), who, F("mono_b", 26), rgba(col, a), 3, "lm")
        y += 56
        fnt = F("oswald", 58)
        for ln in wrap(txt, fnt, W - 180):
            d.text((90, y + 26), ln, font=fnt, fill=rgba((255, 255, 255), a), anchor="lm"); y += 64
        if tr:
            for ln in wrap(tr, F("inter_m", 32), W - 180):
                d.text((90, y + 18), ln, font=F("inter_m", 32), fill=rgba(MUTED, a), anchor="lm"); y += 44
        y += 34
    tag(d, "PETIKAN KOMUNIKASI RADIO", "tx")
    return arr


def sc_twoto(t, d, t0, t1):
    k = t - t0
    arr = vgrad(H, (8, 12, 18), (16, 22, 30))
    arr = fog_over(arr, t, 0.2, k=1, color=(40, 50, 62))
    split = wd("a2", 9) - t0
    a = clamp(k / 0.4)
    draw_text(d, (W / 2, 330), "ARAHAN MENARA KAWALAN", F("mono_b", 30), rgba(ORANGE, a), 5, "mm")
    f = F("oswald_b", 74)
    draw_text(d, (W / 2, 440), "DESCEND TWO FOUR ZERO ZERO", f, rgba(INK, a), 1, "mm")
    n = int(2400 * ease_out(clamp(k / 1.2)))
    col = INK if k < split else (110, 112, 118)
    headline(d, f"{n:,} FT", 620, 230, a, col, tracking=4)
    if k >= split:
        b = clamp((k - split) / 0.35)
        w = F("bebas", 230).getlength("2,400 FT") + 30
        d.line([W / 2 - w / 2, 620, W / 2 - w / 2 + w * ease(b), 620], fill=rgba(RED, b), width=14)
        draw_text(d, (W / 2, 820), "YANG DIFAHAMI", F("mono_b", 30), rgba(RED, b), 5, "mm")
        # "TWO" -> "TO"
        t1_ = "DESCEND "; t2 = "TO"; t3 = " FOUR ZERO ZERO"
        tw = f.getlength(t1_ + t2 + t3); x = W / 2 - tw / 2
        d.text((x, 930), t1_, font=f, fill=rgba(INK, b), anchor="lm"); x += f.getlength(t1_)
        d.text((x, 930), t2, font=f, fill=rgba(RED, b), anchor="lm")
        d.line([x, 975, x + f.getlength(t2), 975], fill=rgba(RED, b), width=5); x += f.getlength(t2)
        d.text((x, 930), t3, font=f, fill=rgba(INK, b), anchor="lm")
        c = clamp((k - split - 0.6) / 0.4)
        headline(d, "400 FT", 1110, 230, c, RED, tracking=4)
    tag(d, "ILUSTRASI · ARAHAN RADIO", "ilu")
    return arr


# ------------------------------------------------------------------ vertical profile: descent into terrain
def sc_profile(t, d, t0, t1):
    k = t - t0
    arr = vgrad(H, (16, 24, 38), (34, 44, 58))
    arr = fog_over(arr, t, 0.35, k=2, speed=(20, 1), color=(70, 80, 92))
    x0, x1 = 80, W - 80
    yft = lambda ft: 1180 - ft * 0.27  # 2400 ft -> 532
    hill_x = 860
    def terrain(x):
        h = 60 + 15 * math.sin(x * 0.02)
        h += 470 * math.exp(-((x - hill_x) / 95) ** 2)
        return h
    im = Image.new("RGBA", (W, H)); g = ImageDraw.Draw(im)
    pts = [(0, H)] + [(x, yft(terrain(x))) for x in range(0, W + 10, 10)] + [(W, H)]
    g.polygon(pts, fill=(18, 26, 30, 255), outline=(80, 100, 90, 255))
    for ft, lab, col in [(2400, "2,400 FT · ARAHAN SEBENAR", INK), (400, "400 FT · YANG DISANGKA", RED)]:
        y = yft(ft)
        for x in range(x0, x1, 36):
            g.line([x, y, x + 20, y], fill=(*col, 200), width=3)
        g.text((x0, y - 26), lab, font=F("mono_b", 26), fill=(*col, 255), anchor="lm")
    g.text((hill_x - 30, yft(terrain(hill_x)) - 110), "BUKIT · PUCHONG", font=F("oswald_b", 36), fill=(200, 230, 200, 255), anchor="mm")
    # aircraft path: from left at 2400, descend towards 400, meets hill
    imp = IMPACT - t0
    u = clamp(k / imp)
    xa = lerp(60, hill_x - 70, u)
    ft = 2450 - 2100 * ease(clamp(u * 1.05))
    ya = yft(ft)
    # trail
    tr = []
    for i in range(30):
        uu = u * i / 29
        tr.append((lerp(60, hill_x - 70, uu), yft(2450 - 2100 * ease(clamp(uu * 1.05)))))
    if len(tr) > 1:
        g.line(tr, fill=(*ORANGE, 200), width=4)
    if k < imp:
        ang = -math.degrees(math.atan2(yft(2450 - 2100 * ease(clamp((u + 0.02) * 1.05))) - ya, 10)) if u < 1 else 0
        draw_plan(g, xa, ya, 90 + 12, 1.4, "tiger")
    arr = composite(arr, im)
    # altitude readout
    a = clamp(k / 0.4)
    if k < imp:
        draw_text(d, (W / 2, 330), "PESAWAT TERUS MENURUN", F("oswald_b", 52), rgba(INK, a), 2, "mm")
        draw_text(d, (W / 2, 410), f"ALTITUD ~{int(ft / 10) * 10:,} FT", F("mono_b", 34), rgba(ORANGE, a), 3, "mm")
    else:
        e = k - imp
        fl = clamp(1 - e / 0.5)
        if fl > 0:
            add_glow(arr, hill_x - 60, yft(terrain(hill_x - 60)), 120, (255, 200, 140), fl * 2.5)
        arr = arr * (1 - 0.85 * clamp((e - 0.3) / 1.0))
        b = clamp((e - 0.6) / 0.5)
        draw_text(d, (W / 2, H / 2 - 120), "06:36 PAGI", F("mono", 44), rgba((170, 170, 170), b), 8, "mm")
    tag(d, "ILUSTRASI · PROFIL DIPERMUDAH", "ilu")
    return arr


# ------------------------------------------------------------------ archival + toll
CROPS = {"news_ms.png": (0, 30, 1079, 915), "news_en.png": (0, 10, 1079, 1000), "ground.png": (0, 40, 1079, 555)}


def sc_crash(t, d, t0, t1):
    k = t - t0
    arr = photo_plate("crash.jpg", k, t1 - t0, bw=True, dark=0.25, y_center=760, z0=1.0, z1=1.12)
    a = clamp((k - 0.2) / 0.5)
    headline(d, "AWAL PAGI", 350, 120, a, tracking=6)
    draw_text(d, (W / 2, 440), "19 FEBRUARI 1989 · 06:36 PAGI", F("mono_b", 30), rgba(ORANGE, a), 3, "mm")
    tag(d, "FOTO ARKIB · LOKASI NAHAS", "arkib")
    return arr


def sc_toll(t, d, t0, t1):
    k = t - t0
    arr = photo_plate("news_ms.png", k, t1 - t0, crop=CROPS["news_ms.png"], bw=True, dark=0.72, y_center=780, z0=1.0, z1=1.1)
    a = clamp(k / 0.5)
    n = int(4 * ease_out(clamp(k / 0.8))) if k < 0.8 else 4
    d.rounded_rectangle([140, 420, W - 140, 1180], radius=24, fill=(0, 0, 0, int(150 * a)))
    headline(d, str(max(1, n)), 640, 380, a)
    draw_text(d, (W / 2, 860), "NYAWA TERKORBAN", F("mono_b", 44), rgba(RED, a), 10, "mm")
    b = clamp((k - 1.0) / 0.5)
    for i in range(4):
        x = W / 2 + (i - 1.5) * 120; y = 1000
        d.ellipse([x - 22, y - 60, x + 22, y - 16], fill=rgba(INK, b))
        d.rounded_rectangle([x - 38, y - 8, x + 38, y + 70], radius=30, fill=rgba(INK, b))
    draw_text(d, (W / 2, 1130), "KESEMUA 4 ANAK KAPAL", F("mono_b", 30), rgba(MUTED, b), 4, "mm")
    tag(d, "FOTO ARKIB · AKHBAR 1989", "arkib")
    return arr


def sc_lesson(t, d, t0, t1):
    k = t - t0
    arr = vgrad(H, (30, 34, 46), (70, 64, 66))
    arr = hills(arr, t, 1350, col=(16, 20, 28), drift=4)
    arr = fog_over(arr, t, 0.4, k=0, speed=(10, 1), color=(120, 112, 112))
    add_glow(arr, W / 2, 1180, 260, (255, 170, 110), 0.35)
    a = clamp((k - 0.3) / 0.6)
    draw_text(d, (W / 2, 420), "DALAM PENERBANGAN…", F("mono_b", 34), rgba(MUTED, a), 6, "mm")
    b = clamp((t - wd("c1", 8)) / 0.5)
    c = clamp((t - wd("c1", 11)) / 0.5)
    e = clamp((t - wd("c1", 13)) / 0.5)
    headline(d, "SETIAP ARAHAN.", 580, 140, b, tracking=3)
    headline(d, "SETIAP PERKATAAN.", 720, 140, c, ORANGE, tracking=3)
    draw_text(d, (W / 2, 840), "MEMBAWA MAKNA.", F("oswald_l", 60), rgba(INK, e), 4, "mm")
    f2 = clamp((k - 0.8) / 0.6) * 0.8
    draw_text(d, (W / 2, 1000), "\"TWO\"  BUKAN  \"TO\"", F("mono_b", 40), rgba(MUTED, f2), 6, "mm")
    tag(d, "MENGENANG FLIGHT 66", "ilu")
    return arr


LOGO = Image.open(os.path.join(A, "brand", "logo.png")).convert("RGBA")


def logo_img(size):
    im = LOGO.resize((size, int(size * LOGO.height / LOGO.width)), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    lum = a[..., :3].max(axis=2)
    a[..., 3] = np.clip((lum - 12) / 30, 0, 1) * 255
    return Image.fromarray(a.astype(np.uint8))


def sc_end(t, d, t0, t1):
    arr = vgrad(H, (8, 14, 24), (20, 32, 48))
    arr = fog_over(arr, t, 0.35, k=1, color=(40, 56, 74))
    k = t - t0
    lg = logo_img(int(600 + 40 * ease_out(k / 2.5)))
    a = clamp(k / 0.8) * clamp((t1 - t) / 0.6)
    lg.putalpha(lg.split()[3].point(lambda v: int(v * a)))
    ov = Image.new("RGBA", (W, H))
    ov.alpha_composite(lg, (W // 2 - lg.width // 2, 680 - lg.height // 2))
    od = ImageDraw.Draw(ov)
    a2 = clamp((t - wd("c2", 2) + 0.3) / 0.6) * clamp((t1 - t) / 0.6)
    headline(od, "NABIL AVIATION", 1130, 130, clamp((k - 0.4) / 0.6) * clamp((t1 - t) / 0.6), tracking=8)
    od.line([W / 2 - 200, 1210, W / 2 + 200, 1210], fill=rgba(ORANGE, a2), width=3)
    draw_text(od, (W / 2, 1275), "Learning from", F("oswald_l", 56), rgba(INK, a2), 2, "mm")
    draw_text(od, (W / 2, 1350), "Aviation History.", F("oswald_l", 56), rgba(INK, a2), 2, "mm")
    draw_text(od, (W / 2, 1470), "AIR DISASTER CHRONICLES · EP 01", F("mono", 28), rgba(ORANGE, a2), 2, "mm")
    d._ov = ov
    return arr


# ------------------------------------------------------------------ edit decision list
def build_edl():
    e = []
    def add(t0, t1, fn):
        e.append((t0, t1, fn))
    add(0, wd("h1", 9) - 0.2, sc_map_hook)
    add(wd("h1", 9) - 0.2, wd("h1", 18) - 0.2, sc_jumbo)
    add(wd("h1", 18) - 0.2, st("h2") - 0.2, sc_approach)
    add(st("h2") - 0.2, st("f1") - 0.3, sc_title)
    add(st("f1") - 0.3, wd("f1", 30) - 0.2, sc_card)
    add(wd("f1", 30) - 0.2, st("a1") - 0.3, sc_route)
    add(st("a1") - 0.3, wd("a1", 9) - 0.2, sc_plan)
    add(wd("a1", 9) - 0.2, st("a2") - 0.2, sc_radio)
    add(st("a2") - 0.2, st("a3") - 0.2, sc_twoto)
    add(st("a3") - 0.2, st("m1") - 0.3, sc_profile)
    add(st("m1") - 0.3, wd("m1", 5) - 0.2, sc_crash)
    add(wd("m1", 5) - 0.2, st("c1") - 0.3, sc_toll)
    add(st("c1") - 0.3, st("c2") - 0.3, sc_lesson)
    add(st("c2") - 0.3, END, sc_end)
    return e


EDL = None


def render_frame(i):
    global EDL
    if EDL is None:
        EDL = build_edl()
    t = i / FPS
    path = os.path.join(OUT, f"{i:05d}.jpg")
    if os.path.exists(path):
        return
    for (t0, t1, fn) in EDL:
        if t0 <= t < t1:
            break
    ov = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(ov)
    arr = fn(t, d, t0, t1)
    extra = getattr(d, "_ov", None)
    if extra is not None:
        extra.alpha_composite(ov); ov = extra; d = ImageDraw.Draw(ov)
    dipa = 0.0
    for (a0, a1, _) in EDL:
        if abs(t - a0) < 0.12 and a0 > 0:
            dipa = max(dipa, 1 - abs(t - a0) / 0.12)
    if dipa:
        arr = arr * (1 - 0.6 * dipa)
    if fn is not sc_end:
        brand(d)
    subtitle(d, t)
    fade_in = clamp(t / 0.3)
    im = finish(arr * fade_in, t, ov)
    im.save(path, quality=92)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    args = sys.argv[1:]
    if args and args[0] == "--test":
        OUT = os.path.join(ROOT, "build", "test"); os.makedirs(OUT, exist_ok=True)
        for tt in args[1].split(","):
            i = int(float(tt) * FPS)
            p = os.path.join(OUT, f"{i:05d}.jpg")
            if os.path.exists(p): os.remove(p)
            render_frame(i)
            print(p)
    else:
        from multiprocessing import Pool
        n = int(END * FPS)
        with Pool(4) as p:
            for j, _ in enumerate(p.imap_unordered(render_frame, range(n), chunksize=8)):
                if j % 400 == 0:
                    print(j, "/", n, flush=True)
        print("done", n)
