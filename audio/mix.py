"""Synthesised score + sound design + VO mix -> build/mix.wav"""
import json, os, subprocess, math
import numpy as np
from scipy import signal
from scipy.io import wavfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TL = json.load(open(os.path.join(ROOT, "build", "vo", "timeline.json")))
LN = {l["key"]: l for l in TL["lines"]}
st = lambda k: LN[k]["start"]
SR = 48000
END = LN["l8"]["end"] + 5.0
N = int(END * SR)
t = np.arange(N) / SR
rng = np.random.default_rng(7)


def env(points):
    """piecewise-linear envelope from [(time, value), ...]"""
    xs, ys = zip(*points)
    return np.interp(t, xs, ys).astype(np.float32)


def lp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), "low"); return signal.lfilter(b, a, x)


def bp(x, f1, f2, order=2):
    b, a = signal.butter(order, [f1 / (SR / 2), f2 / (SR / 2)], "band"); return signal.lfilter(b, a, x)


def hz(note):  # midi -> hz
    return 440 * 2 ** ((note - 69) / 12)


FLASH = st("x4") + 1.1
SIL0, SIL1 = FLASH + 0.4, st("x5") - 0.3

# ---------------- drone pad (D minor), slow movement
pad = np.zeros(N)
chords = [(0, [38, 45, 50, 53]), (st("w1"), [38, 45, 50, 53]), (st("c1"), [34, 41, 50, 53]), (st("m1"), [36, 43, 51, 55]),
          (st("x1"), [37, 44, 50, 56]), (st("x5"), [38, 45, 50, 53, 57]), (st("l3"), [34, 46, 50, 53, 58]), (st("l5"), [38, 45, 50, 54, 57])]
for i, (c0, notes) in enumerate(chords):
    c1 = chords[i + 1][0] if i + 1 < len(chords) else END
    m = ((t >= c0 - 1.5) & (t < c1 + 1.5))
    w = np.clip(np.minimum((t - (c0 - 1.5)) / 3, ((c1 + 1.5) - t) / 3), 0, 1) * m
    for n in notes:
        f = hz(n)
        for det in (-0.12, 0.0, 0.13):
            ph = 2 * np.pi * f * (1 + det / 100) * t + rng.random() * 6
            pad += w * (np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)) / len(notes)
pad = lp(pad, 900) * (0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t))
pad_env = env([(0, 0), (1.0, 0.5), (st("h4"), 0.55), (st("h5"), 0.75), (st("w1"), 0.5), (st("c5"), 0.6), (st("m1"), 0.55),
               (st("m6"), 0.8), (FLASH, 1.0), (SIL0, 0.0), (SIL1, 0.0), (st("x5"), 0.45), (st("l5"), 0.55), (st("l7"), 0.7), (END - 2.5, 0.6), (END, 0)])
pad *= pad_env * 0.16

# ---------------- low string swell / sub for tension
sub = np.sin(2 * np.pi * hz(26) * t) * env([(0, 0), (st("m3"), 0), (st("m6"), 0.5), (FLASH, 0.9), (SIL0, 0), (END, 0)]) * 0.18

# ---------------- pulses (heartbeat-like thumps)
pulse = np.zeros(N)
def thump(at, amp):
    i = int(at * SR); n = int(0.5 * SR)
    if i >= N: return
    n = min(n, N - i)
    tt = np.arange(n) / SR
    pulse[i:i + n] += amp * np.sin(2 * np.pi * (48 + 30 * np.exp(-tt * 25)) * tt) * np.exp(-tt * 9)
tc = st("h4");
while tc < st("h5") - 0.3:
    thump(tc, 0.5); tc += 60 / 66
tc = st("m3")
while tc < FLASH:
    k = (tc - st("m3")) / (FLASH - st("m3"))
    thump(tc, 0.35 + 0.45 * k); tc += 60 / (62 + 60 * k)

# ---------------- piano-like notes for the lesson/memorial
piano = np.zeros(N)
def note(at, n, amp=0.25):
    i = int(at * SR); L = int(3.5 * SR); L = min(L, N - i)
    if L <= 0: return
    tt = np.arange(L) / SR; f = hz(n)
    piano[i:i + L] += amp * (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(4 * np.pi * f * tt) * np.exp(-tt * 3)) * np.exp(-tt * 1.4) * np.minimum(1, tt * 200)
seq = [62, 65, 69, 67, 65, 64, 62, 60, 58, 62, 65, 64]
tc = st("x5") + 1.0; i = 0
while tc < END - 3:
    note(tc, seq[i % len(seq)], 0.16)
    if i % 4 == 0: note(tc, seq[i % len(seq)] - 24, 0.1)
    tc += 2.2; i += 1
note(0.25, 50, 0.2); note(0.25, 62, 0.15)

# ---------------- wind / fog ambience
noise = rng.standard_normal(N)
wind = lp(noise, 400) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t + 1))
wind *= env([(0, 0), (2.6, 0.5), (st("h5") - 0.5, 0.5), (st("h5"), 0.1), (st("w5"), 0.1), (st("w6"), 0.6), (st("m2") - 0.3, 0.6),
             (st("m2"), 0.0), (st("m6") - 0.3, 0.0), (st("m6"), 0.6), (SIL0, 0.6), (SIL0 + 0.01, 0), (st("l4"), 0), (st("l4") + 1, 0.35), (st("l5"), 0)]) * 0.5

# ---------------- jet engines (idle taxi + spool-up take-off roll)
jet_n = bp(noise, 150, 2500)
whine = sum(np.sin(2 * np.pi * f * t * (1 + 0.002 * np.sin(t))) for f in (1850, 2710)) * 0.02
eng_env = env([(0, 0), (st("h1"), 0.15), (st("h2") + 2, 0.15), (st("h3"), 0.0), (st("h4"), 0.3), (st("h5") - 0.5, 0.45), (st("h5"), 0),
               (st("c1"), 0), (st("c1") + 1, 0.15), (st("c2") - 0.5, 0.15), (st("c2"), 0), (st("m1") - 0.3, 0), (st("m1"), 0.18), (st("m2") - 0.3, 0.18), (st("m2"), 0),
               (st("m6") - 0.3, 0), (st("m6"), 0.5), (st("x1"), 0.75), (st("x1") + 0.1, 0.35), (FLASH - 1.5, 0.9), (FLASH, 1.0), (SIL0, 0.0)])
spool = env([(0, 1), (st("m6"), 1), (st("x1"), 1.6), (FLASH, 1.8)])
jet = (jet_n * 0.25 + whine * spool) * eng_env

# ---------------- radio static & heterodyne during transcripts
radio = np.zeros(N)
rad_env = env([(0, 0), (st("m2") - 0.2, 0), (st("m2"), 0.25), (st("m6") - 0.3, 0.25), (st("m6") - 0.2, 0)])
radio += bp(noise, 400, 3200) * rad_env * 0.12
crackle = (rng.random(N) > 0.9993) * rng.standard_normal(N) * 0.6
radio += bp(crackle, 500, 4000) * rad_env * 2
h0, h1 = st("m3") + 0.3, st("m3") + 4.0
hm = env([(0, 0), (h0, 0), (h0 + 0.2, 1), (h1 - 0.3, 1), (h1, 0), (END, 0)])
radio += (np.sin(2 * np.pi * 1740 * t) * np.sin(2 * np.pi * 1752 * t)) * hm * 0.05
for k in ("m2", "m3", "m4", "m5"):  # mic key clicks
    i = int((st(k) - 0.2) * SR); radio[i:i + 400] += rng.standard_normal(400) * 0.3

# ---------------- impact: muffled low boom then silence
boom = np.zeros(N)
i = int((FLASH - 0.15) * SR); L = int(2.0 * SR)
tt = np.arange(L) / SR
boom[i:i + L] = lp(rng.standard_normal(L), 160) * np.exp(-tt * 2.5) * 2.2 + np.sin(2 * np.pi * 38 * tt) * np.exp(-tt * 3) * 0.6

# ---------------- logo whoosh
wh = np.zeros(N); L = int(1.4 * SR); tt = np.arange(L) / SR
wh[:L] = bp(rng.standard_normal(L), 300, 3000) * np.sin(np.pi * tt / 1.4) ** 2 * 0.12

music = pad + sub + pulse * 0.6 + piano
sfx = wind + jet + radio + boom + wh

# ---------------- VO track
vo = np.zeros(N)
for l in TL["lines"]:
    sr, x = wavfile.read(l["wav"])
    x = x.astype(np.float32) / 32768
    i = int(l["start"] * SR)
    vo[i:i + len(x)] += x[: max(0, N - i)]
vo = vo / (np.abs(vo).max() + 1e-9) * 0.85
# ducking
ve = lp(np.abs(vo), 6)
duck = 1 - 0.45 * np.clip(ve / 0.05, 0, 1)
# hard silence window (dramatic pause)
sil = env([(0, 1), (SIL0 - 0.05, 1), (SIL0, 0), (SIL1, 0), (SIL1 + 0.8, 1), (END, 1)])
mix = vo + (music * 1.0 + sfx * 0.9) * duck * sil
mix = np.tanh(mix * 1.1) * 0.92
mix *= env([(0, 0), (0.05, 1), (END - 1.5, 1), (END, 0)])
out = os.path.join(ROOT, "build", "mix.wav")
wavfile.write(out, SR, (np.stack([mix, mix], 1) * 32767).astype(np.int16))
print("wrote", out, END)
