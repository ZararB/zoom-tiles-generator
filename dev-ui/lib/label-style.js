// This transformation edits symbol text only. Sources, geometry, fills and lines are untouched.
export const ORIGINAL_LAKE_NAME = 'Lake Ontario';
export const LABEL_SOURCE = 'custom-lake-name';
export const LABEL_LAYER = 'custom-lake-name-label';
const aliases = ['lake ontario', 'lac ontario'];
const nameKeys = ['name_en', 'name:en', 'name', 'name:latin'];

export function renamedStyle(base, state) {
  const style = structuredClone(base);
  if (!state.enabled) return style;
  const matchesOntario = ['any', ...nameKeys.map(key =>
    ['in', ['downcase', ['to-string', ['coalesce', ['get', key], '']]], ['literal', aliases]])];
  for (const layer of style.layers) {
    if (layer.type === 'symbol' && layer['source-layer'] === 'water_name' && layer.layout?.['text-field']) {
      layer.layout['text-field'] = ['case', matchesOntario, '', layer.layout['text-field']];
    }
  }
  style.sources[LABEL_SOURCE] = {type:'geojson', data:{type:'FeatureCollection', features:[{
    type:'Feature', id:'lake-ontario', properties:{name:state.lake_name},
    geometry:{type:'Point',coordinates:[-77.9,43.77]},
  }]}};
  style.layers.push({id:LABEL_LAYER, type:'symbol', source:LABEL_SOURCE,
    layout:{'text-field':['get','name'], 'text-font':['Noto Sans Italic'],
      'text-size':['interpolate',['linear'],['zoom'],0,10,5,13,9,17],
      'text-letter-spacing':.1, 'text-max-width':10, 'text-allow-overlap':true,
      'text-ignore-placement':true},
    paint:{'text-color':'#495e91','text-halo-color':'rgba(255,255,255,0.85)','text-halo-width':1.5}});
  return style;
}

export function geometrySignature(style) {
  const ordered = value => Array.isArray(value) ? value.map(ordered) : value && typeof value === 'object'
    ? Object.fromEntries(Object.keys(value).sort().filter(key =>
      !(['layout','paint'].includes(key) && value[key] && Object.keys(value[key]).length === 0))
      .map(key => [key, ordered(value[key])])) : value;
  const sources = Object.fromEntries(Object.entries(style.sources).filter(([id]) => id !== LABEL_SOURCE));
  return JSON.stringify(ordered({sources, layers: style.layers.filter(layer => layer.type !== 'symbol')}));
}
