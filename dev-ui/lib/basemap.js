/**
 * Public raster templates (dev only). Prod uses backend proxy + optional CARTO keys.
 */
export const BASEMAP = {
  carto_dark: {
    label: 'CARTO dark',
    leaflet: 'https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
    url: (z, x, y) =>
      `https://basemaps.cartocdn.com/dark_all/${z}/${x}/${y}.png`,
    attribution: '&copy; CARTO, OSM',
  },
  carto_light: {
    label: 'CARTO light',
    leaflet: 'https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
    url: (z, x, y) =>
      `https://basemaps.cartocdn.com/light_all/${z}/${x}/${y}.png`,
    attribution: '&copy; CARTO, OSM',
  },
  osm: {
    label: 'OSM',
    leaflet: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    url: (z, x, y) => `https://tile.openstreetmap.org/${z}/${x}/${y}.png`,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  },
};

export function basemapUrl(providerKey, z, x, y) {
  const p = BASEMAP[providerKey] || BASEMAP.carto_dark;
  return p.url(z, x, y);
}

export async function fetchTilePng(providerKey, z, x, y,options={}) {
  if (providerKey === 'vector') {
    const { renderVectorTile } = await import('./map-names.js');
    return renderVectorTile(z, x, y,options);
  }
  const url = basemapUrl(providerKey, z, x, y);
  const res = await fetch(url,options);
  if (!res.ok) throw new Error(`basemap ${res.status} ${url}`);
  return res.blob();
}

export function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result;
      const b64 = String(dataUrl).split(',')[1];
      resolve(b64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}
