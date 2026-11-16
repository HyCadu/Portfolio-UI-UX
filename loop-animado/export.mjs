// Exporta a animação quadro a quadro e monta o MP4.
// Uso: node export.mjs [pasta-de-quadros] [saida.mp4]   (requer playwright + ffmpeg)
// Para ver quadros soltos: ONLY=5.7,8.5 node export.mjs pasta   (tempos em segundos)
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright');   // resolve também instalação global (NODE_PATH)
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const dir = process.argv[2] || path.join(here, '.frames');
const out = process.argv[3] || path.join(here, 'loop-estudo-recompensa.mp4');
const FPS = 30, only = process.env.ONLY ? process.env.ONLY.split(',').map(Number) : null;
mkdirSync(dir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1080, height: 1080 }, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(path.join(here, 'index.html')).href + '?export');
await page.evaluate(() => window.ready);
const total = Math.round((await page.evaluate(() => window.DURATION)) * FPS);
const canvas = page.locator('#c');
for (const i of only ? only.map(s => Math.round(s * FPS)) : [...Array(total).keys()]) {
  await page.evaluate(t => window.renderAt(t), i / FPS);
  writeFileSync(path.join(dir, `f${String(i).padStart(4, '0')}.png`), await canvas.screenshot());
}
await browser.close();
if (!only) {
  const trilha = path.join(here, 'assets', 'trilha.m4a');     // gerada por gerar_trilha.py
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(FPS), '-i', path.join(dir, 'f%04d.png'),
    ...(existsSync(trilha) ? ['-i', trilha, '-c:a', 'copy', '-shortest'] : []), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '23', '-preset', 'slow', '-movflags', '+faststart', out]);
  console.log('ok', out);
}
