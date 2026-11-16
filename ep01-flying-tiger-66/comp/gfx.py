"""2D drawing toolkit (PIL + numpy) - shared with the Tenerife episode, plus Flying Tigers livery."""
import math, os, json, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageChops

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "assets")
CACHE = os.path.join(ROOT, "build", "cache")
os.makedirs(CACHE, exist_ok=True)
W, H = 1080, 1920
FPS = 24

ORANGE = (242, 140, 40)
RED = (200, 58, 50)
KLM_BLUE = (64, 152, 210)
KLM_DARK = (14, 52, 120)
PA_BLUE = (22, 82, 160)
FT_NAVY = (20, 34, 78)
FT_RED = (196, 36, 44)
FOG = (150, 158, 164)
INK = (232, 234, 236)
MUTED = (160, 168, 176)


# ------------------------------------------------------------------ easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in(x):
    x = clamp(x)
    return x ** 3


def lerp(a, b, t):
    return a + (b - a) * t


def fade(t, t0, t1, d=0.4):
    """1 inside [t0,t1] with fades of length d at either end."""
    return clamp((t - t0) / d) * clamp((t1 - t) / d)


# ------------------------------------------------------------------ fonts & text
@functools.lru_cache(None)
def F(name, size):
    files = {
        "bebas": "bebas-neue-latin-400-normal.woff",
        "oswald": "oswald-latin-500-normal.woff",
        "oswald_l": "oswald-latin-300-normal.woff",
        "oswald_b": "oswald-latin-700-normal.woff",
        "mono": "ibm-plex-mono-latin-400-normal.woff",
        "mono_b": "ibm-plex-mono-latin-600-normal.woff",
        "inter": "Inter-Regular.otf",
        "inter_m": "Inter-Medium.otf",
        "inter_sb": "Inter-SemiBold.otf",
        "inter_b": "Inter-Bold.otf",
        "disp": "InterDisplay-Bold.otf",
        "disp_k": "InterDisplay-Black.otf",
    }
    return ImageFont.truetype(os.path.join(A, "fonts", files[name]), size)


def text_w(s, font, tracking=0):
    return font.getlength(s) + tracking * max(0, len(s) - 1)


def draw_text(d, xy, s, font, fill, tracking=0, anchor="la"):
    """Text with letter spacing. anchor: l/m/r + a/m/s (like PIL)."""
    x, y = xy
    if tracking == 0:
        d.text((x, y), s, font=font, fill=fill, anchor=anchor)
        return
    w = text_w(s, font, tracking)
    if anchor[0] == "m":
        x -= w / 2
    elif anchor[0] == "r":
        x -= w
    va = "l" + anchor[1]
    for ch in s:
        d.text((x, y), ch, font=font, fill=fill, anchor=va)
        x += font.getlength(ch) + tracking


def wrap(s, font, maxw):
    words = s.split()
    lines, cur = [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if font.getlength(t) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def rgba(c, a):
    return (int(c[0]), int(c[1]), int(c[2]), int(clamp(a) * 255))


# ------------------------------------------------------------------ noise / fog
def _smooth_noise(n, sigma, seed):
    rng = np.random.default_rng(seed)
    x = rng.standard_normal((n, n))
    fx = np.fft.fftfreq(n)[:, None]
    fy = np.fft.fftfreq(n)[None, :]
    g = np.exp(-(fx ** 2 + fy ** 2) * (sigma ** 2) * 2 * math.pi ** 2)
    y = np.real(np.fft.ifft2(np.fft.fft2(x) * g))
    y = (y - y.mean()) / (y.std() + 1e-9)
    return y


@functools.lru_cache(None)
def fog_tex(k):
    p = os.path.join(CACHE, f"fog{k}.npy")
    if os.path.exists(p):
        return np.load(p)
    n = 1024
    y = _smooth_noise(n, 60, k) * 0.65 + _smooth_noise(n, 22, k + 10) * 0.3 + _smooth_noise(n, 8, k + 20) * 0.12
    y = 1 / (1 + np.exp(-1.6 * y))  # 0..1
    y = y.astype(np.float32)
    np.save(p, y)
    return y


def fog_layer(t, k=0, speed=(30, 4), scale=2.0, w=W, h=H):
    """returns float32 (h,w) fog density in 0..1, drifting, tiled."""
    tex = fog_tex(k)
    n = tex.shape[0]
    ys = (np.arange(h) / scale + t * speed[1]).astype(np.int64) % n
    xs = (np.arange(w) / scale + t * speed[0]).astype(np.int64) % n
    return tex[ys[:, None], xs[None, :]]


@functools.lru_cache(8)
def _fog_small(k):
    return fog_tex(k)


def fog_over(img, t, amount, k=0, speed=(25, 3), scale=2.2, color=FOG, y_bias=None):
    """Composite drifting fog onto float image (h,w,3) 0..1. amount 0..1.
    y_bias: optional (h,) weights (e.g. more fog near horizon)."""
    h, w = img.shape[:2]
    f = fog_layer(t, k, speed, scale, w, h)
    a = np.clip((f - 0.25) * 1.4, 0, 1) * amount
    if y_bias is not None:
        a = a * y_bias[:, None]
    c = np.array(color, np.float32) / 255
    return img * (1 - a[..., None]) + c * a[..., None]


# ------------------------------------------------------------------ image helpers
def to_f(im):
    return np.asarray(im.convert("RGB"), dtype=np.float32) / 255


def to_im(a):
    return Image.fromarray(np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8))


def vgrad(h, top, bot, w=W):
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    top = np.array(top, np.float32) / 255; bot = np.array(bot, np.float32) / 255
    return np.broadcast_to(top * (1 - t) + bot * t, (h, w, 3)).copy()


def bloom(a, thresh=0.7, strength=0.8, radius=40):
    small = to_im(np.clip(a - thresh, 0, 1) / (1 - thresh)).resize((W // 4, H // 4), Image.BILINEAR)
    b = small.filter(ImageFilter.GaussianBlur(radius / 4)).resize((W, H), Image.BILINEAR)
    b2 = small.filter(ImageFilter.GaussianBlur(radius / 12)).resize((W, H), Image.BILINEAR)
    return a + (to_f(b) * 0.6 + to_f(b2) * 0.4) * strength


def glow_dot(layer_d, x, y, r, col, a=1.0):
    """additive-ish glow on RGBA layer (draw concentric circles)."""
    steps = 10
    for i in range(steps, 0, -1):
        rr = r * i / steps
        al = a * (1 - i / steps) ** 1.6 * 0.5 + (0.0)
        layer_d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=rgba(col, al))


def add_glow(arr, x, y, r, col, a):
    """Physically additive radial glow into float arr."""
    if a <= 0.002 or r < 0.5:
        return
    h, w = arr.shape[:2]
    R = int(r * 4) + 2
    x0, x1 = int(max(0, x - R)), int(min(w, x + R + 1))
    y0, y1 = int(max(0, y - R)), int(min(h, y + R + 1))
    if x0 >= x1 or y0 >= y1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    d2 = ((xx - x) ** 2 + (yy - y) ** 2) / (r * r)
    g = np.exp(-d2 * 2.0) + 0.12 * np.exp(-d2 * 0.18)
    c = np.array(col, np.float32) / 255
    arr[y0:y1, x0:x1] += (g * a)[..., None] * c


@functools.lru_cache(None)
def load_photo(name):
    return Image.open(os.path.join(A, "archival", name)).convert("RGB")


def photo_plate(name, t, dur, crop=None, z0=1.0, z1=1.12, pan=(0, 0), plate_h=None, bw=False, dark=0.0, y_center=None):
    """Full-frame vertical composition: blurred dark enlarged photo as backdrop and
    the photo itself as a full-width plate with slow Ken Burns. returns float arr."""
    im = load_photo(name)
    if crop:
        im = im.crop(crop)
    if bw:
        im = ImageOps.grayscale(im).convert("RGB")
    # backdrop
    bgk = ("bg", name, crop, bw)
    bg = _bg_cache(name, crop, bw)
    arr = bg.copy()
    k = clamp(t / max(dur, 1e-3))
    z = lerp(z0, z1, ease(k))
    pw = W
    ph = plate_h or int(W * im.height / im.width)
    # crop window in source for zoom
    cw, ch = im.width / z, im.height / z
    cx = im.width / 2 + pan[0] * (im.width - cw) / 2 * (2 * ease(k) - 1)
    cy = im.height / 2 + pan[1] * (im.height - ch) / 2 * (2 * ease(k) - 1)
    # aspect of plate
    target_ar = pw / ph
    if cw / ch > target_ar:
        cw = ch * target_ar
    else:
        ch = cw / target_ar
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    plate = im.transform((pw, ph), Image.EXTENT, box, Image.BICUBIC)
    pa = to_f(plate)
    yc = y_center or H // 2 - 80
    y0 = yc - ph // 2
    # soft edges top/bottom
    m = np.ones(ph, np.float32)
    e = 60
    m[:e] = np.linspace(0, 1, e) ** 1.5
    m[-e:] = np.linspace(1, 0, e) ** 1.5
    ys0, ys1 = max(0, y0), min(H, y0 + ph)
    arr[ys0:ys1] = arr[ys0:ys1] * (1 - m[ys0 - y0:ys1 - y0, None, None]) + pa[ys0 - y0:ys1 - y0] * m[ys0 - y0:ys1 - y0, None, None]
    if dark:
        arr *= (1 - dark)
    return arr


@functools.lru_cache(16)
def _bg_cache(name, crop, bw):
    im = load_photo(name)
    if crop:
        im = im.crop(crop)
    if bw:
        im = ImageOps.grayscale(im).convert("RGB")
    s = max(W / im.width, H / im.height) * 1.1
    big = im.resize((int(im.width * s), int(im.height * s)), Image.BILINEAR)
    l = (big.width - W) // 2; tp = (big.height - H) // 2
    big = big.crop((l, tp, l + W, tp + H)).filter(ImageFilter.GaussianBlur(28))
    return to_f(big) * 0.32


# ------------------------------------------------------------------ 747 side profile (accurate proportions)
L747 = 70.6
R747 = 3.25
ZC = 6.0


def fuse_profile(s):
    nose_len, tail_start = 14.0, 50.0
    R = R747
    if s < nose_len:
        t = s / nose_len
        k = math.sqrt(max(0.0, 1 - (1 - t) ** 2.15))
        a = R * k; zc = -0.55 * (1 - t) ** 2; bt = bb = a
    elif s <= tail_start:
        zc, bt, bb = 0.0, R, R
    else:
        t = (s - tail_start) / (L747 - tail_start)
        ztop = R - 0.80 * t ** 1.6
        zbot = -R + 4.75 * t ** 1.25
        zc = (ztop + zbot) / 2
        bt = bb = max(0.05, (ztop - zbot) / 2)
    def ss(x):
        x = min(1, max(0, x)); return x * x * (3 - 2 * x)
    h = 1.55 * ss((s - 1.2) / 7.2) * (1 - ss((s - 18.5) / 12.5))
    return zc, bt * 1.06, bb * 1.02, h

class _SD:
    """ImageDraw wrapper that sorts box coordinates (nose-right drawings flip x)."""
    def __init__(self, d):
        self.d = d
    def _b(self, b):
        x0, y0, x1, y1 = b
        return [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]
    def rounded_rectangle(self, b, **k):
        return self.d.rounded_rectangle(self._b(b), **k)
    def ellipse(self, b, **k):
        return self.d.ellipse(self._b(b), **k)
    def rectangle(self, b, **k):
        return self.d.rectangle(self._b(b), **k)
    def __getattr__(self, n):
        return getattr(self.d, n)


@functools.lru_cache(None)
def side_747(airline, ppm=24):
    """RGBA side view, nose pointing RIGHT. ppm = pixels per metre. Returns (img, ground_y)."""
    p = os.path.join(CACHE, f"side_{airline}_{ppm}.png")
    if os.path.exists(p):
        im = Image.open(p); return im, im.height - int(0.3 * ppm)
    Wm, Hm = 74.0, 20.5
    w, h = int(Wm * ppm), int(Hm * ppm)
    ox = 1.5  # metres margin at left (tail side)
    def X(s):  # s from nose; nose at right
        return (ox + L747 - s) * ppm
    def Y(z):
        return h - int(0.3 * ppm) - z * ppm
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = _SD(ImageDraw.Draw(img))

    if airline == "klm":
        upper, cheat, thin, lower, belly = KLM_BLUE, KLM_DARK, (245, 245, 245), (205, 208, 211), (176, 180, 184)
        wingc, nacc = (168, 172, 176), (188, 190, 193)
    elif airline == "tiger":
        upper, cheat, thin, lower, belly = (236, 238, 240), FT_RED, FT_NAVY, (214, 218, 222), (176, 180, 186)
        wingc, nacc = (172, 176, 182), (198, 201, 205)
    else:
        upper, cheat, thin, lower, belly = (244, 244, 242), PA_BLUE, PA_BLUE, (244, 244, 242), (178, 182, 186)
        wingc, nacc = (170, 174, 178), (196, 198, 201)

    # far-side engines & far wing (darker) drawn first
    def nacelle(s_front, zc_, col, dark=1.0):
        c = tuple(int(v * dark) for v in col)
        L_, r = 7.2, 1.33
        d.rounded_rectangle([X(s_front), Y(zc_ + r), X(s_front + L_ - 1.2), Y(zc_ - r)], radius=int(r * ppm * 0.9), fill=c)
        d.polygon([(X(s_front + L_ - 1.4), Y(zc_ + 0.95)), (X(s_front + L_ + 0.4), Y(zc_ + 0.55)),
                   (X(s_front + L_ + 0.4), Y(zc_ - 0.55)), (X(s_front + L_ - 1.4), Y(zc_ - 0.95))], fill=tuple(int(v * 0.8) for v in c))
        d.polygon([(X(s_front + L_ + 0.4), Y(zc_ + 0.4)), (X(s_front + L_ + 1.4), Y(zc_)), (X(s_front + L_ + 0.4), Y(zc_ - 0.4))], fill=(90, 90, 92))
        # intake lip
        d.ellipse([X(s_front) - 0.25 * ppm, Y(zc_ + r * 0.95), X(s_front) + 0.35 * ppm, Y(zc_ - r * 0.95)], fill=tuple(int(v * 0.55) for v in c))
        d.line([X(s_front + 2.2), Y(zc_ + r * 0.95), X(s_front + 2.2), Y(zc_ - r * 0.95)], fill=tuple(int(v * 0.85) for v in c), width=max(1, ppm // 12))
    wz = ZC - 2.05
    nacelle(41.4 - 4.6, wz + 18.6 * 0.1228 - 1.95, nacc, 0.72)
    nacelle(33.6 - 4.6, wz + 9.2 * 0.1228 - 1.95, nacc, 0.78)
    # far wing silhouette
    d.polygon([(X(27.5), Y(wz + 0.3)), (X(48.0), Y(wz + 3.1 + 0.25)), (X(51.8), Y(wz + 3.1 + 0.25)), (X(44.0), Y(wz - 0.2))], fill=tuple(int(v * 0.6) for v in wingc))

    # fuselage mask + paint using numpy per column
    ss = np.linspace(0, L747, 1400)
    top = []; bot = []
    for s in ss:
        zc, bt, bb, hh = fuse_profile(s)
        top.append((X(s), Y(ZC + zc + bt + hh)))
        bot.append((X(s), Y(ZC + zc - bb)))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).polygon(top + bot[::-1], fill=255)
    paint = np.zeros((h, w, 3), np.float32)
    cols = np.arange(w)
    s_of_col = L747 + ox - cols / ppm
    rows = np.arange(h)
    z_of_row = (h - int(0.3 * ppm) - rows) / ppm  # absolute height
    zcs = np.zeros(w); bts = np.ones(w)
    for i, s in enumerate(s_of_col):
        if 0 <= s <= L747:
            zc, bt, bb, hh = fuse_profile(s)
            zcs[i] = ZC + zc; bts[i] = max(bt / 1.06, 0.05)
    zn = (z_of_row[:, None] - zcs[None, :]) / bts[None, :] * R747  # normalised to constant section metres
    def setc(m, c):
        paint[m] = np.array(c, np.float32)
    setc(np.ones_like(zn, bool), lower)
    if airline == "klm":
        setc(zn >= 1.05, upper)
        setc((zn >= 0.35) & (zn < 1.05) & (s_of_col[None, :] > 2.0) & (s_of_col[None, :] < 66), cheat)
        setc((zn >= 0.22) & (zn < 0.35) & (s_of_col[None, :] > 2.0) & (s_of_col[None, :] < 66), thin)
        setc(zn < -1.6, belly)
    elif airline == "tiger":
        setc(zn >= 0.30, upper)
        setc((zn >= 0.05) & (zn < 0.30) & (s_of_col[None, :] > 2.5) & (s_of_col[None, :] < 62), cheat)
        setc((zn >= -0.22) & (zn < 0.05) & (s_of_col[None, :] > 2.5) & (s_of_col[None, :] < 62), thin)
        setc(zn < -1.4, belly)
    else:
        setc(zn < -0.55, belly)
        setc((zn >= 0.48) & (zn < 0.95) & (s_of_col[None, :] > 1.5) & (s_of_col[None, :] < 64), cheat)
        setc((zn >= 0.30) & (zn < 0.38) & (s_of_col[None, :] > 1.5) & (s_of_col[None, :] < 64), thin)
    # simple cylindrical shading: brighter at top, darker at belly
    shade = np.clip(0.80 + 0.25 * np.clip(zn / R747, -1, 1), 0.55, 1.08)
    paint = paint * shade[..., None]
    pim = Image.fromarray(np.clip(paint, 0, 255).astype(np.uint8)).convert("RGBA")
    pim.putalpha(mask)
    img.alpha_composite(pim)
    d = _SD(ImageDraw.Draw(img))

    # windows
    doors = [7.2, 17.6, 31.0, 44.0, 57.5]
    wc = (190, 214, 236) if airline == "klm" else (32, 40, 54)
    def zabs(s, znorm):
        zc, bt, bb, hh = fuse_profile(s)
        return ZC + zc + znorm / R747 * (bt / 1.06)
    s = 6.0
    while s < 63.5 and airline != "tiger":  # freighter: no main-deck windows
        if all(abs(s - ds) > 1.0 for ds in doors):
            z = zabs(s, 0.70)
            d.rounded_rectangle([X(s) - 0.12 * ppm, Y(z + 0.18), X(s) + 0.12 * ppm, Y(z - 0.18)], radius=max(1, ppm // 10), fill=wc)
        s += 0.508
    for ds in (doors if airline != "tiger" else [7.2]):
        z = zabs(ds, 0.70)
        d.rounded_rectangle([X(ds) - 0.55 * ppm, Y(z + 1.25), X(ds) + 0.55 * ppm, Y(z - 0.75)], radius=max(2, ppm // 6),
                            outline=(110, 114, 120) if airline != "klm" else (10, 34, 86), width=max(1, ppm // 14))
        d.rounded_rectangle([X(ds) - 0.12 * ppm, Y(z + 0.18), X(ds) + 0.12 * ppm, Y(z - 0.18)], radius=max(1, ppm // 10), fill=wc)
    # cockpit windows (slanted strip on the hump nose)
    cz = ZC + fuse_profile(4.2)[0] + 0.0
    pts = [(X(3.15), Y(ZC + 2.05)), (X(5.6), Y(ZC + 2.55)), (X(5.6), Y(ZC + 2.05)), (X(3.55), Y(ZC + 1.62))]
    d.polygon(pts, fill=(18, 22, 30))
    for s_ in (4.0, 4.8):
        d.line([X(s_), Y(ZC + 2.55), X(s_ - 0.25), Y(ZC + 1.55)], fill=upper, width=max(1, ppm // 10))
    for s_ in (9.3, 10.5, 11.7):
        d.rounded_rectangle([X(s_) - 0.12 * ppm, Y(ZC + 4.05), X(s_) + 0.12 * ppm, Y(ZC + 3.65)], radius=2, fill=wc if airline == "klm" else (32, 40, 54))
    # titles
    if airline == "tiger":
        # main-deck side cargo door outline (aft)
        z = zabs(52.0, 0.0)
        d.rounded_rectangle([X(49.6), Y(z + 2.1), X(54.6), Y(z - 1.0)], radius=max(2, ppm // 8), outline=(150, 154, 160), width=max(1, ppm // 14))
        d.text((X(24.0), Y(ZC + 1.55)), "FLYING TIGER LINE", font=F("disp_k", int(1.25 * ppm)), fill=FT_NAVY, anchor="mm")
        d.text((X(60.5), Y(ZC + 1.25)), "N807FT", font=F("inter_b", int(0.5 * ppm)), fill=(40, 44, 54), anchor="mm")
    elif airline == "klm":
        f1 = F("disp_k", int(1.15 * ppm)); f2 = F("inter_sb", int(0.42 * ppm))
        d.text((X(21.5), Y(ZC + 1.55)), "KLM", font=f1, fill=(255, 255, 255), anchor="mm")
        _crown(d, X(21.5), Y(ZC + 2.55), 0.45 * ppm, (255, 255, 255))
        d.text((X(21.5), Y(ZC + 0.02)), "Royal Dutch Airlines", font=f2, fill=KLM_DARK, anchor="mm")
        d.text((X(61.0), Y(ZC + 1.45)), "PH-BUF", font=F("inter_b", int(0.55 * ppm)), fill=(255, 255, 255), anchor="mm")
    else:
        f1 = F("disp_k", int(1.45 * ppm))
        d.text((X(14.0), Y(ZC + 2.05)), "PAN AM", font=f1, fill=(18, 18, 20), anchor="mm")
        d.text((X(13.5), Y(ZC + 1.25)), "Clipper Victor", font=F("inter_m", int(0.38 * ppm)), fill=(40, 70, 140), anchor="mm")
        d.text((X(59.5), Y(ZC + 1.45)), "N736PA", font=F("inter_b", int(0.5 * ppm)), fill=(40, 40, 44), anchor="mm")

    # vertical fin
    fin = [(X(52.5), Y(ZC + 2.9)), (X(67.0), Y(19.25)), (X(71.3), Y(19.25)), (X(70.0), Y(ZC + 1.9)), (X(64.0), Y(ZC + 2.6))]
    d.polygon(fin, fill=(240, 240, 238))
    d.line([X(67.0), Y(19.25), X(71.3), Y(19.25)], fill=(200, 200, 200), width=2)
    if airline == "tiger":
        d.polygon(fin, fill=FT_NAVY)
        lg = tiger_logo(int(4.4 * ppm))
        img.alpha_composite(lg, (int(X(65.8) - lg.width / 2), int(Y(13.4) - lg.height / 2)))
    elif airline == "klm":
        _crown(d, X(65.0), Y(14.9), 0.9 * ppm, KLM_DARK)
        d.text((X(65.2), Y(12.9)), "KLM", font=F("disp_k", int(1.9 * ppm)), fill=KLM_DARK, anchor="mm")
    else:
        g = _globe(int(4.6 * ppm))
        img.alpha_composite(g, (int(X(66.0) - g.width / 2), int(Y(13.2) - g.height / 2)))
        fl = _usflag(int(1.6 * ppm), int(0.9 * ppm))
        img.alpha_composite(fl, (int(X(67.6) - fl.width / 2), int(Y(17.4) - fl.height / 2)))
    # horizontal stabiliser (near side)
    d.polygon([(X(59.6), Y(ZC + 1.3)), (X(68.0), Y(ZC + 2.4)), (X(70.7), Y(ZC + 2.4)), (X(69.2), Y(ZC + 1.05))], fill=wingc)

    # near wing + near engines
    d.polygon([(X(26.0), Y(wz - 0.1)), (X(48.2), Y(wz + 3.35)), (X(52.0), Y(wz + 3.35)), (X(44.5), Y(wz - 0.55)), (X(43.0), Y(wz - 0.75))], fill=wingc)
    d.line([(X(26.0), Y(wz - 0.1)), (X(48.2), Y(wz + 3.35))], fill=tuple(min(255, v + 30) for v in wingc), width=max(1, ppm // 10))
    # pylons
    for (s_f, zz) in [(33.6 - 4.6, wz + 9.2 * 0.1228 - 1.95), (41.4 - 4.6, wz + 18.6 * 0.1228 - 1.95)]:
        d.polygon([(X(s_f + 1.5), Y(zz + 1.2)), (X(s_f + 6.0), Y(zz + 2.3)), (X(s_f + 7.4), Y(zz + 2.0)), (X(s_f + 6.0), Y(zz + 1.2))], fill=tuple(int(v * 0.9) for v in wingc))
    nacelle(33.6 - 4.6, wz + 9.2 * 0.1228 - 1.95, nacc, 1.0)

    # landing gear
    gc = (60, 60, 62)
    for s_ in (33.8, 36.6):
        d.line([X(s_), Y(ZC - 2.6), X(s_), Y(0.62)], fill=(120, 120, 124), width=max(2, ppm // 5))
        for dx in (-0.75, 0.75):
            d.ellipse([X(s_ + dx) - 0.62 * ppm, Y(1.24), X(s_ + dx) + 0.62 * ppm, Y(0)], fill=(22, 22, 24))
            d.ellipse([X(s_ + dx) - 0.3 * ppm, Y(0.92), X(s_ + dx) + 0.3 * ppm, Y(0.32)], fill=(110, 110, 112))
    d.line([X(7.8), Y(ZC - 2.9), X(7.8), Y(0.55)], fill=(120, 120, 124), width=max(2, ppm // 6))
    d.ellipse([X(7.8) - 0.55 * ppm, Y(1.1), X(7.8) + 0.55 * ppm, Y(0)], fill=(22, 22, 24))
    img.save(p)
    return img, h - int(0.3 * ppm)


@functools.lru_cache(None)
def tiger_logo(size, ring=(245, 245, 245), bg=None):
    """Simplified Flying Tigers tail mark: segmented ring with a 'T'."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = size / 2; r0, r1 = size * 0.48, size * 0.36
    if bg:
        d.ellipse([c - r0, c - r0, c + r0, c + r0], fill=bg)
    n = 12
    for i in range(n):
        a0 = 360 / n * i + 4; a1 = 360 / n * (i + 1) - 4
        d.pieslice([c - r0, c - r0, c + r0, c + r0], a0, a1, fill=ring)
    d.ellipse([c - r1, c - r1, c + r1, c + r1], fill=bg or (0, 0, 0, 0))
    if not bg:  # punch the hole
        m = Image.new("L", (size, size), 255); ImageDraw.Draw(m).ellipse([c - r1, c - r1, c + r1, c + r1], fill=0)
        im.putalpha(ImageChops.multiply(im.split()[3], m))
        d = ImageDraw.Draw(im)
    tw, th = size * 0.08, size * 0.42
    d.rectangle([c - size * 0.24, c - size * 0.20, c + size * 0.24, c - size * 0.10], fill=ring)
    d.polygon([(c - tw, c - size * 0.10), (c + tw, c - size * 0.10), (c + tw * 0.6, c + size * 0.28), (c - tw * 0.6, c + size * 0.28)], fill=ring)
    return im


def _crown(d, cx, cy, s, col):
    """simplified crown mark centred at cx,cy; s ~ half-width in px"""
    k = s / 100
    d.rounded_rectangle([cx - 80 * k, cy + 30 * k, cx + 80 * k, cy + 48 * k], radius=6 * k, fill=col)
    for i, x in enumerate([-65, -28, 28, 65]):
        y = 8 if i in (0, 3) else -10
        d.ellipse([cx + (x - 12) * k, cy + (y - 12) * k, cx + (x + 12) * k, cy + (y + 12) * k], fill=col)
    d.ellipse([cx - 13 * k, cy - 30 * k, cx + 13 * k, cy - 4 * k], fill=col)
    d.rectangle([cx - 5 * k, cy - 70 * k, cx + 5 * k, cy - 30 * k], fill=col)
    d.rectangle([cx - 16 * k, cy - 59 * k, cx + 16 * k, cy - 50 * k], fill=col)


def _globe(size):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    blue = (25, 105, 180, 255)
    d.ellipse([0, 0, size - 1, size - 1], fill=blue)
    c = size / 2; r = size / 2 - 2; lw = max(2, size // 60)
    for k in (0.3, 0.62, 0.88):
        d.ellipse([c - r * k, 2, c + r * k, size - 3], outline=(255, 255, 255, 255), width=lw)
    d.line([c, 2, c, size - 3], fill=(255, 255, 255, 255), width=lw)
    for k in (-0.62, -0.32, 0.32, 0.62):
        y = c + r * k; half = math.sqrt(max(0, r * r - (r * k) ** 2))
        d.line([c - half, y, c + half, y], fill=(255, 255, 255, 255), width=lw)
    bh = size * 0.2
    d.rectangle([0, c - bh / 2, size, c + bh / 2], fill=blue)
    d.text((c, c), "PAN AM", font=F("disp_k", int(size * 0.15)), fill=(255, 255, 255, 255), anchor="mm")
    mask = Image.new("L", (size, size), 0); ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    im.putalpha(ImageChops.multiply(im.split()[3], mask))
    return im


def _usflag(w, h):
    im = Image.new("RGBA", (w, h), (255, 255, 255, 255)); d = ImageDraw.Draw(im)
    sh = h / 13
    for i in range(0, 13, 2):
        d.rectangle([0, i * sh, w, (i + 1) * sh], fill=(178, 34, 52, 255))
    d.rectangle([0, 0, w * 0.4, sh * 7], fill=(60, 59, 110, 255))
    return im


def sprite_scaled(airline, length_px, flip=False):
    """side sprite scaled so the aircraft length is length_px. nose right unless flip."""
    im, gy = side_747(airline)
    k = length_px / (L747 * 24)
    s = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    if flip:
        s = s.transpose(Image.FLIP_LEFT_RIGHT)
    return s, int(gy * k)


# ------------------------------------------------------------------ 747 planform (top view), nose = +x
def planform_poly():
    def P(s, y):
        return (L747 / 2 - s, y)
    body = []
    for s in np.linspace(0, L747, 60):
        zc, bt, bb, hh = fuse_profile(s)
        half = min(R747, max(0.15, bt / 1.06)) if s < 14 or s > 50 else R747
        body.append(P(s, half))
    body = body + [(x, -y) for (x, y) in body[::-1]]
    wing = [P(26.0, 3), P(48.3, 29.8), P(52.0, 29.8), P(45.0, 11.6), P(43.6, 3)]
    wing2 = [(x, -y) for (x, y) in wing]
    hs = [P(59.6, 1.0), P(68.0, 11.0), P(70.7, 11.0), P(69.0, 1.0)]
    hs2 = [(x, -y) for (x, y) in hs]
    eng = []
    for (y, le) in [(11.8, 33.6), (21.2, 41.4)]:
        for sg in (1, -1):
            eng.append([P(le - 4.6, sg * (y - 1.3)), P(le + 2.6, sg * (y - 1.1)), P(le + 2.6, sg * (y + 1.1)), P(le - 4.6, sg * (y + 1.3))])
    return body, [wing, wing2, hs, hs2], eng


def draw_plan(d, x, y, heading_deg, scale, airline, alpha=1.0, outline=True):
    """heading in screen degrees (0 = pointing up / -y screen, clockwise positive)."""
    body, flats, eng = planform_poly()
    th = math.radians(heading_deg)
    def tr(p):
        px, py = p  # px forward, py left
        # forward vector on screen: (sin th, -cos th); left vector: (-cos th, -sin th)
        fx, fy = math.sin(th), -math.cos(th)
        lx, ly = -math.cos(th), -math.sin(th)
        return (x + (px * fx + py * lx) * scale, y + (px * fy + py * ly) * scale)
    if airline == "klm":
        bc, wc, ec = KLM_BLUE, (190, 196, 202), (200, 204, 208)
    elif airline == "panam":
        bc, wc, ec = (245, 245, 245), (190, 196, 202), (200, 204, 208)
    elif airline == "tiger":
        bc, wc, ec = (228, 231, 235), (176, 182, 190), (196, 200, 206)
    else:
        bc, wc, ec = (120, 126, 132), (100, 106, 112), (100, 106, 112)
    a = int(255 * alpha)
    for fl in flats:
        d.polygon([tr(p) for p in fl], fill=(*wc, a), outline=(20, 24, 30, a) if outline else None)
    for e in eng:
        d.polygon([tr(p) for p in e], fill=(*ec, a))
    d.polygon([tr(p) for p in body], fill=(*bc, a), outline=(20, 24, 30, a) if outline else None)
    if airline == "panam":
        # blue cheatline hint along body
        d.line([tr((L747 / 2 - 6, 0)), tr((L747 / 2 - 62, 0))], fill=(*PA_BLUE, a), width=max(1, int(scale * 0.9)))
    if airline == "tiger":
        d.line([tr((L747 / 2 - 8, 0)), tr((L747 / 2 - 60, 0))], fill=(*FT_RED, a), width=max(1, int(scale * 1.2)))
        d.polygon([tr(p) for p in [(L747 / 2 - 64, 0.6), (L747 / 2 - 70.6, 0.6), (L747 / 2 - 70.6, -0.6), (L747 / 2 - 64, -0.6)]], fill=(*FT_NAVY, a))


def draw_generic_plan(d, x, y, heading_deg, scale, length=45, col=(120, 126, 132), alpha=1.0):
    th = math.radians(heading_deg)
    fx, fy = math.sin(th), -math.cos(th)
    lx, ly = -math.cos(th), -math.sin(th)
    def tr(px, py):
        return (x + (px * fx + py * lx) * scale, y + (px * fy + py * ly) * scale)
    Lh = length / 2; span = length * 0.8 / 2
    a = int(255 * alpha)
    d.polygon([tr(-0.05 * length, 1.8), tr(-0.3 * length, span), tr(-0.38 * length, span), tr(-0.22 * length, 1.8)], fill=(*col, a))
    d.polygon([tr(-0.05 * length, -1.8), tr(-0.3 * length, -span), tr(-0.38 * length, -span), tr(-0.22 * length, -1.8)], fill=(*col, a))
    d.polygon([tr(-0.82 * Lh * 1.0, 1), tr(-Lh, 6), tr(-Lh - 2, 6), tr(-Lh - 2, -6), tr(-Lh, -6), tr(-0.82 * Lh, -1)], fill=(*col, a))
    d.polygon([tr(Lh, 0), tr(Lh - 3, 1.9), tr(-Lh, 1.5), tr(-Lh, -1.5), tr(Lh - 3, -1.9)], fill=(*[min(255, c + 30) for c in col], a))


# ------------------------------------------------------------------ perspective runway (2D projection)
def runway_view(t, travel, vis=320.0, cam_h=9.0, horizon=820, f=1100.0, lateral=0.0, shake=0.0,
                oncoming=None, sky=(120, 128, 135), fog_col=(142, 150, 156), edge_lights=True, light_scale=1.0,
                yaw=0.0, darkness=0.0):
    """Ground-level view along a runway into fog. travel: metres the camera has moved.
    oncoming: dict(z=distance m, x=lateral m, lights=1.0, size=1.0, sil=alpha) for an approaching 747.
    returns float array."""
    hz = horizon + shake * math.sin(t * 61) * 2.0
    cx = W / 2 + yaw + shake * math.sin(t * 47) * 2.0
    arr = vgrad(H, (sky[0] * 0.78, sky[1] * 0.78, sky[2] * 0.8), fog_col)
    # ground region
    yy = np.arange(H, dtype=np.float32)
    below = yy > hz + 0.5
    z_row = np.full(H, 1e5, np.float32)
    z_row[below] = f * cam_h / (yy[below] - hz)
    fogk = 1 - np.exp(-z_row / vis)
    # ground base colours: grass and asphalt by column via x = (col-cx)*z/f
    cols = np.arange(W, dtype=np.float32)
    Xg = (cols[None, :] - cx) * z_row[:, None] / f + lateral
    grass = np.array([62, 70, 54], np.float32) / 255
    asphalt = np.array([46, 47, 49], np.float32) / 255
    on_rwy = np.abs(Xg) < 22.5
    g = np.where(on_rwy[..., None], asphalt, grass)
    # longitudinal texture: subtle stripes in grass
    zabs = z_row[:, None] + travel
    tex = 0.92 + 0.08 * np.sin(Xg * 0.35 + np.sin(zabs * 0.05) * 2)
    g = g * tex[..., None]
    # markings: edge stripes & centreline dashes
    white = np.array([200, 202, 204], np.float32) / 255
    edge = (np.abs(np.abs(Xg) - 21.5) < 0.45)
    dash = (np.abs(Xg) < 0.45) & (np.mod(zabs, 50.0) < 30.0)
    g = np.where((edge | dash)[..., None], white * 0.85, g)
    fk = fogk[:, None, None]
    fc = np.array(fog_col, np.float32) / 255
    ground = g * (1 - fk) + fc * fk
    arr[below] = ground[below]
    # lights
    if edge_lights:
        sp = 60.0
        k0 = math.floor(travel / sp)
        for k in range(k0, k0 + 40):
            zz = k * sp - travel
            if zz < 4:
                continue
            for side in (-1, 1):
                X = side * 23.5 - lateral
                sx = cx + f * X / zz
                sy = hz + f * (cam_h - 0.4) / zz
                if -50 < sx < W + 50:
                    a = math.exp(-zz / (vis * 0.9)) * 1.1 * light_scale
                    r = max(1.2, 28 * 0.9 / zz * f / 60)
                    add_glow(arr, sx, sy, r * 1.4, (255, 214, 150), a)
    if oncoming:
        z = oncoming["z"]; xl = oncoming.get("x", 0.0) - lateral
        if z > 3:
            att = math.exp(-z / (vis * 1.15))
            sil = oncoming.get("sil", 1.0)
            if sil > 0:
                _front_747(arr, cx + f * xl / z, hz, z, f, cam_h, att, sil, fc, oncoming.get("pitch", 0.0))
            lights = oncoming.get("lights", 1.0)
            for (lx, lz, rr) in [(-4.6, 4.2, 1.0), (4.6, 4.2, 1.0), (0, 3.1, 0.7)]:
                sx = cx + f * (xl + lx) / z
                sy = hz + f * (cam_h - lz - oncoming.get("pitch", 0.0) * 0) / z
                r = max(2.5, f * 1.1 / z) * rr * oncoming.get("size", 1.0)
                add_glow(arr, sx, sy, r * 2.2, (255, 228, 190), lights * (0.25 + 1.6 * att ** 0.7))
                add_glow(arr, sx, sy, r * 9, (255, 220, 170), lights * 0.25 * att ** 0.4)
    if darkness:
        arr *= (1 - darkness)
    return arr


def _front_747(arr, sx, hz, z, f, cam_h, att, alpha, fc, pitch=0.0):
    """dark frontal silhouette of a 747 (fogged)."""
    im = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(im)
    k = f / z
    gy = hz + f * cam_h / z  # ground line at that distance
    def P(x, zz):
        return (sx + x * k, gy - zz * k)
    # fuselage
    d.ellipse([*P(-3.25, ZC + 3.4), *P(3.25, ZC - 3.25)], fill=255)
    d.ellipse([*P(-2.2, ZC + 4.8), *P(2.2, ZC + 1.6)], fill=255)
    # wings (dihedral)
    d.polygon([P(-2, ZC - 1.6), P(-29.8, ZC + 1.6), P(-29.8, ZC + 1.2), P(-2, ZC - 2.4)], fill=255)
    d.polygon([P(2, ZC - 1.6), P(29.8, ZC + 1.6), P(29.8, ZC + 1.2), P(2, ZC - 2.4)], fill=255)
    for ex, ez in [(-11.8, ZC - 2.9), (11.8, ZC - 2.9), (-21.2, ZC - 1.8), (21.2, ZC - 1.8)]:
        d.ellipse([*P(ex - 1.35, ez + 1.35), *P(ex + 1.35, ez - 1.35)], fill=255)
    # fin and stab
    d.polygon([P(-0.4, ZC + 3), P(0, 19.3), P(0.4, ZC + 3)], fill=255)
    d.polygon([P(-11, ZC + 2.2), P(11, ZC + 2.2), P(11, ZC + 1.8), P(-11, ZC + 1.8)], fill=255)
    # gear
    for gx in (-5.6, -1.9, 1.9, 5.6, 0):
        d.rectangle([*P(gx - 0.5, ZC - 2.6), *P(gx + 0.5, 0)], fill=255)
    m = np.asarray(im, np.float32)[..., None] / 255 * alpha * (0.15 + 0.85 * att)
    dark = np.array([0.16, 0.17, 0.19], np.float32) * (1 - att) + fc * (1 - att) * 0.0
    sil = fc * (1 - att) + np.array([0.12, 0.13, 0.15]) * att
    arr[:] = arr * (1 - m) + sil * m
