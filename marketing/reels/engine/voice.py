"""Generate the voiceover + music for a reel script, then hand off to render.mjs.

    python3 engine/voice.py scripts/01-empty-fridge.json            # voice + music + render
    python3 engine/voice.py scripts/01-empty-fridge.json --voice am_michael

Uses Kokoro (free, runs offline). One-time setup:
    pip install kokoro-onnx soundfile numpy
    download kokoro-v1.0.onnx and voices-v1.0.bin from
    https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0  into  marketing/reels/models/
"""
import json, os, re, subprocess, sys
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SR = 24000
GAP = 0.18  # silence between a headline and each spoken list item


def clean(text):
    return re.sub(r"\*", "", text).strip()


def tts(k, text, voice, speed):
    audio, sr = k.create(text, voice=voice, speed=speed, lang="en-us")
    assert sr == SR
    # trim leading/trailing silence so timings are tight
    idx = np.where(np.abs(audio) > 0.01)[0]
    return audio[max(0, idx[0] - 240): idx[-1] + 2400] if len(idx) else audio


# ---------------- music: a light, upbeat kitchen groove (synthesised, royalty-free) ----------------
def music(seconds, bpm=104, seed=7):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    out = np.zeros(n + SR * 2)
    beat = 60 / bpm
    t_note = lambda d: np.arange(int(d * SR)) / SR
    midi = lambda m: 440 * 2 ** ((m - 69) / 12)

    def keys(freq, dur, vol):  # soft electric piano
        t = t_note(dur)
        env = np.exp(-t * 3.2) * (1 - np.exp(-t * 200))
        w = np.sin(2 * np.pi * freq * t) + .35 * np.sin(4 * np.pi * freq * t) * np.exp(-t * 6) + .12 * np.sin(6 * np.pi * freq * t) * np.exp(-t * 9)
        return vol * env * w

    def add(sig, at):
        i = int(at * SR)
        if i >= len(out):
            return
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i]

    prog = [[60, 64, 67, 71], [57, 60, 64, 67], [53, 57, 60, 64], [55, 59, 62, 65]]  # Cmaj7 Am7 Fmaj7 G7
    bass = [36, 33, 29, 31]
    bar = beat * 4
    t, b = 0.0, 0
    while t < seconds + bar:
        ch = prog[b % 4]
        for k in range(8):  # eighth-note arpeggio
            note = ch[[0, 1, 2, 3, 2, 1, 2, 3][k]] + (12 if k in (3, 7) else 0)
            add(keys(midi(note), beat * 1.2, .055), t + k * beat / 2)
        for k in (0, 2.5):  # stab chords
            for m in ch:
                add(keys(midi(m), beat * 1.5, .03), t + k * beat)
        bt = t_note(bar)
        add(.16 * np.sin(2 * np.pi * midi(bass[b % 4]) * bt) * np.exp(-bt * 1.2) * (1 - np.exp(-bt * 80)), t)
        for k in range(4):  # kick on every beat
            kt = t_note(.3)
            add(.42 * np.sin(2 * np.pi * (50 + 90 * np.exp(-kt * 30)) * kt) * np.exp(-kt * 14), t + k * beat)
        for k in range(8):  # hats
            ht = t_note(.06)
            add((.05 if k % 2 else .025) * rng.standard_normal(len(ht)) * np.exp(-ht * 70), t + k * beat / 2)
        for k in (1, 3):  # clap
            ct = t_note(.18)
            add(.10 * rng.standard_normal(len(ct)) * np.exp(-ct * 25), t + k * beat)
        t += bar
        b += 1
    out = out[:n]
    fade = int(1.5 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    out[: int(.3 * SR)] *= np.linspace(0, 1, int(.3 * SR))
    return (out / (np.abs(out).max() + 1e-9) * .9).astype(np.float32)


def whoosh():
    t = np.arange(int(.45 * SR)) / SR
    noise = np.random.default_rng(3).standard_normal(len(t))
    # crude band-pass sweep: smooth the noise with a moving average whose width shrinks over time
    sig = np.convolve(noise, np.ones(12) / 12, mode="same") - np.convolve(noise, np.ones(80) / 80, mode="same")
    env = np.sin(np.pi * t / t[-1]) ** 2
    return (.5 * sig * env / np.abs(sig).max()).astype(np.float32)


def main():
    args = sys.argv[1:]
    script = args[0]
    voice = args[args.index("--voice") + 1] if "--voice" in args else None
    from kokoro_onnx import Kokoro
    models = os.environ.get("KOKORO_DIR", os.path.join(ROOT, "models"))
    k = Kokoro(os.path.join(models, "kokoro-v1.0.onnx"), os.path.join(models, "voices-v1.0.bin"))

    cfg = json.load(open(script))
    voice = voice or cfg.get("voice", "af_heart")
    speed = cfg.get("speed", 1.08)
    name = os.path.splitext(os.path.basename(script))[0]
    build = os.path.join(ROOT, "build", name)
    os.makedirs(build, exist_ok=True)

    for i, s in enumerate(cfg["scenes"]):
        parts = [tts(k, clean(s.get("speak", s.get("say", ""))), voice, speed)]
        vo = {"say": len(parts[0]) / SR, "items": []}
        # steps / recipes: speak each item so it can pop in exactly when it's said
        if s.get("visual") in ("steps", "recipes", "fridge") and s.get("speakItems", True):
            t = vo["say"]
            for it in s["items"]:
                label = it[0] if s["visual"] == "steps" else it[1]
                if s["visual"] == "fridge":
                    label += "."
                t += GAP
                vo["items"].append(round(t, 3))
                a = tts(k, label, voice, speed)
                parts += [np.zeros(int(GAP * SR), np.float32), a]
                t += len(a) / SR
        clip = np.concatenate(parts)
        vo["dur"] = round(len(clip) / SR, 3)
        vo["say"] = round(vo["say"], 3)
        vo["file"] = f"vo-{i:02d}.wav"
        sf.write(os.path.join(build, vo["file"]), clip, SR)
        s["vo"] = vo
        print(f"  scene {i + 1}: {vo['dur']:.1f}s  {clean(s.get('say', ''))}")

    sf.write(os.path.join(build, "music.wav"), music(90), SR)
    sf.write(os.path.join(build, "whoosh.wav"), whoosh(), SR)
    cfg["voiceBuild"] = "."
    cfg["name"] = name
    out = os.path.join(build, "script.json")
    json.dump(cfg, open(out, "w"), indent=2, ensure_ascii=False)
    if "--no-render" not in args:
        subprocess.run(["node", os.path.join(HERE, "render.mjs"), out], check=True)


if __name__ == "__main__":
    main()
