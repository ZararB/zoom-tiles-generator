import {
  canvas, ctx, C, textures, clamp, ease, mix, text, line, rounded,
  grid, projection,
} from '../../docs/animation-art.js';

const scenes = await (await fetch(new URL('./story.json', import.meta.url))).json();
const duration = scenes.reduce((total, scene) => total + scene.duration, 0);
const W = canvas.width;
const H = canvas.height;
const ramp = (time, start, end) => ease((time - start) / (end - start));
const card = '#101010';
const bridge = [.456, .484];
const demoImages = new Map();
const backdropImage = document.createElement('canvas');
backdropImage.width = W;
backdropImage.height = H;
const background = backdropImage.getContext('2d');
const glow = background.createRadialGradient(1335, 510, 0, 1335, 510, 800);
glow.addColorStop(0, '#2b1509');
glow.addColorStop(1, '#000000');
background.fillStyle = glow;
background.fillRect(0, 0, W, H);
background.fillStyle = '#ffffff12';
for (let x = 43; x < W; x += 43) {
  for (let y = 43; y < H; y += 43) background.fillRect(x, y, 2, 2);
}

function circle(x, y, radius, fill, stroke, width = 2) {
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.stroke(); }
}

function box(x, y, width, height, fill, border = C.line, radius = 14) {
  rounded(x, y, width, height, radius);
  ctx.fillStyle = fill;
  ctx.fill();
  if (border) { ctx.strokeStyle = border; ctx.lineWidth = 2; ctx.stroke(); }
}

function backdrop(time) {
  ctx.drawImage(backdropImage, 0, 0);
  line([84, 1000], [1836, 1000], C.line);
  line([84, 1000], [84 + 1752 * time / duration, 1000], C.orange, 3);
  text('zTiles', 84, 1044, 25, C.ink, 700);
  text('WHAT ARE ZOOM TILES?', 1836, 1044, 16, C.muted, 600, 'right');
}

function heading(kicker, headings, supporting, top = 276) {
  text(kicker, 84, top - 94, 23, C.orange, 700);
  headings.forEach((part, index) => {
    text(part, 84, top + index * 102, 89, index === 0 ? C.ink : C.orange, 700);
  });
  supporting.forEach((part, index) => {
    text(part, 88, top + headings.length * 102 + 12 + index * 45, 34, C.secondary);
  });
}

function pin(x, y, time) {
  circle(x, y, 19 + (time % 1.5) * 14, null, '#f9731670', 3);
  circle(x, y, 10, C.orange, '#000000', 4);
  circle(x, y, 3, C.ink);
}

function hook(time) {
  heading('THE MAP UNDER THE MAP', ['What are', 'zoom tiles?'], ['From region to street.']);
  const view = { x: 1340, y: 292 + 11 * Math.sin(time / 2), s: 510, tilt: .39 };
  grid(view, 1, 1);
  const point = projection(view, ...bridge);
  pin(...point, time);
  const split = ramp(time, 3.4, 5.4);
  if (split > 0) grid({ ...view, y: view.y + 96 * split }, 2, 1, { gap: 26 * split, alpha: split });
  if (time > 6.2) {
    const rise = ramp(time, 6.2, 8.3);
    grid({ ...view, y: view.y - 132 * rise, s: 410 }, 4, 2, { gap: 15 * rise, alpha: rise });
  }
}

function pyramid(time) {
  heading('THE TILE PYRAMID', ['A stack of', 'zoom levels.'], ['Each step doubles the grid', 'in both directions.'], 258);
  const rows = [
    { level: 0, cells: 1, y: 180, delay: 1.5, label: '01 tile' },
    { level: 1, cells: 2, y: 418, delay: 6.6, label: '04 tiles' },
    { level: 2, cells: 4, y: 656, delay: 9.3, label: '16 tiles' },
  ];
  rows.forEach(({ level, cells, y, delay, label }) => {
    const amount = ramp(time, delay, delay + 1.2);
    box(950, y, 860, 210, card, amount > .99 ? '#70401d' : C.line);
    text(`LEVEL ${level}`, 997, y + 70, 24, C.muted, 700);
    text(label, 997, y + 132, 44, amount > .99 ? C.orange : C.ink, 700);
    const view = { x: 1510, y: y + 31, s: 238, tilt: .32 };
    grid(view, cells, level, { gap: amount * 18, alpha: .16 + amount * .84 });
  });
}

function detail(time) {
  const settle = ramp(time, .8, 3.6);
  const closer = ramp(time, 6.7, 9.6);
  const blend = ramp(time, 3.25, 4.1);
  const final = ramp(time, 8.2, 9.1);
  heading('THE SAME COORDINATES', ['Same place.', 'More detail.'], ['Follow the bridge.', 'The streets resolve around it.'], 305);
  const left = 870;
  const top = 120;
  const side = 850;
  const range = mix(mix(1, .44, settle), .205, closer);
  const centerX = mix(.5, bridge[0], settle);
  const centerY = mix(.5, bridge[1], settle);
  const u = centerX - range / 2;
  const v = centerY - range / 2;
  box(left - 10, top - 10, side + 20, side + 20, card);
  ctx.save();
  rounded(left, top, side, side, 9);
  ctx.clip();
  [1, blend, final].forEach((alpha, level) => {
    ctx.globalAlpha = alpha;
    ctx.drawImage(textures[level], u * 1200, v * 1200, range * 1200, range * 1200, left, top, side, side);
  });
  ctx.globalAlpha = 1;
  for (let i = 1; i < 4; i++) {
    const shift = side * i / 4;
    line([left + shift, top], [left + shift, top + side], '#ffffff29', 1);
    line([left, top + shift], [left + side, top + shift], '#ffffff29', 1);
  }
  pin(left + (bridge[0] - u) / range * side, top + (bridge[1] - v) / range * side, time);
  ctx.restore();
  box(left + 20, top + 20, 208, 48, '#000000dd', null, 7);
  text(closer > .85 ? 'STREET' : settle > .85 ? 'DISTRICT' : 'REGION', left + 39, top + 52, 24, C.ink, 700);
}

function diagram(kind, x, y, amount) {
  const nodes = kind === 0
    ? [[.13,.52],[.32,.22],[.34,.72],[.56,.39],[.62,.8],[.81,.19],[.89,.56]]
    : kind === 1
      ? [[.12,.7],[.25,.42],[.42,.48],[.56,.18],[.64,.45],[.81,.36],[.9,.14]]
      : [[.13,.14],[.13,.68],[.38,.68],[.38,.36],[.68,.36],[.68,.76],[.87,.76]];
  const links = kind === 0 ? [[0,1],[0,2],[1,3],[2,3],[2,4],[3,5],[3,6],[4,6],[5,6]]
    : [[0,1],[1,2],[2,3],[2,4],[4,5],[5,6]];
  const coords = nodes.map(([u, v]) => [x + u * 458, y + v * 290]);
  ctx.save();
  ctx.globalAlpha = .24 + .76 * amount;
  if (kind === 1) {
    ctx.beginPath();
    ctx.moveTo(x + 5, y + 249);
    ctx.bezierCurveTo(x + 56, y - 80, x + 420, y + 318, x + 455, y + 168);
    ctx.strokeStyle = '#a3a3a350';
    ctx.lineWidth = 16;
    ctx.stroke();
  }
  if (kind === 2) {
    for (let i = 0; i < 19; i++) {
      const left = x + 28 + (i % 6) * 69;
      const top = y + 38 + Math.floor(i / 6) * 66;
      box(left, top, 34, 26, '#2a2a2a', null, 3);
    }
  }
  links.forEach(([a, b]) => line(coords[a], coords[b], kind === 0 ? '#a3a3a3' : '#f9731680', 4, kind === 1 ? [7, 9] : []));
  coords.forEach(([px, py], i) => circle(px, py, i === 3 ? 15 : 8, i === 3 ? C.orange : C.ink, '#111', 3));
  ctx.restore();
}

function beyondEarth(time) {
  text('WHAT CAN YOU MAP?', 90, 149, 23, C.orange, 700);
  text('Maps beyond Earth.', 82, 257, 96, C.ink, 700);
  const cards = [
    ['Knowledge maps', 'Science · history · the internet'],
    ['Imaginary worlds', 'A world like Middle-earth'],
    ['Game worlds', 'From the region to the block'],
  ];
  cards.forEach(([label, sub], i) => {
    const start = [3, 7, 8.8][i];
    const amount = ramp(time, start, start + 1);
    const x = 86 + i * 590;
    box(x, 356 + 22 * (1 - amount), 566, 510, card, amount > .9 ? '#70401d' : C.line);
    diagram(i, x + 54, 395, amount);
    text(label, x + 41, 765, 40, C.ink, 700);
    text(sub, x + 41, 814, 25, C.muted);
  });
}

function demo(time) {
  const key = time < 3.1 ? 'overview' : time < 7.2 ? 'fields' : time < 10.25 ? 'physics' : 'detail';
  text('zTiles WORLD EXPLORER', 85, 112, 22, C.orange, 700);
  text('Explore a map of science.', 82, 189, 70, C.ink, 700);
  const step = time >= 9.3 && time < 10.8 ? Math.min(4, 1 + Math.floor((time - 9.3) * 3)) : 0;
  const image = demoImages.get(step ? `zoom-${step}` : key);
  if (image) {
    ctx.save();
    rounded(86, 228, 1340, 724, 12);
    ctx.clip();
    ctx.drawImage(image, 86, 228, 1340, 724);
    ctx.restore();
    ctx.strokeStyle = '#404040';
    ctx.lineWidth = 2;
    rounded(86, 228, 1340, 724, 12);
    ctx.stroke();
  } else {
    box(86, 228, 1340, 724, card);
    text('Local capture goes here', 756, 593, 34, C.muted, 500, 'center');
  }
  const info = {
    overview: ['01', 'Overview', 'The full topic map'],
    fields: ['02', 'Main fields', 'Physics, chemistry, biology'],
    physics: ['03', 'Search: physics', 'Jump to a saved topic'],
    detail: ['04', 'Subfields', 'Explore mechanics'],
  }[key];
  text(info[0], 1481, 328, 29, C.orange, 700);
  text(info[1], 1478, 389, 43, C.ink, 700);
  text(info[2], 1481, 441, 25, C.muted);
  text('PROTOTYPE CAPTURE', 1481, 912, 19, C.muted, 700);
}

function outro(time) {
  const amount = ramp(time, 5.8, 8.2);
  heading('zTiles', ['What would', 'you map?'], ['Start with the big picture.', 'Follow what interests you.'], 235);
  const views = [0, 1, 2].map(i => ({ x: 1335, y: 598 - 134 * i + 8 * Math.sin(time + i * .6), s: 476 - i * 100, tilt: .24 }));
  views.forEach((view, i) => grid(view, 2 ** i, i, { gap: 14 + 18 * amount, highlight: i > 0 ? [1, 0] : null }));
  for (let i = 0; i < 2; i++) {
    const a = projection(views[i], .5, .5);
    const b = projection(views[i + 1], .5, .5);
    line(a, b, C.orange, 3, [4, 10]);
    circle(...b, 6, C.orange);
  }
}

const drawScenes = [hook, pyramid, detail, beyondEarth, demo, outro];

function render(second) {
  const position = clamp(second, 0, duration - 1 / 30);
  let local = position;
  let index = 0;
  while (local >= scenes[index].duration) local -= scenes[index++].duration;
  backdrop(position);
  drawScenes[index](local);
  canvas.dataset.scene = scenes[index].slug;
}

async function setDemoImages(sources) {
  for (const [name, url] of Object.entries(sources)) {
    const image = new Image();
    image.src = url;
    await image.decode();
    demoImages.set(name, image);
  }
}

window.zoomTilesFilm = { render, setDemoImages };
const slider = document.querySelector('#position');
const clock = document.querySelector('#clock');
const play = document.querySelector('#play');
let playback = null;
slider.max = duration;
slider.value = 0;

function preview(second) {
  slider.value = second;
  clock.value = `${second.toFixed(1)} / ${duration}s`;
  render(second);
}
slider.oninput = () => {
  cancelAnimationFrame(playback);
  playback = null;
  play.textContent = 'Play';
  preview(Number(slider.value));
};
play.onclick = () => {
  if (playback !== null) {
    slider.oninput();
    return;
  }
  const start = performance.now() - (Number(slider.value) >= duration ? 0 : Number(slider.value)) * 1000;
  play.textContent = 'Pause';
  function frame(now) {
    const second = Math.min(duration, (now - start) / 1000);
    preview(second);
    if (second < duration) playback = requestAnimationFrame(frame);
    else { playback = null; play.textContent = 'Play'; }
  }
  playback = requestAnimationFrame(frame);
};

const imageNames = ['overview', 'fields', 'physics', 'zoom-1', 'zoom-2', 'zoom-3', 'zoom-4', 'detail'];
if (new URLSearchParams(location.search).has('demo')) {
  await setDemoImages(Object.fromEntries(imageNames.map(name => [
    name, `../../artifacts/zoom-tiles-intro/demo-stills/${name}.jpg`,
  ])));
}
preview(0);
