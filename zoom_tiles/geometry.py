"""Validate and derive editable water, land and border GeoJSON. All state is local."""
import copy
import json
import math
import hashlib
from datetime import datetime, timezone
from shapely.geometry import shape, mapping, Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely import orient_polygons
from pyproj import Geod

geod=Geod(ellps='WGS84')


def normalize_geography(body):
    if not isinstance(body,dict): raise ValueError('Provide a geography document')
    features = body.get('features')
    if not isinstance(features,list) or len(features)>100:
        raise ValueError('Provide at most 100 geography features')
    if type(body.get('enabled',True)) is not bool:
        raise ValueError('enabled must be a boolean')
    cleaned=[]; ids=set(); shapes={}; count=0
    def check_coords(value,depth=0):
        nonlocal count
        if depth>4: raise ValueError('Coordinate nesting is too deep')
        if not isinstance(value,list): raise ValueError('Invalid coordinates')
        if value and isinstance(value[0],(int,float)):
            if len(value)!=2 or not all(type(v) in (int,float) and math.isfinite(v) for v in value): raise ValueError('Invalid coordinate pair')
            if not -180<=value[0]<=180 or not -85.05<=value[1]<=85.05: raise ValueError('Coordinate outside map bounds')
            count+=1
            if count>15000: raise ValueError('Geometry exceeds 15000 vertices')
        else:
            for item in value: check_coords(item,depth+1)
    for feature in features:
        if not isinstance(feature,dict) or not isinstance(feature.get('properties'),dict) or not isinstance(feature.get('geometry'),dict): raise ValueError('Invalid GeoJSON feature')
        ident=feature.get('id'); props=feature.get('properties',{}); geom=feature.get('geometry',{})
        if not isinstance(ident,str) or not ident or len(ident)>80 or ident in ids: raise ValueError('Each feature needs a unique ID')
        ids.add(ident)
        kind=props.get('kind'); raw_name=props.get('name','')
        if not isinstance(raw_name,str):raise ValueError('Feature name must be text')
        name=raw_name.strip()
        if kind not in {'water','land','border'} or not 1<=len(name)<=120: raise ValueError('Feature needs a kind and name')
        allowed={'LineString'} if kind=='border' else {'Polygon','MultiPolygon'}
        if geom.get('type') not in allowed: raise ValueError('Water/land must be polygons; borders must be lines')
        check_coords(geom.get('coordinates'))
        geometry=shape(geom)
        if geometry.is_empty or not geometry.is_valid: raise ValueError(f'{name}: geometry is empty or self-intersects')
        properties={'kind':kind,'name':name}
        if props.get('role')=='replacement-region' and kind=='land': properties['role']='replacement-region'
        if isinstance(props.get('source_lakes'),list): properties['source_lakes']=[str(s)[:40] for s in props['source_lakes'][:5]]
        cleaned.append({'type':'Feature','id':ident,'properties':properties,'geometry':mapping(geometry)})
        shapes[ident]=geometry
    # Baseline water supplies only newly exposed land. Never paint a rectangular
    # replacement region over unchanged roads, landcover, buildings or settlements.
    baseline=body.get('base_water_features',[])
    if baseline:
        baseline=normalize_geography({'features':baseline})['features']
        if any(f['properties']['kind']!='water' for f in baseline):
            raise ValueError('Baseline water must contain water polygons only')
    islands=[shapes[f['id']] for f in cleaned if f['properties']['kind']=='land' and f['properties'].get('role')!='replacement-region']
    land=unary_union(islands) if islands else Polygon()
    rendered=copy.deepcopy(cleaned); water=[]; water_owners=[]
    for f in rendered:
        if f['properties']['kind']=='water':
            geom=shapes[f['id']].difference(land)
            if geom.is_empty: raise ValueError('A land edit would erase an entire water body; delete the water feature instead')
            f['geometry']=mapping(geom); water.append(geom);water_owners.append((f,geom))
    merged=unary_union(water) if water else Polygon()
    reclaimed=unary_union([shape(f['geometry']) for f in baseline]).difference(merged) if baseline else Polygon()
    components=0 if merged.is_empty else len(merged.geoms) if isinstance(merged,MultiPolygon) else 1
    # Connected water is rendered as one polygon, so a drawn connector never leaves internal shorelines.
    rendered=[f for f in rendered if f['properties']['kind']!='water']
    if not reclaimed.is_empty:
        rendered.insert(0,{'type':'Feature','id':'reclaimed-lake-land',
            'properties':{'kind':'land','name':'Reclaimed lake land','role':'reclaimed-land'},
            'geometry':mapping(reclaimed)})
    used_ids=set()
    for index,component in enumerate(list(merged.geoms) if isinstance(merged,MultiPolygon) else [] if merged.is_empty else [merged]):
        owner,_=max(water_owners,key=lambda item:item[1].intersection(component).area)
        ident=owner['id'] if owner['id'] not in used_ids else f"{owner['id']}-part-{index}"
        used_ids.add(ident)
        rendered.append({'type':'Feature','id':ident,'properties':owner['properties'],'geometry':mapping(component)})
    # Labels use a guaranteed interior point, including after islands or shoreline edits.
    labels=[]
    for f in rendered:
        if f['properties']['kind']=='water':
            point=shape(f['geometry']).representative_point()
            labels.append({'type':'Feature','id':f['id'],'properties':f['properties'],'geometry':mapping(point)})
    digest=hashlib.sha256(json.dumps({'enabled':body.get('enabled',True),'features':cleaned,'base_water_features':baseline},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'version':1,'enabled':body.get('enabled',True),'scenario':str(body.get('scenario','custom'))[:80],
            'sha256':digest,
            'features':cleaned,'base_water_features':baseline,'render_features':rendered,'labels':labels,
            'summary':{'water_features':len(water),'connected_water_bodies':components,
                       'water_area_km2':round(abs(geod.geometry_area_perimeter(orient_polygons(merged))[0])/1e6,1) if not merged.is_empty else 0,
                       'area_method':'WGS84 geodesic',
                       'land_features':sum(f['properties']['kind']=='land' for f in cleaned),
                       'borders':sum(f['properties']['kind']=='border' for f in cleaned),
                       'vertices':count,'valid':True},
            'revision':datetime.now(timezone.utc).isoformat(),
            'provenance':body.get('provenance',{}) if isinstance(body.get('provenance',{}),dict) else {}}
