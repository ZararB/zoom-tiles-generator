/**
 * Stitch a rectangle of slippy tiles into one PNG (canvas).
 * Mirrors backend custom_map_tile_mosaic.build_tile_mosaic_png (simplified).
 */
import { fetchTilePng } from './basemap.js';

const TILE_PX = 256;
const MAX_DIM = 4096;

export async function buildMosaicPng(providerKey, z, centerX, centerY, radius = 1) {
  const minX = centerX - radius;
  const maxX = centerX + radius;
  const minY = centerY - radius;
  const maxY = centerY + radius;
  const gridW = maxX - minX + 1;
  const gridH = maxY - minY + 1;

  let tilePx = TILE_PX;
  let width = gridW * tilePx;
  let height = gridH * tilePx;
  if (width > MAX_DIM || height > MAX_DIM) {
    const scale = Math.min(MAX_DIM / width, MAX_DIM / height);
    tilePx = Math.max(64, Math.floor(TILE_PX * scale));
    width = gridW * tilePx;
    height = gridH * tilePx;
  }

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#1c2026';
  ctx.fillRect(0, 0, width, height);

  const layout = [];
  const n = 2 ** z;
  for (let ty = minY; ty <= maxY; ty += 1) {
    for (let tx = minX; tx <= maxX; tx += 1) {
      if (ty < 0 || ty >= n) continue;
      const wrappedX = ((tx % n) + n) % n;
      const blob = await fetchTilePng(providerKey, z, wrappedX, ty);
      const bmp = await createImageBitmap(blob);
      const dx = (tx - minX) * tilePx;
      const dy = (ty - minY) * tilePx;
      ctx.drawImage(bmp, 0, 0, bmp.width, bmp.height, dx, dy, tilePx, tilePx);
      bmp.close();
      layout.push({ z, x: tx, y: ty, dx, dy, w: tilePx, h: tilePx });
    }
  }

  const pngBlob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
  return { pngBlob, layout, minX, minY, gridW, gridH, tilePx };
}

export function canvasFromBlob(blob) {
  return new Promise(async (resolve, reject) => {
    try {
      const bmp = await createImageBitmap(blob);
      const c = document.createElement('canvas');
      c.width = bmp.width;
      c.height = bmp.height;
      c.getContext('2d').drawImage(bmp, 0, 0);
      resolve(c);
    } catch (e) {
      reject(e);
    }
  });
}
