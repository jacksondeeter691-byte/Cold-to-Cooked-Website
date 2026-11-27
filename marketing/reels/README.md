# Reel maker: how to make a new reel

Free replacement for ReelFactory. You write one script file and run one command, and you get a 1080×1920 MP4 plus a cover image in `out/`.

## One-time setup (Mac)

```bash
brew install ffmpeg node
cd marketing/reels
npm install
npx playwright install chromium
```

## Make a reel

1. Copy a script: `cp scripts/01-empty-fridge.json scripts/04-leftover-rice.json`
2. Edit the words (see the format below). Use a question from `../PLAYBOOK.md`.
3. Check the stills: `node engine/render.mjs scripts/04-leftover-rice.json --preview`
4. Render it with voice + music: `python3 engine/voice.py scripts/04-leftover-rice.json` (or silent: `node engine/render.mjs scripts/04-leftover-rice.json`). This writes `out/04-leftover-rice.mp4` and `out/04-leftover-rice-cover.jpg` in under a minute.

Shortcut: ask Claude Code *"make a Cold-to-Cooked reel answering: what do I do with leftover rice?"* and it can write the script and render it for you.

## Script format

```jsonc
{
  "caption": "text for the post",
  "wordGap": 0.3,               // seconds between caption words (lower = faster)
  "audio": "vo/04.m4a",         // optional voiceover, muxed in automatically
  "scenes": [
    { "chapter": "the problem", "visual": "bigtext", "emoji": "🧊", "say": "Your fridge isn't *empty.*" }
  ]
}
```

- `say`: the caption, revealed word by word. Wrap words in `*stars*` to make them gold italic.
- `chapter`: the label on the pill at the top. Scenes that share a chapter share a pill.
- `minDur` / `dur` / `hold`: how long the scene stays on screen.

| visual | extra fields |
|---|---|
| `bigtext` | `emoji`: the hook screen |
| `fridge` | `items`: `[["🥚","Eggs"], …]` (up to 8) |
| `steps` | `items`: `[["Title","subtitle"], …]` (up to 4) |
| `recipes` | `items`: `[["🍳","Name","15 min","390 kcal"], …]` (up to 3) |
| `phone` | `photo` emojis, `tags`: `[["🥚","Eggs"], …]` (up to 6), `ready` text |
| `counter` | `to`, `label`, optional `prefix` / `suffix` |
| `cta` | `keyword`: the word people comment |

## Voiceover + music (one command)

`engine/voice.py` reads the script out loud with a free AI voice (Kokoro, runs on your computer). It times every caption word and list item to the voice, adds a royalty-free background beat that ducks under the voice, adds a whoosh on each cut, and renders the final MP4.

One-time setup:

```bash
pip install kokoro-onnx soundfile numpy
mkdir -p marketing/reels/models && cd marketing/reels/models
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -L -o voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

Make a voiced reel:

```bash
python3 engine/voice.py scripts/01-empty-fridge.json
```

- `"voice": "af_heart"` in the script picks the voice. Other good ones: `af_bella`, `af_nicole`, `am_michael`, `am_adam`, `bf_emma`. You can also pass `--voice am_michael`.
- `"speak": "..."` on a scene changes how a line is *said* without changing the caption. Use it for words the voice reads wrong, such as `COOK` → `cook` and `AI` → `A.I.`.
- In `steps`, `recipes` and `fridge` scenes, each item is read aloud and pops in as it's said.
- `"musicVolume": 0.22` sets how loud the beat is.

Prefer your own voice? Record yourself reading the captions, put the file in `vo/`, add `"audio": "../vo/04.m4a"` to the script, and run `render.mjs` instead.

## Live preview while editing

```bash
npx serve marketing/reels
```

Then open `http://localhost:3000/engine/reel.html?script=../scripts/01-empty-fridge.json`.
