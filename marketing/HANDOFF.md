# Handoff: Cold-to-Cooked marketing reels

## What's been done (branch `claude/zen-galileo-6vmkl6`)

- **Method:** taken from a ReelFactory Instagram reel and applied to Cold-to-Cooked (an iOS app: snap your fridge and get AI recipes, plus a health tracker, meal scanner, barcode scanner and meal planner). Reels are question-led and answer-first. Each one gives away a useful tip, shows the app as the shortcut, and ends with "Comment KEYWORD and I'll send you the app" (auto-DM through ManyChat). Full plan is in `marketing/PLAYBOOK.md`, including 30 reel questions and the posting schedule.
- **Free reel maker** in `marketing/reels/` (our own replacement for ReelFactory):
  - `engine/reel.html`: animated scenes (bigtext, fridge, steps, recipes, phone, counter, cta) with word-timed captions, chapter pills, and the app's colors (#0E0E0E background, #EDB821 gold).
  - `engine/render.mjs`: renders a script JSON to a 1080×1920 MP4 with Playwright and ffmpeg. It also mixes in audio when the script was built by voice.py.
  - `engine/voice.py`: Kokoro AI voiceover (free, runs offline, voice `af_heart`). It times captions and items to the speech, adds a synthesized music bed that ducks under the voice plus transition whooshes, then calls render.mjs.
  - `scripts/*.json`: one file per reel. `"speak"` overrides pronunciation without changing the caption (e.g. COOK → "cook").
- **Finished reels with voice and music:** `out/01-empty-fridge.mp4`, `out/02-food-waste.mp4`, `out/03-protein.mp4`, each with a `-cover.jpg`. Titles and captions are in each script's `title` and `caption` fields.
- **Profile pictures:** `marketing/brand/profile-picture*.png` (3 options).

## Setup on a Mac (one time)

```bash
brew install ffmpeg node python
cd marketing/reels && npm install && npx playwright install chromium
pip3 install kokoro-onnx soundfile numpy
mkdir -p models && cd models
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -L -o voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

Make a reel: `cd marketing/reels && python3 engine/voice.py scripts/<name>.json`

## Next up

- Make reels #4 onward from the question list in `PLAYBOOK.md`. Copy a script, change the words, render, and check the stills with `--preview`.
- Possibly swap the voice, or swap the profile picture for the real App Store icon.
- Captions for every new reel. On YouTube, use "link in profile" instead of "comment".
