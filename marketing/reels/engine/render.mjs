// Render a reel script (JSON) to a 1080x1920 MP4.
//   node marketing/reels/engine/render.mjs marketing/reels/scripts/01-empty-fridge.json
// Optional: add "audio": "path/to/voiceover.m4a" in the JSON (relative to the JSON file) to mux a voiceover.
// Needs: Node 18+, `npm i playwright` (+ `npx playwright install chromium`), and ffmpeg on your PATH.
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const scriptPath = process.argv[2];
if (!scriptPath) { console.error('usage: node render.mjs <script.json> [--fps 30] [--preview]'); process.exit(1); }
const fps = Number(process.argv[process.argv.indexOf('--fps') + 1]) || 30;
const preview = process.argv.includes('--preview'); // stills only, fast
const cfg = JSON.parse(fs.readFileSync(scriptPath, 'utf8'));
const name = cfg.name || path.basename(scriptPath, '.json');
const outDir = path.resolve(here, '..', 'out');
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(path.join(here, 'reel.html')).href);
await page.evaluate(() => document.fonts.ready);
const total = await page.evaluate(c => window.loadReel(c), cfg);
const frames = Math.ceil(total * fps);
console.log(`${name}: ${total.toFixed(1)}s, ${frames} frames`);

if (preview) {
  // 8 evenly spaced stills for a quick look before a full render
  for (let k = 1; k <= 8; k++) {
    const tt = (total * k) / 9;
    await page.evaluate(x => window.seek(x), tt);
    await page.screenshot({ path: path.join(outDir, `${name}-preview-${k}.jpg`), type: 'jpeg', quality: 80 });
  }
  await browser.close();
  console.log('previews written to', outDir);
  process.exit(0);
}

const out = path.join(outDir, `${name}.mp4`);
const args = ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-'];
if (cfg.audio) args.push('-i', path.resolve(path.dirname(scriptPath), cfg.audio));
args.push('-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart');
if (cfg.audio) args.push('-c:a', 'aac', '-b:a', '192k', '-shortest');
args.push(out);
const ff = spawn('ffmpeg', args, { stdio: ['pipe', 'inherit', 'inherit'] });

for (let f = 0; f < frames; f++) {
  await page.evaluate(x => window.seek(x), f / fps);
  const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
  if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  if (f % fps === 0) process.stdout.write(`\r  ${Math.round((f / frames) * 100)}%`);
}
ff.stdin.end();
await new Promise(r => ff.on('close', r));

// Voiced build (from voice.py): mix voiceover clips + music (ducked under the voice) + whooshes on cuts
if (cfg.voiceBuild) {
  const dir = path.resolve(path.dirname(scriptPath), cfg.voiceBuild);
  const starts = await page.evaluate(() => window.__starts);
  const VO_LEAD = 0.2;
  const inputs = ['-i', out, '-i', path.join(dir, 'music.wav')];
  const f = [`[1:a]atrim=0:${total.toFixed(2)},afade=t=out:st=${(total - 1.5).toFixed(2)}:d=1.5,volume=${cfg.musicVolume ?? 0.22}[mus]`];
  const voLabels = [], fxLabels = [];
  cfg.scenes.forEach((s, i) => {
    if (!s.vo) return;
    inputs.push('-i', path.join(dir, s.vo.file));
    const k = inputs.length / 2 - 1;
    f.push(`[${k}:a]adelay=${Math.round((starts[i] + VO_LEAD) * 1000)}:all=1[v${i}]`); voLabels.push(`[v${i}]`);
  });
  starts.slice(1).forEach((st, i) => {
    inputs.push('-i', path.join(dir, 'whoosh.wav'));
    const k = inputs.length / 2 - 1;
    f.push(`[${k}:a]adelay=${Math.max(0, Math.round((st - 0.3) * 1000))}:all=1,volume=0.35[w${i}]`); fxLabels.push(`[w${i}]`);
  });
  f.push(`${voLabels.join('')}amix=inputs=${voLabels.length}:normalize=0,asplit[vo][key]`);
  f.push(`[mus][key]sidechaincompress=threshold=0.02:ratio=5:attack=15:release=350[duck]`);
  f.push(`[vo][duck]${fxLabels.join('')}amix=inputs=${2 + fxLabels.length}:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]`);
  const voiced = out.replace(/\.mp4$/, '.voiced.mp4');
  await new Promise((res, rej) => spawn('ffmpeg', ['-y', '-loglevel', 'error', ...inputs, '-filter_complex', f.join(';'),
    '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-t', total.toFixed(2), voiced],
    { stdio: 'inherit' }).on('close', c => c ? rej(new Error('audio mix failed')) : res()));
  fs.renameSync(voiced, out);
}

// cover image = a frame from the hook (used as the reel thumbnail)
await page.evaluate(x => window.seek(x), cfg.coverAt ?? 1.6);
await page.screenshot({ path: path.join(outDir, `${name}-cover.jpg`), type: 'jpeg', quality: 90 });
await browser.close();
console.log(`\r  done → ${path.relative(process.cwd(), out)}`);
