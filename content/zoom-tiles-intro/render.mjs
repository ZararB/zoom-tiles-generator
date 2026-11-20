import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdir, readFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.ZTILES_PLAYWRIGHT_CORE || 'playwright-core');
const output = resolve('artifacts/zoom-tiles-intro');
const filmUrl = 'http://127.0.0.1:8798/content/zoom-tiles-intro/?demo';
const explorerUrl = 'http://127.0.0.1:8796/world-explorer.html';
const story = JSON.parse(await readFile(new URL('./story.json', import.meta.url)));
const fps = 30;
const args = process.argv.slice(2);
const requested = args.filter(arg => arg !== '--reuse-demo');
for (const slug of requested) {
  if (!story.some(scene => scene.slug === slug)) throw new Error(`Unknown scene: ${slug}`);
}

await mkdir(resolve(output, 'demo-stills'), { recursive: true });
await mkdir(resolve(output, 'clips'), { recursive: true });

async function captureDemo(browser) {
  const page = await browser.newPage({ viewport: { width: 1340, height: 724 } });
  await page.addInitScript(() => {
    localStorage.setItem('zoom-world-auto', '0');
    localStorage.setItem('zoom-world-layer', 'original');
  });
  await page.goto(explorerUrl, { waitUntil: 'domcontentloaded' });
  const map = page.locator('#map');
  const ready = () => page.waitForFunction(() => {
    const { world, ready } = document.querySelector('#map').dataset;
    return world?.startsWith('world-') && ready === 'true';
  });
  const capture = async name => {
    await ready();
    await page.screenshot({ path: resolve(output, 'demo-stills', `${name}.jpg`), quality: 96 });
    console.log('World Explorer', name, await map.getAttribute('data-zoom'), await map.getAttribute('data-center'));
  };
  await page.locator('#science').click();
  await page.locator('#create').click();
  await page.waitForFunction(() => document.querySelector('#create-status').textContent.startsWith('Map ready.'));
  await capture('overview');
  const bounds = await map.boundingBox();
  await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);
  const initialZoom = Number(await map.getAttribute('data-zoom'));
  for (let step = 1; step <= 2; step++) {
    await page.mouse.wheel(0, -115);
    await page.waitForFunction(zoom => Math.abs(Number(document.querySelector('#map').dataset.zoom) - zoom) < .015,
      initialZoom + step * .25);
  }
  await capture('fields');
  await page.locator('#search').fill('Physics');
  await page.locator('#find').click();
  await page.waitForFunction(() => document.querySelector('#map').dataset.center === '[2048,768]');
  await capture('physics');
  await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);
  for (let step = 1; step <= 4; step++) {
    await page.mouse.wheel(0, -115);
    await page.waitForFunction(zoom => Number(document.querySelector('#map').dataset.zoom) === zoom, 3 + step * .25);
    await capture(`zoom-${step}`);
  }
  await page.locator('#search').fill('Mechanics');
  await page.locator('#find').click();
  await page.waitForFunction(() => document.querySelector('#map').dataset.center !== '[2048,768]');
  await capture('detail');
  await page.close();
}

async function recordScene(page, scene, offset) {
  const path = resolve(output, 'clips', `${scene.slug}.mp4`);
  const encoder = spawn('ffmpeg', [
    '-hide_banner', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps),
    '-c:v', 'mjpeg', '-i', 'pipe:0', '-vf', 'scale=in_range=full:out_range=limited:out_color_matrix=bt709',
    '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '16', '-pix_fmt', 'yuv420p',
    '-colorspace', 'bt709', '-color_trc', 'bt709', '-color_primaries', 'bt709',
    '-g', '30', '-movflags', '+faststart', path,
  ], { stdio: ['pipe', 'inherit', 'inherit'] });
  const finished = once(encoder, 'close');
  const frameCount = scene.duration * fps;
  try {
    for (let start = 0; start < frameCount; start += 10) {
      const frames = await page.evaluate(({ offset, start, end, fps }) => {
        const canvas = document.querySelector('#film');
        const batch = [];
        for (let frame = start; frame < end; frame++) {
          window.zoomTilesFilm.render(offset + frame / fps);
          batch.push(canvas.toDataURL('image/jpeg', .94).split(',')[1]);
        }
        return batch;
      }, { offset, start, end: Math.min(start + 10, frameCount), fps });
      for (const frame of frames) {
        if (!encoder.stdin.write(Buffer.from(frame, 'base64'))) await once(encoder.stdin, 'drain');
      }
    }
    encoder.stdin.end();
    const [status] = await finished;
    if (status !== 0) throw new Error(`FFmpeg failed for ${scene.slug} (${status})`);
  } catch (error) {
    encoder.kill();
    throw error;
  }
  console.log('Rendered', scene.slug, frameCount, 'frames');
}

const browser = await chromium.launch({
  executablePath: process.env.ZTILES_CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
});
try {
  if (!args.includes('--reuse-demo')) await captureDemo(browser);
  const page = await browser.newPage();
  page.on('pageerror', error => console.error('Film page:', error.message));
  await page.goto(filmUrl);
  await page.waitForFunction(() => document.querySelector('#film').dataset.scene === '01-hook');
  let offset = 0;
  for (const scene of story) {
    if (requested.length === 0 || requested.includes(scene.slug)) {
      await recordScene(page, scene, offset);
    }
    offset += scene.duration;
  }
} finally {
  await browser.close();
}
