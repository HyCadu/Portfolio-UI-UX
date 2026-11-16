"""Sintetiza a trilha do loop (16 s), sincronizada com a linha do tempo de index.html.
Uso: python3 gerar_trilha.py saida.wav"""
import sys, wave
import numpy as np

SR, T, TR = 44100, 16.0, 8.5
N = int(SR * T); t = np.arange(N) / SR
rng = np.random.default_rng(7)

# --- mesmas curvas da animação ---
PRESS  = [(0,.18),(3.4,.72),(6.6,1),(7.4,.9),(8.45,0),(15.3,0),(16,.18)]
RELIEF = [(0,0),(6.6,0),(8.0,.25),(8.6,1),(15.0,1),(15.8,0),(16,0)]
ORBIT  = [(0,0),(3.4,0),(4.7,1),(5.4,2),(6.0,3),(6.6,4),(7.1,5),(7.6,6),(8.05,7),(8.6,8),(10.0,8),(10.7,9),
          (11.6,9),(12.3,10),(13.0,10),(13.7,11),(15.25,11),(16,12)]
STRESS = [2.0, 3.6, 4.5, 5.2, 5.8, 6.4, 6.9]   # um por etapa do giro
WINS   = [9.1, 9.7, 10.3]
curve = lambda k: np.interp(t, *zip(*k))
P, R = curve(PRESS), curve(RELIEF)
ph = np.cumsum(0.85 + 2.5 * P) / SR
ph *= np.ceil(ph[-1]) / ph[-1]                      # nº inteiro de batidas, como no canvas
box = lambda x, s: np.convolve(x, np.ones(int(s * SR)) / int(s * SR), 'same')
vel = box(np.abs(np.gradient(curve(ORBIT), 1 / SR)), 0.18)

L, Rt = np.zeros(N), np.zeros(N)
def add(sig, at=0.0, gain=1.0, pan=0.0):            # pan -1 (esq) .. 1 (dir)
    i = int(at * SR); n = min(len(sig), N - i)
    if n <= 0: return
    L[i:i+n] += sig[:n] * gain * np.sqrt((1 - pan) / 2); Rt[i:i+n] += sig[:n] * gain * np.sqrt((1 + pan) / 2)
def band(x, lo, hi):                                # filtro passa-faixa por FFT
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0; return np.fft.irfft(X, len(x))
env = lambda n, a, d: np.minimum(np.arange(n) / (a * SR + 1), 1) * np.exp(-np.arange(n) / (d * SR))
def tone(f, dur, a=0.005, d=0.2, kind='sin'):
    n = int(dur * SR); x = 2 * np.pi * f * np.arange(n) / SR
    w = np.sin(x) if kind == 'sin' else np.sign(np.sin(x)) * 0.5 if kind == 'sq' else 2 / np.pi * np.arcsin(np.sin(x))
    return w * env(n, a, d)
noise = rng.standard_normal(N)

# 1) coração: tum-tum no mesmo relógio da vinheta e do ECG
def thump(f0):
    n = int(0.22 * SR); k = np.arange(n) / SR
    return np.sin(2 * np.pi * (f0 * k - 60 * k * k)) * env(n, 0.004, 0.055)
for off, f0, g in ((0.0, 62, 1.0), (0.28, 52, 0.7)):
    for b in np.flatnonzero(np.diff(np.floor(ph - off)) > 0):
        add(thump(f0), b / SR, g * (0.35 + 0.75 * P[b]))

# 2) tensão: drone grave dissonante + tom que sobe sem parar + chiado
drone = sum(np.sin(2 * np.pi * f * t + i) / (i + 1) for i, f in enumerate((55, 58.3, 110, 116.5, 164.8)))
drone *= (0.6 + 0.4 * np.sin(2 * np.pi * ph)) * P ** 1.4 * 0.22
rise_f = 180 * (1250 / 180) ** np.clip((t - 2.5) / (TR - 2.5), 0, 1)
riser = np.sin(2 * np.pi * np.cumsum(rise_f) / SR) + 0.5 * np.sin(2 * np.pi * np.cumsum(rise_f * 1.06) / SR)
riser *= np.clip((t - 2.5) / (TR - 2.5), 0, 1) ** 2 * (t < TR) * 0.11
hiss = band(noise, 3000, 9000) * P ** 3 * 0.10
add(drone, pan=-0.15); add(drone[::-1][::-1] * 0.9, pan=0.15); add(riser); add(hiss)

# 3) relógio acelerando e notificações chegando (à direita, onde aparecem)
tk, gap = 0.3, 0.5
while tk < 7.4:
    add(band(rng.standard_normal(900), 1800, 6000) * env(900, 0.0005, 0.006), tk, 0.5, -0.5)
    gap = max(0.11, gap * 0.955); tk += gap
for s in STRESS:
    add(np.concatenate([tone(988, 0.09, d=0.06, kind='sq'), tone(740, 0.16, d=0.07, kind='sq')]), s, 0.30, 0.6)

# 4) glitches no pico e vento do giro (segue a velocidade da órbita)
for g in np.arange(4.6, 8.3, 0.07):
    i = int(g * SR)
    if rng.random() < (P[i] - 0.55) * 1.3:
        n = int(rng.uniform(0.02, 0.07) * SR); hold = int(rng.integers(8, 40))
        add(np.repeat(rng.uniform(-1, 1, n // hold + 1), hold)[:n], g, 0.16, rng.uniform(-0.8, 0.8))
wind = band(noise, 250, 2600) * np.clip(vel / 1.8, 0, 1.2) ** 1.5 * 0.34
add(wind * (0.6 + 0.4 * np.sin(2 * np.pi * 0.9 * t)), pan=-0.3); add(np.roll(wind, 900) * (0.6 + 0.4 * np.cos(2 * np.pi * 0.9 * t)), pan=0.3)

# 5) a virada: tudo some por um instante, depois o impacto solta a pressão
duck = 1 - 0.85 * np.clip((t - (TR - 0.4)) / 0.35, 0, 1) * (t < TR)
L *= duck; Rt *= duck
n = int(2.2 * SR); k = np.arange(n) / SR
add(np.sin(2 * np.pi * (70 * k - 9 * k * k).clip(0)) * np.exp(-k / 0.45), TR, 0.9)          # grave
add(band(rng.standard_normal(n), 2500, 12000) * np.exp(-k / 0.5), TR, 0.30)                  # prato
whoosh = band(rng.standard_normal(int(0.9 * SR)), 400, 5000)
add(whoosh * np.linspace(0, 1, len(whoosh)) ** 3, TR - 0.9, 0.28)                            # sucção antes

# 6) alívio: acordes maiores abrindo (I–V–vi–IV) + arpejo chiptune + sininhos das conquistas
A = 220.0; st = lambda s: A * 2 ** (s / 12)
CHORDS = [(8.5, (0, 4, 7)), (10.5, (-5, -1, 2)), (12.5, (-3, 0, 4)), (14.5, (-7, -3, 0))]
for i, (c0, notes) in enumerate(CHORDS):
    c1 = CHORDS[i + 1][0] if i + 1 < len(CHORDS) else 15.9
    n = int((c1 - c0 + 0.6) * SR); k = np.arange(n) / SR
    e = np.minimum(k / 0.25, 1) * np.minimum((n / SR - k) / 0.6, 1)
    for j, s in enumerate(notes + (notes[0] + 12,)):
        f = st(s); pad = sum(np.sin(2 * np.pi * f * d * k) for d in (0.997, 1, 1.003)) + 0.3 * np.sin(2 * np.pi * 2 * f * k)
        add(pad * e, c0, 0.045, (j - 1.5) * 0.4)
    add(np.sin(2 * np.pi * st(notes[0] - 24) * k) * e, c0, 0.16)                              # baixo
    seq = [notes[0], notes[1], notes[2], notes[0] + 12, notes[2], notes[1] + 12, notes[0] + 12, notes[2]]
    step = 0
    while c0 + step * 0.25 < min(c1, 15.2) - 0.01:
        at = c0 + step * 0.25
        add(tone(st(seq[step % 8] + 12), 0.24, a=0.003, d=0.11, kind='sq'), at, 0.085, 0.35 if step % 2 else -0.35)
        add(tone(st(seq[step % 8] + 12), 0.24, a=0.003, d=0.11, kind='sq'), at + 0.19, 0.03, -0.35 if step % 2 else 0.35)  # eco
        step += 1
for s, semi in zip(WINS, (19, 24, 28)):
    add(tone(st(semi + 12), 0.9, d=0.22) + 0.4 * tone(st(semi + 24), 0.9, d=0.12), s, 0.17, -0.5)
# fecha o loop: fade do alívio já vem de R; aplica saída suave no fim para emendar no começo
tail = np.clip((T - t) / 0.25, 0, 1) * 0.35 + 0.65
fadein = np.clip(t / 0.05, 0, 1) * 0.35 + 0.65
mix = np.stack([L, Rt], 1) * (tail * fadein)[:, None]
mix = np.tanh(mix * 1.5) / np.tanh(1.5)
mix *= 0.89 / np.abs(mix).max()
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype('<i2').tobytes())
print('ok', sys.argv[1])
