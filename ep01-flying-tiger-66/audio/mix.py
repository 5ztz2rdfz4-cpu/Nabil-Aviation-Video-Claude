"""Synthesised score + sound design + VO mix -> build/mix.wav (adapted from the Tenerife episode)."""
import json, os
import numpy as np
from scipy import signal
from scipy.io import wavfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TL = json.load(open(os.path.join(ROOT, "build", "vo", "timeline.json")))
LN = {l["key"]: l for l in TL["lines"]}
st = lambda k: LN[k]["start"]
wd = lambda k, i: LN[k]["words"][i][0]
SR = 48000
END = TL["end"]
N = int(END * SR)
t = np.arange(N) / SR
rng = np.random.default_rng(7)
env = lambda pts: np.interp(t, *zip(*pts)).astype(np.float32)
def lp(x, fc): b, a = signal.butter(2, fc / (SR / 2), "low"); return signal.lfilter(b, a, x)
def bp(x, f1, f2): b, a = signal.butter(2, [f1 / (SR / 2), f2 / (SR / 2)], "band"); return signal.lfilter(b, a, x)
hz = lambda n: 440 * 2 ** ((n - 69) / 12)

IMPACT = wd("a3", 9) + 0.55
SIL0, SIL1 = IMPACT + 0.5, st("m1") - 0.4

pad = np.zeros(N)
chords = [(0, [38, 45, 50, 53]), (st("f1"), [34, 41, 50, 53]), (st("a1"), [36, 43, 51, 55]), (st("a3"), [37, 44, 50, 56]),
          (st("m1"), [38, 45, 50, 53, 57]), (st("c1"), [34, 46, 50, 53, 58]), (st("c2"), [38, 45, 50, 54, 57])]
for i, (c0, notes) in enumerate(chords):
    c1 = chords[i + 1][0] if i + 1 < len(chords) else END
    w = np.clip(np.minimum((t - (c0 - 1.5)) / 3, ((c1 + 1.5) - t) / 3), 0, 1)
    for n in notes:
        for det in (-0.12, 0.0, 0.13):
            ph = 2 * np.pi * hz(n) * (1 + det / 100) * t + rng.random() * 6
            pad += w * (np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)) / len(notes)
pad = lp(pad, 900) * (0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t))
pad *= env([(0, 0), (0.8, 0.55), (st("a1"), 0.6), (st("a3"), 0.8), (IMPACT, 1.0), (SIL0, 0), (SIL1, 0), (st("m1"), 0.45),
            (st("c1"), 0.6), (END - 2.5, 0.6), (END, 0)]) * 0.16
sub = np.sin(2 * np.pi * hz(26) * t) * env([(0, 0), (st("a2"), 0), (st("a3"), 0.5), (IMPACT, 0.9), (SIL0, 0), (END, 0)]) * 0.18

pulse = np.zeros(N)
def thump(at, amp):
    i = int(at * SR); n = min(int(0.5 * SR), N - i)
    if n <= 0: return
    tt = np.arange(n) / SR
    pulse[i:i + n] += amp * np.sin(2 * np.pi * (48 + 30 * np.exp(-tt * 25)) * tt) * np.exp(-tt * 9)
tc = st("a2")
while tc < IMPACT:
    k = (tc - st("a2")) / (IMPACT - st("a2")); thump(tc, 0.35 + 0.45 * k); tc += 60 / (62 + 60 * k)
thump(0.3, 0.6)

piano = np.zeros(N)
def note(at, n, amp):
    i = int(at * SR); L = min(int(3.5 * SR), N - i)
    if L <= 0: return
    tt = np.arange(L) / SR; f = hz(n)
    piano[i:i + L] += amp * (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(4 * np.pi * f * tt) * np.exp(-tt * 3)) * np.exp(-tt * 1.4) * np.minimum(1, tt * 200)
seq = [62, 65, 69, 67, 65, 64, 62, 60, 58, 62, 65, 64]
tc = st("m1"); i = 0
while tc < END - 3:
    note(tc, seq[i % 12], 0.16)
    if i % 4 == 0: note(tc, seq[i % 12] - 24, 0.1)
    tc += 2.2; i += 1

noise = rng.standard_normal(N)
wind = lp(noise, 400) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t + 1)) * env(
    [(0, 0.2), (st("a1"), 0.3), (st("a3"), 0.6), (SIL0, 0.6), (SIL0 + 0.01, 0), (st("c1"), 0), (st("c1") + 1, 0.3), (END, 0)]) * 0.5
jet_n = bp(noise, 150, 2500)
whine = sum(np.sin(2 * np.pi * f * t) for f in (1850, 2710)) * 0.02
jet = (jet_n * 0.25 + whine) * env([(0, 0), (wd("h1", 9), 0), (wd("h1", 9) + 0.5, 0.35), (st("h2"), 0.3), (st("h2") + 1, 0.12),
                                    (st("f1"), 0.12), (st("a1"), 0.2), (st("a3"), 0.4), (IMPACT, 0.7), (SIL0, 0)])
radio = np.zeros(N)
r0, r1 = wd("a1", 9) - 0.2, st("a2") + 0.3
re = env([(0, 0), (r0, 0), (r0 + 0.2, 0.25), (r1, 0.25), (r1 + 0.2, 0)])
radio += bp(noise, 400, 3200) * re * 0.12
radio += bp((rng.random(N) > 0.9993) * rng.standard_normal(N) * 0.6, 500, 4000) * re * 2
for at in (r0 + 0.2, r0 + 2.0):
    i = int(at * SR); radio[i:i + 400] += rng.standard_normal(400) * 0.3
boom = np.zeros(N)
i = int((IMPACT - 0.1) * SR); L = int(2.0 * SR); tt = np.arange(L) / SR
boom[i:i + L] = lp(rng.standard_normal(L), 160) * np.exp(-tt * 2.5) * 2.2 + np.sin(2 * np.pi * 38 * tt) * np.exp(-tt * 3) * 0.6

music = pad + sub + pulse * 0.6 + piano
sfx = wind + jet + radio + boom
vo = np.zeros(N)
for l in TL["lines"]:
    sr, x = wavfile.read(l["wav"]); x = x.astype(np.float32) / 32768
    i = int(l["offset"] * SR); vo[i:i + len(x)] += x[:max(0, N - i)]
vo = vo / (np.abs(vo).max() + 1e-9) * 0.85
duck = 1 - 0.45 * np.clip(lp(np.abs(vo), 6) / 0.05, 0, 1)
sil = env([(0, 1), (SIL0 - 0.05, 1), (SIL0, 0), (SIL1, 0), (SIL1 + 0.8, 1), (END, 1)])
mix = np.tanh((vo + (music + sfx * 0.9) * duck * sil) * 1.1) * 0.92
mix *= env([(0, 0), (0.05, 1), (END - 1.5, 1), (END, 0)])
out = os.path.join(ROOT, "build", "mix.wav")
wavfile.write(out, SR, (np.stack([mix, mix], 1) * 32767).astype(np.int16))
print("wrote", out, END)
