import json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance, ImageOps

S = sys.argv[1]
OUT = sys.argv[2]
D, V, W = f"{S}/drive", f"{S}/vo", f"{S}/work"
os.makedirs(W, exist_ok=True)
WID, HEI, FPS = 1080, 1920, 30
XF = 0.4  # crossfade seconds

INTER = "/usr/share/fonts/opentype/inter/"
def font(name, size): return ImageFont.truetype(INTER + name, size)
BLACK = "InterDisplay-Black.otf"; XB = "Inter-ExtraBold.otf"; SB = "Inter-SemiBold.otf"; MED = "Inter-Medium.otf"
ORANGE = (242, 140, 40); RED = (205, 40, 40); WHITE = (245, 245, 245); GREY = (190, 195, 205)

IMG = {
    "poster": "f_1kQb37lv0hCQAoH4pV2fHhjVqHY7J0uyn",
    "logo": "f_1mbpm6JlGgw10Ca7asA_29gNWhSq0Iid3",
    "ground": "f_1_IyfuldJGeXZc_0HrsIsJ1baBgnI3NGM",
    "crash": "f_12d5ajZy8bsu6gJ2_avxv-2E4LejezBBy",
    "news_en": "f_1lC6QrfRRKNqzzyDw2IVj7Kfa7bJ9aA1j",
    "news_ms": "f_1oHpJCYLTJZee55ksG2sCYSK-5-JmXVxM",
    "flight": "f_1QjoY2J9x-R65m9dSf6eGVvVmJaaBcnFm",
    "subang": "f_1Ye6tifT2wuFmIvfeU_daWoJy-zaSFYhO",
}
CROP = {  # remove phone UI bars / Google Lens badge
    "ground": (0, 40, 1079, 555),
    "news_en": (0, 10, 1079, 1000),
    "news_ms": (0, 25, 1079, 915),
}
def load(k):
    im = Image.open(f"{D}/{IMG[k]}").convert("RGB")
    return im.crop(CROP[k]) if k in CROP else im

def tracked(draw, xy, text, f, fill, spacing, anchor_center=True):
    widths = [draw.textlength(c, font=f) for c in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x = xy[0] - total / 2 if anchor_center else xy[0]
    for c, w in zip(text, widths):
        draw.text((x, xy[1]), c, font=f, fill=fill); x += w + spacing

def header(d):
    tracked(d, (WID / 2, 120), "NABIL AVIATION", font(XB, 34), WHITE, 9)
    d.line((WID/2 - 230, 178, WID/2 + 230, 178), fill=ORANGE, width=3)
    tracked(d, (WID / 2, 196), "AIR DISASTER CHRONICLES  ·  EPISODE 01", font(SB, 24), GREY, 4)

def vignette(im, strength=0.75):
    mask = Image.new("L", (WID, HEI), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse((-300, -200, WID + 300, HEI + 200), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(220))
    dark = Image.new("RGB", (WID, HEI), (5, 8, 15))
    return Image.composite(im, Image.blend(im, dark, strength), mask)

def framed(k, label=None, sub=None, gray=False, fg_w=1000, cy=820, max_h=1050):
    src = load(k)
    if gray: src = ImageOps.grayscale(src).convert("RGB")
    bg = ImageOps.fit(src, (WID, HEI)).filter(ImageFilter.GaussianBlur(40))
    bg = ImageEnhance.Brightness(bg).enhance(0.35)
    fg = src.resize((fg_w, round(src.height * fg_w / src.width)), Image.LANCZOS)
    if fg.height > max_h:
        fg = src.resize((round(src.width * max_h / src.height), max_h), Image.LANCZOS)
    x, y = (WID - fg.width) // 2, cy - fg.height // 2
    shadow = Image.new("RGBA", (WID, HEI), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle((x + 10, y + 16, x + fg.width + 10, y + fg.height + 16), fill=(0, 0, 0, 200))
    bg = Image.alpha_composite(bg.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(18))).convert("RGB")
    bg.paste(fg, (x, y))
    d = ImageDraw.Draw(bg)
    d.rectangle((x, y + fg.height, x + fg.width, y + fg.height + 6), fill=ORANGE)
    bg = vignette(bg, 0.45)
    d = ImageDraw.Draw(bg)
    header(d)
    if label:
        f = font(BLACK, 58)
        tw = d.textlength(label, font=f)
        d.text(((WID - tw) / 2, y - 120), label, font=f, fill=WHITE)
    if sub:
        tracked(d, (WID / 2, y - 48), sub, font(SB, 28), ORANGE, 5)
    return bg

def altitude_card(state):
    bg = ImageOps.fit(load("crash"), (WID, HEI)).filter(ImageFilter.GaussianBlur(30))
    bg = ImageEnhance.Brightness(ImageOps.grayscale(bg).convert("RGB")).enhance(0.25)
    bg = vignette(bg, 0.5)
    d = ImageDraw.Draw(bg)
    header(d)
    tracked(d, (WID / 2, 420), "ARAHAN MENARA KAWALAN", font(XB, 34), ORANGE, 6)
    f_big = font(BLACK, 180)
    t = "2,400 FT"
    tw = d.textlength(t, font=f_big)
    col = WHITE if state == 0 else (110, 110, 115)
    d.text(((WID - tw) / 2, 500), t, font=f_big, fill=col)
    q = "“...descend two four zero zero...”"
    fq = font(MED, 38)
    d.text(((WID - d.textlength(q, font=fq)) / 2, 760), q, font=fq, fill=GREY)
    if state == 1:
        d.line(((WID - tw) / 2 - 10, 605, (WID + tw) / 2 + 10, 605), fill=RED, width=14)
        tracked(d, (WID / 2, 900), "DIFAHAMI SEBAGAI", font(XB, 34), RED, 6)
        t2 = "400 FT"
        d.text(((WID - d.textlength(t2, font=f_big)) / 2, 980), t2, font=f_big, fill=RED)
        q2 = "“...to four zero zero...”"
        d.text(((WID - d.textlength(q2, font=fq)) / 2, 1240), q2, font=fq, fill=GREY)
    return bg

def poster():
    p = load("poster")
    return ImageOps.fit(p, (WID, HEI), centering=(0.5, 0.45))

def logo_card():
    bg = Image.new("RGB", (WID, HEI), (6, 10, 20))
    glow = Image.new("RGB", (WID, HEI), (6, 10, 20))
    ImageDraw.Draw(glow).ellipse((140, 420, 940, 1220), fill=(60, 40, 20))
    bg = glow.filter(ImageFilter.GaussianBlur(160))
    lg = load("logo")
    # circular crop of the badge
    s = 1000; cx, cy = 645, 590
    lg = lg.crop((cx - 520, cy - 520, cx + 520, cy + 520)).resize((760, 760), Image.LANCZOS)
    m = Image.new("L", (760, 760), 0); ImageDraw.Draw(m).ellipse((8, 8, 752, 752), fill=255)
    bg.paste(lg, (160, 400), m)
    d = ImageDraw.Draw(bg)
    tracked(d, (WID / 2, 1240), "LEARNING FROM", font(XB, 46), WHITE, 10)
    tracked(d, (WID / 2, 1305), "AVIATION HISTORY.", font(XB, 46), WHITE, 10)
    d.line((WID/2 - 260, 1395, WID/2 + 260, 1395), fill=ORANGE, width=4)
    tracked(d, (WID / 2, 1420), "AIR DISASTER CHRONICLES  ·  EP 01", font(SB, 26), GREY, 4)
    return bg

# ---------- audio timeline ----------
order = ["h1", "h2", "f1", "a1", "a2", "a3", "m1", "c1", "c2"]
gap_before = {"h1": 0.4, "h2": 0.45, "f1": 0.65, "a1": 0.65, "a2": 0.5, "a3": 0.5, "m1": 0.75, "c1": 0.75, "c2": 0.8}
words, start = {}, {}
t = 0.0
for k in order:
    w = json.load(open(f"{V}/{k}.json"))
    t += gap_before[k]
    start[k] = t - w[0][0]           # file offset in timeline
    words[k] = [(a + start[k], b + start[k], x) for a, b, x in w]
    t = words[k][-1][1]
TOTAL = round(t + 1.9, 2)
print("total", TOTAL)
def ws(k, i): return words[k][i][0]

# ---------- scenes: (image, start time) ----------
scene_imgs = {
    "poster": poster(),
    "flight": framed("flight", "19 FEBRUARY 1989", "SINGAPURA  →  KUALA LUMPUR  →  HONG KONG"),
    "ground": framed("ground", "FLIGHT 66", "BOEING 747-249F  ·  N807FT"),
    "subang": framed("subang", "SUBANG", "LAPANGAN TERBANG SUBANG  ·  RUNWAY 33", gray=True),
    "alt0": altitude_card(0),
    "alt1": altitude_card(1),
    "crash": framed("crash", "PUCHONG", "KAWASAN BERBUKIT  ·  AWAL PAGI", fg_w=1040),
    "news_ms": framed("news_ms", "4 NYAWA", "TERKORBAN", fg_w=1040, max_h=860, cy=860),
    "news_en": framed("news_en", "4 NYAWA", "TERKORBAN", fg_w=1040, max_h=860, cy=860),
    "closing": framed("flight", None, "SETIAP ARAHAN · SETIAP PERKATAAN", gray=True),
    "logo": logo_card(),
}
timeline = [
    ("poster", 0.0),
    ("flight", ws("f1", 0) - 0.5),
    ("ground", ws("f1", 22) - 0.2),          # "dengan pendaftaran..."
    ("subang", ws("a1", 0) - 0.5),
    ("alt0", ws("a2", 0) - 0.3),
    ("alt1", ws("a2", 9) - 0.15),            # "telah disalahertikan"
    ("crash", ws("a3", 0) - 0.4),
    ("news_ms", ws("m1", 0) - 0.5),
    ("news_en", ws("m1", 5) - 0.1),          # "mengorbankan"
    ("closing", ws("c1", 0) - 0.5),
    ("logo", ws("c2", 0) - 0.6),
]
clips = []
for i, (name, st) in enumerate(timeline):
    en = timeline[i + 1][1] if i + 1 < len(timeline) else TOTAL
    dur = en - st + (XF if i + 1 < len(timeline) else 0)
    png = f"{W}/{i:02d}_{name}.png"
    scene_imgs[name].save(png)
    mp4 = f"{W}/{i:02d}_{name}.mp4"
    zoom_in = name not in ("alt0", "alt1")
    z = f"(1+0.07*t/{dur:.3f})" if zoom_in else "1.0"
    if name.startswith("alt"):
        z = f"(1.04-0.04*t/{dur:.3f})"
    vf = (f"scale=2160:3840,zoompan=z='{z.replace('t', 'in/' + str(FPS))}':"
          f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={WID}x{HEI}:fps={FPS},format=yuv420p")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", str(FPS), "-i", png,
                    "-t", f"{dur:.3f}", "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", mp4], check=True)
    clips.append((mp4, st, dur))
    print("clip", name, round(st, 2), round(dur, 2))

# ---------- subtitles (ASS) ----------
chunks = {
    "h1": [("Korang tahu tak...", 3), ("Malaysia pernah menjadi lokasi satu tragedi", 6),
           ("melibatkan sebuah pesawat jumbo jet", 5), ("Boeing 747", 4),
           ("yang terhempas ketika menghampiri", 4), ("Lapangan Terbang Subang?", 3)],
    "h2": [("Kejadian ini berlaku", 3), ("pada tahun 1989.", 7)],
    "f1": [("Pada 19 Februari 1989,", 9), ("Flying Tiger Line Flight 66,", 5), ("sebuah Boeing 747-200F,", 8),
           ("dengan pendaftaran N807FT,", 8), ("sedang dalam perjalanan dari Singapura", 5),
           ("menuju ke Kuala Lumpur,", 4), ("sebelum meneruskan penerbangan ke Hong Kong.", 6)],
    "a1": [("Ketika menghampiri Subang", 3), ("untuk mendarat di Runway 33,", 6),
           ("berlaku salah faham komunikasi", 4), ("antara juruterbang dan menara kawalan trafik udara.", 7)],
    "a2": [("Arahan untuk turun ke 2,400 kaki...", 9), ("telah disalahertikan sebagai 400 kaki.", 6)],
    "a3": [("Pesawat terus menurun...", 3), ("dan akhirnya melanggar kawasan berbukit", 5), ("berhampiran Puchong.", 2)],
    "m1": [("Tragedi pada awal pagi itu...", 5), ("mengorbankan kesemua empat individu", 4), ("di dalam pesawat tersebut.", 4)],
    "c1": [("Tragedi ini mengingatkan kita bahawa", 5), ("dalam dunia penerbangan,", 3),
           ("setiap arahan, dan setiap perkataan,", 5), ("membawa makna.", 2)],
    "c2": [("Nabil Aviation.", 2), ("Learning from aviation history.", 4)],
}
def ts(x):
    h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return f"{h}:{m:02d}:{s:05.2f}"
events = []
for k in order[:-1]:  # c2 tagline is shown on the end card
    i = 0
    assert sum(n for _, n in chunks[k]) == len(words[k]), (k, len(words[k]))
    for j, (txt, n) in enumerate(chunks[k]):
        a = words[k][i][0]; b = words[k][i + n - 1][1]
        nxt = words[k][i + n][0] if i + n < len(words[k]) else b + 0.5
        events.append((a, min(nxt, b + 0.6), txt)); i += n
ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {WID}
PlayResY: {HEI}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Inter ExtraBold,66,&H00FFFFFF,&H00FFFFFF,&H8C000000,&H8C000000,0,0,0,0,100,100,0,0,3,14,0,2,90,90,430,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
for a, b, txt in events:
    ass += f"Dialogue: 0,{ts(a)},{ts(b)},Sub,,0,0,0,,{{\\fad(80,80)}}{txt}\n"
open(f"{W}/subs.ass", "w", encoding="utf-8").write(ass)

# ---------- audio mix ----------
inputs, filt = [], []
for n, k in enumerate(order):
    inputs += ["-i", f"{V}/{k}.mp3"]
    filt.append(f"[{n}:a]adelay={int(start[k]*1000)}|{int(start[k]*1000)},apad[v{n}]")
filt.append("".join(f"[v{n}]" for n in range(len(order))) +
            f"amix=inputs={len(order)}:normalize=0,atrim=0:{TOTAL},"
            "equalizer=f=140:t=q:w=1:g=3,acompressor=threshold=-20dB:ratio=3:attack=10:release=200,"
            "loudnorm=I=-15:TP=-1.5:LRA=9[voice]")
# ambient drone bed
filt.append(f"aevalsrc='0.5*sin(2*PI*55*t)*(0.6+0.4*sin(2*PI*0.07*t))+0.35*sin(2*PI*82.4*t)*(0.6+0.4*sin(2*PI*0.05*t+1))+0.2*sin(2*PI*110.3*t)':s=48000:d={TOTAL},"
            f"lowpass=f=400,volume=0.05,afade=t=in:d=2,afade=t=out:st={TOTAL-3}:d=3[bed]")
filt.append(f"anoisesrc=c=pink:a=0.02:d={TOTAL}:r=48000,lowpass=f=900,highpass=f=80,afade=t=in:d=2,afade=t=out:st={TOTAL-3}:d=3[air]")
filt.append("[voice][bed][air]amix=inputs=3:normalize=0,alimiter=limit=0.89[aout]")
subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filt),
                "-map", "[aout]", "-ar", "48000", "-c:a", "pcm_s16le", f"{W}/mix.wav"], check=True)

# ---------- video assembly ----------
inp, fc = [], []
for mp4, _, _ in clips: inp += ["-i", mp4]
prev = "[0:v]"
for n in range(1, len(clips)):
    off = clips[n][1]
    fc.append(f"{prev}[{n}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[x{n}]")
    prev = f"[x{n}]"
fc.append(f"{prev}subtitles={W}/subs.ass:fontsdir={INTER},fade=t=in:d=0.6,fade=t=out:st={TOTAL-1.0}:d=1.0,format=yuv420p[vout]")
subprocess.run(["ffmpeg", "-y", "-v", "error", *inp, "-i", f"{W}/mix.wav", "-filter_complex", ";".join(fc),
                "-map", "[vout]", "-map", f"{len(clips)}:a", "-t", str(TOTAL),
                "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-profile:v", "high", "-r", str(FPS),
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", OUT], check=True)
json.dump({"total": TOTAL, "events": events}, open(f"{W}/timing.json", "w"), ensure_ascii=False, indent=1)
print("done", OUT)
