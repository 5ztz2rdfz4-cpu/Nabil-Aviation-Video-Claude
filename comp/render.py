"""Render all frames of the Tenerife 1977 documentary (flat 2D style).
usage: python3 comp/render.py [--test t1,t2,...] [--workers N]
"""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from gfx import *

TL = json.load(open(os.path.join(ROOT, "build", "vo", "timeline.json")))
LINES = TL["lines"]
LN = {l["key"]: l for l in LINES}
END = LN["l8"]["end"] + 5.0
OUT = os.path.join(ROOT, "build", "frames")
BG = (11, 20, 32)
NAVY = (16, 30, 48)


def st(k):
    return LN[k]["start"]


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
    for l in LINES:
        if l["start"] - 0.05 <= t <= l["end"] + 0.25:
            txt = l["text"]
            f = F("inter_sb", 44)
            lines = wrap(txt, f, 900)
            # split long subtitles into pages of 2 lines, timed by length
            pages = [lines[i:i + 2] for i in range(0, len(lines), 2)]
            tot = sum(len(" ".join(p)) for p in pages)
            acc = 0; dur = l["end"] - l["start"]
            page = pages[-1]
            for p in pages:
                n = len(" ".join(p))
                if t < l["start"] + dur * (acc + n) / tot:
                    page = p; break
                acc += n
            y0 = 1440 - 30 * (len(page) - 1)
            for i, s in enumerate(page):
                w = f.getlength(s)
                y = y0 + i * 60
                d.rounded_rectangle([W / 2 - w / 2 - 20, y - 32, W / 2 + w / 2 + 20, y + 30], radius=10, fill=(0, 0, 0, 150))
                d.text((W / 2, y), s, font=f, fill=(255, 255, 255, 255), anchor="mm")
            return


def headline(d, text, y, size=120, a=1.0, col=(255, 255, 255), font="bebas", tracking=2):
    draw_text(d, (W / 2, y), text, F(font, size), rgba(col, a), tracking, "mm")


def finish(arr, t, overlay, grain=0.035, vign=0.55):
    # grade: slight desat + teal shadows / warm highlights
    lum = arr.mean(axis=2, keepdims=True)
    arr = arr * 0.85 + lum * 0.15
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


# ------------------------------------------------------------------ scene: logo
LOGO = Image.open(os.path.join(A, "brand", "logo.png")).convert("RGBA")


def logo_img(size):
    im = LOGO.resize((size, int(size * LOGO.height / LOGO.width)), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    lum = a[..., :3].max(axis=2)
    alpha = np.clip((lum - 12) / 30, 0, 1) * 255  # remove black background
    a[..., 3] = alpha
    return Image.fromarray(a.astype(np.uint8))


def sc_logo(t, d, t0, t1, end_card=False):
    arr = vgrad(H, (8, 14, 24), (20, 32, 48))
    arr = fog_over(arr, t, 0.35, k=1, color=(40, 56, 74))
    k = t - t0
    s = 640 if end_card else int(560 + 60 * ease_out(k / 2.5))
    lg = logo_img(s)
    a = clamp(k / 0.8) * clamp((t1 - t) / 0.5)
    lg.putalpha(lg.split()[3].point(lambda v: int(v * a)))
    cy = 700 if end_card else 860
    ov = Image.new("RGBA", (W, H))
    ov.alpha_composite(lg, (W // 2 - lg.width // 2, cy - lg.height // 2))
    od = ImageDraw.Draw(ov)
    if end_card:
        a2 = clamp((k - 1.0) / 0.8) * clamp((t1 - t) / 0.5)
        headline(od, "NABIL AVIATION", 1150, 130, a2, tracking=8)
        od.line([W / 2 - 200, 1230, W / 2 + 200, 1230], fill=rgba(ORANGE, a2), width=3)
        draw_text(od, (W / 2, 1290), "Exploring Aviation History,", F("oswald_l", 52), rgba(INK, a2), 2, "mm")
        draw_text(od, (W / 2, 1360), "One Story at a Time.", F("oswald_l", 52), rgba(INK, a2), 2, "mm")
        draw_text(od, (W / 2, 1480), "@nabil.aviation", F("mono", 34), rgba(ORANGE, a2), 2, "mm")
    else:
        a2 = clamp((k - 0.6) / 0.6) * clamp((t1 - t) / 0.5)
        draw_text(od, (W / 2, 1230), "PRESENTS", F("mono", 30), rgba(MUTED, a2), 12, "mm")
    d._ov = ov
    return arr


# ------------------------------------------------------------------ scene: runway perspective
def sc_runway(t, d, t0, t1, mode):
    k = t - t0
    if mode == "hook":
        arr = runway_view(t, 40 + k * 6, vis=330, oncoming=dict(z=900 - k * 10, lights=1, sil=0.6))
        arr = fog_over(arr, t, 0.55, k=0, speed=(18, 2))
    elif mode == "rush":
        arr = runway_view(t, k * k * 9, vis=260, shake=0.6, oncoming=dict(z=700, lights=0.7 * clamp(k / 3), sil=0.3),
                          darkness=0.45 * ease((t - (t1 - 2.5)) / 2.5))
        arr = fog_over(arr, t, 0.6, k=2, speed=(40, 4))
    elif mode == "vis":
        arr = runway_view(t, 300 + k * 4, vis=lerp(420, 150, ease(k / (t1 - t0))))
        arr = fog_over(arr, t, 0.7, k=0, speed=(30, 3))
    elif mode == "cockpit":
        arr = runway_view(t, 3, vis=240, cam_h=9, light_scale=1.2)
        arr = fog_over(arr, t, 0.65, k=1, speed=(15, 2))
    elif mode == "accel":
        tr = 20 * k + 9 * k * k
        arr = runway_view(t, tr, vis=240, shake=1.2 * clamp(k / 3), light_scale=1.3)
        arr = fog_over(arr, t, 0.6, k=2, speed=(60 + 30 * k, 4))
    elif mode == "oncoming":
        z = lerp(1100, 170, ease_in(clamp(k / (t1 - t0)) ** 0.7))
        arr = runway_view(t, 2 * k, vis=230, oncoming=dict(z=z, lights=1.0, sil=1.0), light_scale=0.9)
        arr = fog_over(arr, t, 0.55, k=1, speed=(20, 2))
    elif mode == "crash":
        z = max(25, 170 - k * 95)
        arr = runway_view(t, 0, vis=230, oncoming=dict(z=z, lights=1.4, sil=1.0), shake=2 * clamp(k / 1.5))
        arr = fog_over(arr, t, 0.5, k=1, speed=(20, 2))
        w = clamp((k - 1.2) / 0.35)
        arr = arr * (1 - w) + w * 0.92
        arr = arr * (1 - clamp((k - 1.6) / 0.9))
    elif mode == "memorial":
        arr = runway_view(t, k * 2.5, vis=600, sky=(150, 140, 130), fog_col=(170, 160, 150), light_scale=0.8)
        arr = fog_over(arr, t, 0.35, k=0, speed=(10, 1), color=(175, 165, 155))
        arr *= 0.75
    return bloom(arr, 0.75, 0.9)


def cockpit_frame(od, kind="klm"):
    # windscreen pillars and glareshield silhouette
    c = (8, 10, 13, 255)
    od.polygon([(0, 0), (W, 0), (W, 120), (0, 260)], fill=c)
    od.polygon([(0, 0), (150, 0), (90, 1250), (0, 1250)], fill=c)
    od.polygon([(W, 0), (W - 150, 0), (W - 90, 1250), (W, 1250)], fill=c)
    od.polygon([(W / 2 - 18, 120), (W / 2 + 18, 120), (W / 2 + 26, 1150), (W / 2 - 26, 1150)], fill=c)
    od.rounded_rectangle([-40, 1100, W + 40, H + 40], radius=80, fill=(14, 16, 20, 255))
    for i in range(6):  # instrument glows
        x = 150 + i * 150
        od.ellipse([x - 38, 1180, x + 38, 1256], outline=(60, 70, 80, 255), width=4)
        od.line([x, 1218, x + 26 * math.cos(i), 1218 - 26 * math.sin(i + 1)], fill=(200, 200, 190, 220), width=3)


# ------------------------------------------------------------------ scene: title
def sc_title(t, d, t0, t1):
    arr = photo_plate("IMG_9812.jpg", t - t0, t1 - t0, bw=True, z0=1.15, z1=1.3, dark=0.55)
    arr = fog_over(arr, t, 0.5, k=1, color=(60, 66, 74))
    k = t - t0
    a = clamp(k / 0.6)
    headline(d, "THE", 560, 90, a, tracking=20)
    headline(d, "TENERIFE", 690, 230, clamp((k - 0.2) / 0.6), tracking=6)
    d.rectangle([90, 800, W - 90, 900], fill=rgba((150, 20, 20), 0.9 * clamp((k - 0.5) / 0.5)))
    headline(d, "AIRPORT DISASTER", 852, 100, clamp((k - 0.5) / 0.5), tracking=4)
    headline(d, "1 9 7 7", 975, 80, clamp((k - 0.9) / 0.5), tracking=10)
    a2 = clamp((k - 1.6) / 0.6)
    draw_text(d, (W / 2, 1100), "KLM 4805   ×   PAN AM 1736", F("oswald", 46), rgba(INK, a2), 3, "mm")
    draw_text(d, (W / 2, 1170), "27 MAC 1977 · LOS RODEOS, TENERIFE", F("mono", 32), rgba(ORANGE, a2), 2, "mm")
    tag(d, "FOTO ARKIB · 1977", "arkib")
    return arr


# ------------------------------------------------------------------ scene: map
MAP = json.load(open(os.path.join(A, "canary_map.json")))
GANDO = (-15.3866, 27.9319)
TFN = (-16.3415, 28.4827)


def sc_map(t, d, t0, t1):
    k = t - t0
    arr = vgrad(H, (10, 22, 36), (14, 30, 48))
    zoom = lerp(170, 300, ease(k / 4))
    cen = (lerp(-15.6, -15.85, ease(k / 6)), lerp(28.3, 28.2, ease(k / 6)))
    cl = math.cos(math.radians(28))
    def P(lon, lat):
        return (W / 2 + (lon - cen[0]) * cl * zoom, 800 - (lat - cen[1]) * zoom)
    im = Image.new("RGBA", (W, H)); md = ImageDraw.Draw(im)
    for lon in range(-20, -8):
        md.line([P(lon, 25), P(lon, 31)], fill=(40, 70, 100, 120), width=1)
    for lat in range(25, 32):
        md.line([P(-20, lat), P(-8, lat)], fill=(40, 70, 100, 120), width=1)
    for poly in MAP["africa"] + MAP["islands"]:
        if len(poly) > 2:
            md.polygon([P(*p) for p in poly], fill=(58, 72, 80, 255), outline=(120, 140, 150, 255))
    arr = arr * (1 - to_f(im.split()[3].convert("RGB"))) + to_f(im.convert("RGB")) * to_f(im.split()[3].convert("RGB"))
    def lab(lonlat, txt, dy=-50, col=INK, size=34, a=1):
        x, y = P(*lonlat)
        draw_text(d, (x, y + dy), txt, F("oswald", size), rgba(col, a), 3, "mm")
    a0 = clamp(k / 0.6)
    lab((-15.6, 27.62), "GRAN CANARIA", 0, MUTED, 30, a0)
    lab((-16.6, 28.05), "TENERIFE", 0, MUTED, 30, a0)
    lab((-13.6, 27.0), "AFRIKA", 0, (110, 120, 130), 30, a0)
    draw_text(d, (W / 2, 330), "KEPULAUAN CANARY · SEPANYOL", F("mono_b", 30), rgba(MUTED, a0), 6, "mm")
    # explosion pulse at Gran Canaria
    gx, gy = P(*GANDO)
    for i in range(3):
        ph = ((k * 0.9 + i / 3) % 1)
        r = 10 + ph * 90
        d.ellipse([gx - r, gy - r, gx + r, gy + r], outline=rgba(RED, (1 - ph) * a0), width=4)
    d.ellipse([gx - 12, gy - 12, gx + 12, gy + 12], fill=rgba(RED, a0))
    if k < (st("w2") - t0):
        b = clamp((k - 0.8) / 0.5)
        d.rounded_rectangle([gx - 250, gy + 60, gx + 150, gy + 190], radius=12, fill=(0, 0, 0, int(180 * b)), outline=rgba(RED, b), width=2)
        draw_text(d, (gx - 50, gy + 100), "LETUPAN BOM", F("oswald_b", 42), rgba(RED, b), 3, "mm")
        draw_text(d, (gx - 50, gy + 155), "LAPANGAN TERBANG GRAN CANARIA", F("mono", 20), rgba(INK, b), 1, "mm")
    else:
        k2 = k - (st("w2") - t0)
        tx, ty = P(*TFN)
        b = clamp(k2 / 0.5)
        # diversion arrows (curved dashed)
        for j, off in enumerate((-40, 40)):
            pts = []
            for i in range(41):
                u = i / 40
                x = lerp(gx, tx, u) + off * math.sin(u * math.pi)
                y = lerp(gy, ty, u) - 120 * math.sin(u * math.pi)
                pts.append((x, y))
            n = int(40 * ease(k2 / 2.0))
            for i in range(0, n, 2):
                d.line([pts[i], pts[i + 1]], fill=rgba(ORANGE, b), width=5)
        d.ellipse([tx - 13, ty - 13, tx + 13, ty + 13], fill=rgba(ORANGE, b))
        c = clamp((k2 - 1.5) / 0.5)
        d.rounded_rectangle([tx - 220, ty - 170, tx + 200, ty - 50], radius=12, fill=(0, 0, 0, int(180 * c)), outline=rgba(ORANGE, c), width=2)
        draw_text(d, (tx - 10, ty - 130), "LOS RODEOS (TFN)", F("oswald_b", 40), rgba(ORANGE, c), 2, "mm")
        draw_text(d, (tx - 10, ty - 80), "PENERBANGAN DIALIHKAN KE SINI", F("mono", 20), rgba(INK, c), 1, "mm")
    tag(d, "PETA ILUSTRASI", "ilu")
    return arr


# ------------------------------------------------------------------ scene: aircraft cards
def sc_cards(t, d, t0, t1):
    arr = vgrad(H, (10, 20, 34), (18, 34, 54))
    arr = fog_over(arr, t, 0.25, k=1, color=(40, 60, 80))
    k = t - t0
    split = st("w3") + (LN["w3"]["end"] - st("w3")) * 0.48 - t0
    if t >= st("w4"):
        # both side by side: "Boeing 747"
        k4 = t - st("w4")
        im = Image.new("RGBA", (W, H)); pd = ImageDraw.Draw(im)
        draw_plan(pd, 300, 760, -20 + 4 * math.sin(t * 0.6), 6.0, "klm", clamp(k4 / 0.5))
        draw_plan(pd, 780, 760, 20 - 4 * math.sin(t * 0.6), 6.0, "panam", clamp(k4 / 0.5))
        d._under = im
        a = clamp((k4 - 0.3) / 0.5)
        headline(d, "BOEING 747", 420, 150, a, tracking=6)
        draw_text(d, (300, 1080), "747-206B", F("oswald", 44), rgba(KLM_BLUE, a), 2, "mm")
        draw_text(d, (780, 1080), "747-121", F("oswald", 44), rgba(INK, a), 2, "mm")
        draw_text(d, (W / 2, 1190), '"JUMBO JET" · PESAWAT PENUMPANG TERBESAR', F("mono", 26), rgba(MUTED, a), 2, "mm")
        tag(d, "ILUSTRASI IKON", "ilu")
        return arr
    klm = k < split
    kk = k if klm else k - split
    im = Image.new("RGBA", (W, H)); pd = ImageDraw.Draw(im)
    x = lerp(W + 300, W / 2, ease_out(kk / 0.9))
    draw_plan(pd, x, 620, 90 if klm else 90, 7.5, "klm" if klm else "panam")
    d._under = im
    a = clamp((kk - 0.4) / 0.5)
    col = KLM_BLUE if klm else (90, 150, 230)
    rows = ([("KLM 4805", None), ("PESAWAT", "Boeing 747-206B"), ("REGISTRASI", "PH-BUF \"Rijn\""),
             ("LALUAN", "Amsterdam → Las Palmas"), ("DI DALAM PESAWAT", "248 orang")] if klm else
            [("PAN AM 1736", None), ("PESAWAT", "Boeing 747-121"), ("REGISTRASI", "N736PA \"Clipper Victor\""),
             ("LALUAN", "Los Angeles · New York → Las Palmas"), ("DI DALAM PESAWAT", "396 orang")])
    headline(d, rows[0][0], 930, 150, a, col, tracking=4)
    draw_text(d, (W / 2, 1010), "BELANDA" if klm else "AMERIKA SYARIKAT", F("mono_b", 28), rgba(MUTED, a), 8, "mm")
    y = 1080
    for i, (kk_, vv) in enumerate(rows[1:]):
        b = clamp((kk - 0.7 - i * 0.2) / 0.4)
        d.line([140, y + 72, W - 140, y + 72], fill=rgba((255, 255, 255), 0.15 * b), width=1)
        draw_text(d, (140, y + 30), kk_, F("mono", 24), rgba(MUTED, b), 2, "lm")
        draw_text(d, (W - 140, y + 30), vv, F("inter_sb", 32), rgba(INK, b), 0, "rm")
        y += 78
    tag(d, "ILUSTRASI IKON", "ilu")
    return arr


# ------------------------------------------------------------------ scene: airport diagram
# world: d along runway (0 = rwy 12 threshold NW, 3400 = rwy 30 threshold SE), lateral (+ = taxiway side)
EX = {"C1": (250, 90), "C2": (900, 90), "C3": (1600, 148), "C4": (2250, 35)}
TWY = 170.0


def path_pos(pts, u):
    """pts list of (d,l); u 0..1 along polyline -> (d,l,heading)"""
    seg = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    tot = sum(seg); x = clamp(u) * tot
    for i, s in enumerate(seg):
        if x <= s or i == len(seg) - 1:
            f = x / s if s else 0
            p = (lerp(pts[i][0], pts[i + 1][0], f), lerp(pts[i][1], pts[i + 1][1], f))
            hd = math.atan2(pts[i + 1][1] - pts[i][1], pts[i + 1][0] - pts[i][0])
            return p[0], p[1], hd
        x -= s


KLM_PATH = [(-60, 330), (40, 220), (250, 90), (250, 0), (3330, 0), (3370, 25), (3400, 0), (3360, -12), (3330, 0)]
PA_PATH = [(-120, 300), (40, 220), (250, 90), (250, 0), (2140, 0)]


def aircraft_state(t):
    """returns dict of (d, l, heading_rad) for klm & pan am given global time."""
    if t < st("w1"):
        return (3330, 0, math.pi), (1900, 0, 0.0)
    # KLM taxi: from c1 start to ~84 reaches end and turns
    tk0, tk1 = st("c1") + 2, st("c4") + 2.5
    u = ease((t - tk0) / (tk1 - tk0))
    kd, kl, kh = path_pos(KLM_PATH, u)
    if t > tk1:
        kd, kl, kh = 3330, 0, math.pi  # facing NW (towards d=0)
    tp0, tp1 = st("c1") + 4, st("c5") + 2
    up = ease((t - tp0) / (tp1 - tp0))
    pd_, pl, ph = path_pos(PA_PATH, up)
    # takeoff roll and final evasive turn
    t_roll = st("m6")
    if t > t_roll:
        r = t - t_roll
        kd = 3330 - min(1180, 6 * r * r * 1.0)
        kh = math.pi
    if t > st("x2"):
        e = ease((t - st("x2")) / 2.5)
        pd_ += 30 * e; pl += 22 * e; ph = math.radians(35) * e
    return (kd, kl, kh), (pd_, pl, ph)


def sc_diagram(t, d, t0, t1, cam):
    k = t - t0
    arr = vgrad(H, (14, 26, 40), (12, 22, 34))
    # camera: (d_center, scale px/m)
    dc, sc = cam(t)
    def P(dd, ll):
        return (W / 2 - 60 + ll * sc, 800 + (dd - dc) * sc)
    im = Image.new("RGBA", (W, H)); g = ImageDraw.Draw(im)
    # grass texture field
    g.rectangle([0, 0, W, H], fill=(24, 38, 40, 255))
    # runway
    rw = 45 * sc
    a, b = P(0, -22.5), P(3400, 22.5)
    g.rectangle([a[0], a[1], b[0], b[1]], fill=(52, 56, 60, 255))
    for dd in range(30, 3380, 50):
        p0, p1 = P(dd, 0), P(dd + 30, 0)
        g.line([p0, p1], fill=(220, 220, 220, 200), width=max(1, int(sc * 0.9)))
    # taxiway + exits
    tw = 23 * sc
    g.line([P(0, TWY), P(3400, TWY)], fill=(60, 64, 68, 255), width=max(2, int(tw)))
    for name, (dd, ang) in EX.items():
        a_ = math.radians(ang)
        dd2 = dd + TWY / math.tan(a_) if ang != 90 else dd
        g.line([P(dd, 0), P(dd2, TWY)], fill=(60, 64, 68, 255), width=max(2, int(tw)))
        x, y = P((dd + dd2) / 2, TWY / 2)
        hl = name == "C3" and st("c4") <= t <= st("c5") + 1
        col = ORANGE if hl else (240, 200, 60)
        g.rounded_rectangle([x + 18, y - 22, x + 92, y + 22], radius=6, fill=(*((60, 30, 0) if hl else (30, 30, 20)), 230), outline=(*col, 255), width=2)
        g.text((x + 55, y), name, font=F("mono_b", 26), fill=(*col, 255), anchor="mm")
    # apron + terminal + tower
    ax0, ay0 = P(-260, 200); ax1, ay1 = P(150, 520)
    g.rectangle([ax0, ay0, ax1, ay1], fill=(58, 62, 66, 255))
    tx0, ty0 = P(-240, 470); tx1, ty1 = P(120, 540)
    g.rectangle([tx0, ty0, tx1, ty1], fill=(90, 96, 104, 255))
    # parked traffic (congestion)
    for (dd, ll, hd) in [(-200, 300, 180), (-140, 410, 180), (40, 410, 180), (110, 300, 180), (420, TWY, 0), (560, TWY, 0), (700, TWY, 0)]:
        x, y = P(dd, ll)
        draw_generic_plan(g, x, y, hd, sc, col=(120, 126, 132))
    # runway labels
    for dd, txt in ((-40, "12"), (3440, "30")):
        x, y = P(dd, 0)
        g.text((x, y), txt, font=F("oswald_b", max(20, int(sc * 40))), fill=(230, 230, 230, 255), anchor="mm")
    arr = to_f(im.convert("RGB"))
    # icons
    (kd, kl, kh), (pd_, pl, ph) = aircraft_state(t)
    ic = Image.new("RGBA", (W, H)); gi = ImageDraw.Draw(ic)
    isc = max(sc * 1.0, 1.15)
    for (dd, ll, hh, al, name, col) in [(kd, kl, kh, "klm", "KLM 4805", KLM_BLUE), (pd_, pl, ph, "panam", "PAN AM 1736", (240, 240, 240))]:
        x, y = P(dd, ll)
        # heading: world d+ is screen down; l+ is screen right. screen heading(0=up, cw)
        vx, vy = math.sin(hh), math.cos(hh)  # (l, d) components
        sh = math.degrees(math.atan2(vx, -vy))
        draw_plan(gi, x, y, sh, isc, al)
        gi.rounded_rectangle([x - 230 if al == "klm" else x + 60, y - 24, x - 60 if al == "klm" else x + 270, y + 24], radius=8, fill=(0, 0, 0, 190), outline=(*col, 255), width=2)
        gi.text((x - 145 if al == "klm" else x + 165, y), name, font=F("mono_b", 24), fill=(*col, 255), anchor="mm")
    # fog overlay & visibility circles
    fog_amt = clamp((t - st("w6")) / 4.0) * 0.55
    if t > st("c5"):
        fog_amt = 0.55 + 0.2 * clamp((t - st("c5")) / 2)
    arr = to_f(Image.alpha_composite(to_im(arr).convert("RGBA"), ic).convert("RGB"))
    if fog_amt > 0:
        arr = fog_over(arr, t, fog_amt, k=0, speed=(30, 6), color=(150, 158, 164))
    if t > st("c5"):
        b = clamp((t - st("c5")) / 0.8)
        for (dd, ll) in [(kd, kl), (pd_, pl)]:
            x, y = P(dd, ll); r = 300 * sc
            d.ellipse([x - r, y - r, x + r, y + r], outline=rgba(ORANGE, 0.8 * b), width=3)
        if t < st("c6"):
            draw_text(d, (W / 2, 330), "JARAK PENGLIHATAN SANGAT TERHAD", F("oswald_b", 50), rgba(ORANGE, b), 2, "mm")
    # captions per beat
    def cap(t0_, t1_, txt, col=INK, y=330):
        a = fade(t, t0_, t1_, 0.4)
        if a > 0:
            draw_text(d, (W / 2, y), txt, F("oswald_b", 48), rgba(col, a), 2, "mm")
    cap(st("w5"), st("w6") - 0.1, "LAPANGAN TERBANG SESAK")
    cap(st("w6"), st("c1") - 0.1, "KABUS TEBAL MULA MENYELUBUNGI", (200, 210, 220))
    cap(st("c2"), st("c3") - 0.1, "KLM DI HADAPAN · PAN AM MENGEKORI")
    cap(st("c3"), st("c4") - 0.1, "LANDASAN AKTIF DIJADIKAN LALUAN TAXI", ORANGE)
    cap(st("c4"), st("c5") - 0.1, 'ARAHAN: "KELUAR DI SIMPANG KETIGA" (C3)', ORANGE)
    cap(st("c6"), st("m1") - 0.1, "TIDAK DAPAT MELIHAT SATU SAMA LAIN", ORANGE)
    cap(st("x2"), st("x4"), "PAN AM CUBA MENGELAK", ORANGE)
    if st("c4") + 1 < t < st("c5"):
        x, y = P(1600, 0)
        a = fade(t, st("c4") + 1, st("c5"), 0.4)
        draw_text(d, (x - 120, y - 70), "C3 = PUSINGAN 148°", F("mono_b", 26), rgba(ORANGE, a), 1, "mm")
    tag(d, "ILUSTRASI · SUSUN ATUR DIPERMUDAH", "ilu")
    return arr


def cam_overview(t):
    return 1700, 0.42


def cam_follow(t):
    (kd, kl, kh), (pd_, pl, ph) = aircraft_state(t)
    return lerp(kd, pd_, 0.5), 0.40


def cam_apron(t):
    k = clamp((t - st("w5")) / 4)
    return lerp(150, 700, ease(k)), lerp(1.3, 0.75, ease(k))


def cam_final(t):
    (kd, kl, kh), (pd_, pl, ph) = aircraft_state(t)
    return (kd + pd_) / 2, 0.9


# ------------------------------------------------------------------ scene: transcript cards
def sc_transcript(t, d, t0, t1, items, title):
    k = t - t0
    arr = vgrad(H, (8, 12, 18), (16, 22, 30))
    # waveform band
    y0 = 1180
    ws = Image.new("RGBA", (W, H)); wd = ImageDraw.Draw(ws)
    pts = []
    rng = np.random.default_rng(int(t * 24))
    for i in range(0, W, 6):
        amp = 30 + 40 * abs(math.sin(i * 0.02 + t * 5)) * (0.6 + 0.4 * rng.random())
        pts.append((i, y0 + amp * math.sin(i * 0.3 + t * 30)))
    wd.line(pts, fill=(120, 200, 255, 90), width=2)
    arr = to_f(Image.alpha_composite(to_im(arr).convert("RGBA"), ws).convert("RGB"))
    draw_text(d, (80, 280), title, F("mono_b", 28), rgba(MUTED, clamp(k / 0.4)), 4, "lm")
    d.line([80, 315, W - 80, 315], fill=rgba((255, 255, 255), 0.2), width=1)
    y = 360
    for (ts, who, txt, tr, col, strike) in items:
        a = clamp((t - ts) / 0.35)
        if a <= 0:
            continue
        draw_text(d, (80, y + 20), who, F("mono_b", 26), rgba(col, a), 3, "lm")
        y += 56
        fnt = F("oswald", 54)
        lines_ = wrap(txt, fnt, W - 180)
        for ln in lines_:
            if strike:
                jit = int(4 * math.sin(t * 40))
                d.text((90 + jit, y + 24), ln, font=fnt, fill=rgba((255, 255, 255), a * 0.55), anchor="lm")
            else:
                d.text((90, y + 24), ln, font=fnt, fill=rgba((255, 255, 255), a), anchor="lm")
            y += 58
        if tr:
            for ln in wrap(tr, F("inter_m", 30), W - 180):
                d.text((90, y + 18), ln, font=F("inter_m", 30), fill=rgba(MUTED, a), anchor="lm")
                y += 42
        y += 30
    tag(d, "TRANSKRIP RASMI · CVR / ATC", "tx")
    draw_text(d, (W / 2, 1290), "Petikan transkrip daripada laporan siasatan rasmi", F("mono", 20), rgba(MUTED, 0.7), 1, "mm")
    return arr


def items_m2():
    s = st("m2")
    return [(s, "KLM 4805", "\"...we are now at take-off.\"", "\"...kami kini sedang berlepas.\"", KLM_BLUE, False),
            (s + 2.0, "MENARA", "\"OK.\"", None, (240, 200, 60), False),
            (s + 3.6, "SEBENARNYA DIBERI", "ATC CLEARANCE (laluan selepas berlepas)", "BUKAN kebenaran berlepas (take-off clearance)", ORANGE, False)]


def items_m3():
    s = st("m3")
    return [(s + 0.3, "MENARA", "\"Stand by for take-off… I will call you.\"", "\"Tunggu untuk berlepas… saya akan panggil anda.\"", (240, 200, 60), True),
            (s + 1.3, "PAN AM 1736  (SERENTAK)", "\"…we're still taxiing down the runway…\"", "\"…kami masih bergerak di landasan…\"", (230, 230, 230), True),
            (s + 3.8, "DI KOKPIT KLM", "Dua transmisi bertindih — mesej tidak jelas", None, RED, False)]


def items_m4():
    s = st("m4")
    return [(s, "MENARA", "\"Report when runway clear.\"", "\"Laporkan apabila landasan sudah kosong.\"", (240, 200, 60), False),
            (s + 1.8, "PAN AM 1736", "\"OK, we'll report when we're clear.\"", "\"OK, kami akan lapor apabila sudah keluar.\"", (230, 230, 230), False)]


def items_m5():
    s = st("m5")
    return [(s, "JURUTERA KLM", "\"Is hij er niet af, die Pan American?\"", "\"Adakah dia belum keluar, Pan American itu?\"", KLM_BLUE, False),
            (s + 3.2, "KAPTEN KLM", "\"Jawel.\"", "\"Ya, sudah.\"", KLM_BLUE, False)]


# ------------------------------------------------------------------ scene: death toll & archival
def sc_toll(t, d, t0, t1, mode):
    k = t - t0
    if mode == "583":
        arr = np.zeros((H, W, 3), np.float32)
        a = clamp(k / 1.0)
        n = int(583 * ease_out(k / 1.6))
        headline(d, str(n), 880, 380, a, (255, 255, 255), tracking=4)
        draw_text(d, (W / 2, 1110), "NYAWA TERKORBAN", F("mono_b", 40), rgba(RED, a), 10, "mm")
        draw_text(d, (W / 2, 520), "27 MAC 1977 · 17:06", F("mono", 30), rgba(MUTED, a), 4, "mm")
        return arr
    if mode == "split":
        arr = photo_plate("IMG_9811.jpg", k, t1 - t0, bw=True, dark=0.45, y_center=600)
        a = clamp((k - 0.3) / 0.5); b = clamp((k - 3.5) / 0.5)
        for (x, al, num, name, sub, aa) in [(290, "klm", "248", "KLM 4805", "semua di dalam pesawat", a), (790, "panam", "335", "PAN AM 1736", "daripada 396 orang", b)]:
            d.rounded_rectangle([x - 230, 1000, x + 230, 1280], radius=16, fill=(0, 0, 0, int(180 * aa)), outline=rgba(KLM_BLUE if al == "klm" else INK, aa), width=2)
            draw_text(d, (x, 1050), name, F("oswald_b", 40), rgba(KLM_BLUE if al == "klm" else INK, aa), 2, "mm")
            draw_text(d, (x, 1150), num, F("bebas", 130), rgba((255, 255, 255), aa), 2, "mm")
            draw_text(d, (x, 1240), sub.upper(), F("mono", 20), rgba(MUTED, aa), 1, "mm")
        tag(d, "FOTO ARKIB · SELEPAS NAHAS", "arkib")
        return arr
    if mode == "61":
        arr = photo_plate("IMG_9812.jpg", k, t1 - t0, bw=True, dark=0.35, y_center=620)
        a = clamp(k / 0.6)
        headline(d, "61", 1090, 260, a, (255, 255, 255))
        draw_text(d, (W / 2, 1240), "TERSELAMAT · SEMUANYA DARI PAN AM", F("mono_b", 32), rgba(ORANGE, a), 3, "mm")
        tag(d, "FOTO ARKIB · 1977", "arkib")
        return arr


def sc_lesson(t, d, t0, t1, mode):
    k = t - t0
    if mode == "turn":
        arr = photo_plate("IMG_9810.jpg", k, t1 - t0, bw=True, dark=0.4, y_center=640, z0=1.0, z1=1.15)
        a = clamp((k - 2.6) / 0.6)
        headline(d, "TITIK PERUBAHAN", 1120, 130, a)
        draw_text(d, (W / 2, 1210), "DALAM SEJARAH KESELAMATAN PENERBANGAN", F("mono_b", 28), rgba(ORANGE, a), 3, "mm")
        tag(d, "FOTO ARKIB · 1977", "arkib")
        return arr
    arr = vgrad(H, (10, 20, 34), (18, 34, 54))
    arr = fog_over(arr, t, 0.25, k=2, color=(40, 60, 80))
    headline(d, "PENGAJARAN", 320, 120, clamp(k / 0.5), ORANGE, tracking=6)
    cards = [("01", "FRASA STANDARD", '"TAKE-OFF" hanya digunakan untuk kebenaran berlepas sebenar'),
             ("02", "KOMUNIKASI & PENGESAHAN", "Arahan menara dan juruterbang mesti jelas dan disahkan"),
             ("03", "CREW RESOURCE MANAGEMENT", "Setiap anak kapal digalakkan bersuara dan mempersoalkan keputusan")]
    span = (t1 - t0) / 3.2
    for i, (n, h, b) in enumerate(cards):
        a = clamp((k - 0.4 - i * span) / 0.5)
        y = 450 + i * 280
        d.rounded_rectangle([80, y, W - 80, y + 240], radius=18, fill=(255, 255, 255, int(18 * a)), outline=rgba(ORANGE, 0.6 * a), width=2)
        draw_text(d, (130, y + 70), n, F("bebas", 90), rgba(ORANGE, a), 0, "lm")
        draw_text(d, (260, y + 70), h, F("oswald_b", 44), rgba(INK, a), 1, "lm")
        for j, ln in enumerate(wrap(b, F("inter_m", 30), W - 360)):
            d.text((260, y + 130 + j * 40), ln, font=F("inter_m", 30), fill=rgba(MUTED, a), anchor="lm")
    return arr


def sc_memorial(t, d, t0, t1):
    arr = sc_runway(t, d, t0, t1, "memorial")
    a = clamp((t - t0 - 0.8) / 1.0)
    draw_text(d, (W / 2, 420), "MENGENANG", F("mono_b", 34), rgba(INK, a), 12, "mm")
    headline(d, "583 NYAWA", 530, 150, a)
    draw_text(d, (W / 2, 640), "27 MAC 1977 · LOS RODEOS, TENERIFE", F("mono", 28), rgba(MUTED, a), 2, "mm")
    tag(d, "ILUSTRASI", "ilu")
    return arr


def sc_quote(t, d, t0, t1):
    arr = vgrad(H, (6, 10, 16), (12, 18, 26))
    arr = fog_over(arr, t, 0.3, k=1, color=(40, 50, 62))
    k = t - t0
    a = clamp(k / 0.6)
    draw_text(d, (W / 2, 640), "KERANA DALAM PENERBANGAN…", F("mono_b", 34), rgba(MUTED, a), 6, "mm")
    b = clamp((t - st("l6")) / 0.6)
    for i, ln in enumerate(["ONE MISUNDERSTOOD", "MESSAGE CAN", "CHANGE EVERYTHING."]):
        headline(d, ln, 800 + i * 140, 140, b, ORANGE if i == 2 else (255, 255, 255), tracking=3)
    return arr


# ------------------------------------------------------------------ edit decision list
def build_edl():
    e = []
    def add(t0, t1, fn, *args):
        e.append((t0, t1, fn, args))
    add(0, st("h1"), sc_logo)
    add(st("h1"), st("h2") - 0.2, sc_runway, "hook")
    add(st("h2") - 0.2, st("h3") - 0.2, sc_cards_hook)
    add(st("h3") - 0.2, st("h4") - 0.2, sc_diagram, cam_overview)
    add(st("h4") - 0.2, st("h5") - 0.3, sc_runway, "rush")
    add(st("h5") - 0.3, st("w1") - 0.2, sc_title)
    add(st("w1") - 0.2, st("w3") - 0.2, sc_map)
    add(st("w3") - 0.2, st("w5") - 0.2, sc_cards)
    add(st("w5") - 0.2, st("c2") - 0.2, sc_diagram, cam_apron2)
    add(st("c2") - 0.2, st("c5") - 0.2, sc_diagram, cam_follow)
    add(st("c5") - 0.2, st("c6") - 0.2, sc_runway, "vis")
    add(st("c6") - 0.2, st("m1") - 0.3, sc_diagram, cam_overview)
    add(st("m1") - 0.3, st("m2") - 0.2, sc_cockpit)
    add(st("m2") - 0.2, st("m3") - 0.2, sc_transcript, items_m2(), "17:05 · RADIO")
    add(st("m3") - 0.2, st("m4") - 0.2, sc_transcript, items_m3(), "17:06 · RADIO")
    add(st("m4") - 0.2, st("m5") - 0.2, sc_transcript, items_m4(), "17:06 · RADIO")
    add(st("m5") - 0.2, st("m6") - 0.2, sc_transcript, items_m5(), "17:06 · KOKPIT KLM (BAHASA BELANDA)")
    add(st("m6") - 0.2, st("x1") - 0.2, sc_runway, "accel")
    add(st("x1") - 0.2, st("x2") - 0.1, sc_runway, "oncoming")
    add(st("x2") - 0.1, st("x4") - 0.1, sc_diagram, cam_final)
    add(st("x4") - 0.1, st("x4") + 2.6, sc_runway, "crash")
    add(st("x4") + 2.6, st("x5") - 0.2, sc_black)
    add(st("x5") - 0.2, st("x6") - 0.2, sc_toll, "583")
    add(st("x6") - 0.2, st("x7") - 0.2, sc_toll, "split")
    add(st("x7") - 0.2, st("l1") - 0.2, sc_toll, "61")
    add(st("l1") - 0.2, st("l3") - 0.2, sc_lesson, "turn")
    add(st("l3") - 0.2, st("l4") - 0.2, sc_lesson, "cards")
    add(st("l4") - 0.2, st("l5") - 0.2, sc_memorial)
    add(st("l5") - 0.2, st("l7") - 0.2, sc_quote)
    add(st("l7") - 0.2, END, sc_logo, True)
    return e


def sc_cards_hook(t, d, t0, t1):
    arr = runway_view(t, 60, vis=360)
    arr = fog_over(arr, t, 0.6, k=1, speed=(25, 2))
    k = t - t0
    im = Image.new("RGBA", (W, H)); g = ImageDraw.Draw(im)
    draw_plan(g, lerp(-200, W / 2, ease_out(k / 1.2)), 560, 90, 8.0, "klm", 0.95)
    d._under = im
    a = clamp((k - 0.3) / 0.4)
    headline(d, "2 × BOEING 747", 960, 140, a, tracking=4)
    draw_text(d, (W / 2, 1060), "PESAWAT PENUMPANG TERBESAR ERA 1970-AN", F("mono_b", 26), rgba(ORANGE, a), 2, "mm")
    tag(d, "ILUSTRASI", "ilu")
    return bloom(arr, 0.8, 0.6)


def cam_apron2(t):
    if t < st("c1"):
        return cam_apron(t)
    (kd, kl, kh), (pd_, pl, ph) = aircraft_state(t)
    return lerp(700, 400, ease((t - st("c1")) / 3)), lerp(0.75, 0.9, ease((t - st("c1")) / 3))


def sc_cockpit(t, d, t0, t1):
    arr = sc_runway(t, d, t0, t1, "cockpit")
    cockpit_frame(d)
    a = clamp((t - t0 - 0.6) / 0.6)
    d.rounded_rectangle([140, 1300 - 330, W - 140, 1300 - 170], radius=14, fill=(0, 0, 0, int(170 * a)))
    draw_text(d, (W / 2, 1000), "KOKPIT KLM 4805", F("mono_b", 28), rgba(KLM_BLUE, a), 6, "mm")
    draw_text(d, (W / 2, 1065), "Kapten Jacob Veldhuyzen van Zanten", F("oswald", 40), rgba(INK, a), 1, "mm")
    tag(d, "ILUSTRASI", "ilu")
    return arr


def sc_black(t, d, t0, t1):
    a = fade(t, t0, t1, 0.5)
    draw_text(d, (W / 2, H / 2), "17:06", F("mono", 40), rgba((150, 150, 150), a * 0.8), 8, "mm")
    return np.zeros((H, W, 3), np.float32)


# ------------------------------------------------------------------ frame dispatcher
EDL = None


def render_frame(i):
    global EDL
    if EDL is None:
        EDL = build_edl()
    t = i / FPS
    path = os.path.join(OUT, f"{i:05d}.jpg")
    if os.path.exists(path):
        return
    for (t0, t1, fn, args) in EDL:
        if t0 <= t < t1:
            break
    ov = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(ov)
    arr = fn(t, d, t0, t1, *args)
    under = getattr(d, "_under", None)
    if under is not None:
        arr = to_f(Image.alpha_composite(to_im(arr).convert("RGBA"), under).convert("RGB"))
    extra = getattr(d, "_ov", None)
    if extra is not None:
        extra.alpha_composite(ov); ov = extra; d = ImageDraw.Draw(ov)
    # dip to black at scene cuts (short)
    dipa = 0.0
    for (a0, a1, _, _) in EDL:
        if abs(t - a0) < 0.12 and a0 > 0:
            dipa = max(dipa, 1 - abs(t - a0) / 0.12)
    if dipa:
        arr = arr * (1 - 0.6 * dipa)
    if fn not in (sc_logo,):
        brand(d)
    subtitle(d, t)
    im = finish(arr, t, ov)
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
                if j % 500 == 0:
                    print(j, "/", n, flush=True)
        print("done", n)
