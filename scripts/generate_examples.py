"""Build reproducible, fictional map edits and validate their measurable effects."""
from __future__ import annotations
import copy
import hashlib
import json
import sys
import time
from pathlib import Path
from shapely.geometry import Point, LineString, Polygon, GeometryCollection, box, mapping, shape
from shapely.affinity import scale
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from zoom_tiles import normalize_geography

def feature(ident,kind,name,geometry):
    return {'type':'Feature','id':ident,'properties':{'kind':kind,'name':name},'geometry':mapping(geometry)}

def lake(ident,name,x,y,rx=.25,ry=.18):
    return feature(ident,'water',name,scale(Point(x,y).buffer(1,quad_segs=24),rx,ry))

def document(features,baseline=None):
    return {'version':1,'enabled':True,'features':features,'base_water_features':baseline or [],
        'provenance':{'method':'deterministic_geospatial_example','fictional':True}}

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf-8')

def build_cases():
    cases=[]
    def add(ident,title,description,before,after,expected,assertion,prompt):
        cases.append({'id':ident,'title':title,'description':description,'before':before,'after':after,
            'expected':expected,'assertion':assertion,'prompt':prompt})
    original=json.loads((ROOT/'dev-ui/scenarios/great-lakes-original.geojson').read_text(encoding='utf-8'))
    base=[{**f,'id':'original-'+f['properties']['name_en'].lower(),
        'properties':{'kind':'water','name':f['properties']['name']}} for f in original['features']]
    ontario=copy.deepcopy(next(f for f in base if f['properties']['name']=='Lake Ontario'))
    renamed=copy.deepcopy(ontario);renamed['properties']['name']='Lake America'
    add('rename-only','Lake Ontario to Lake America','Only the name changes; editable shoreline coordinates stay identical.',
        document([ontario],[ontario]),document([renamed],[ontario]),[1,1],'name_only',
        'Apply a restrained atlas style. Preserve every shoreline and road; do not redraw text.')
    scene=json.loads((ROOT/'dev-ui/scenarios/great-lakes-two.json').read_text(encoding='utf-8'))
    add('great-lakes-merge','Five Great Lakes into two','Five named outlines become two expanded water bodies. Michigan and Huron already connect in the source geometry.',
        document(base,base),scene,[4,2],'larger_water',
        'Style this fictional map with crisp atlas shading. Preserve the two saved lake boundaries and surrounding detail.')
    left=lake('west-reservoir','Western Reservoir',-4.5,40.2,.22,.15)
    right=lake('east-reservoir','Eastern Reservoir',-3.9,40.2,.22,.15)
    canal=feature('canal','water','Connecting Canal',LineString([(-4.5,40.2),(-3.9,40.2)]).buffer(.035))
    add('reservoir-canal','Join reservoirs with a canal','A narrow water connector removes the internal shorelines and joins two reservoirs.',
        document([left,right]),document([left,right,canal]),[2,1],'one_rendered_shoreline',
        'Draw a detailed topographic map. Preserve the reservoir connector and existing road locations.')
    pond=lake('island-lake','Island Lake',24.4,-24.5,.45,.33)
    islands=[feature('island-'+str(i),'land','Island '+str(i),Point(24.18+i*.2,-24.5).buffer(.055)) for i in range(3)]
    add('three-islands','Carve three islands','Three land polygons cut real holes in one lake without replacing the source water feature.',
        document([pond]),document([pond,*islands]),[1,1],'three_holes',
        'Use subtle green terrain texture. Keep all three islands and their exact coastlines.')
    wide=lake('receding-lake','Receding Lake',-112,36,.42,.3)
    smaller={**wide,'geometry':mapping(shape(wide['geometry']).buffer(-.09))}
    add('lake-recession','Shrink a reservoir','Reclaimed land is confined to the old water footprint; nearby detail remains untouched.',
        document([wide],[wide]),document([smaller],[wide]),[1,1],'reclaimed_land',
        'Show dry exposed lakebed texture and an atlas-style shoreline. Preserve geometry and nearby roads.')
    small=lake('flood-lake','Flood Lake',-90.3,34.1,.12,.09)
    flood=lake('flood-lake','Flood Lake',-90.3,34.1,.4,.3)
    add('flood-expansion','Expand a floodplain lake','Water expands over low ground; unaffected terrain and settlements retain their map detail.',
        document([small],[small]),document([flood],[small]),[1,1],'larger_water',
        'Create a readable floodplain map with muted terrain. Keep the saved flooded area exact.')
    sea=lake('inland-sea','Inland Sea',134,-25,.6,.35)
    bridge=feature('land-bridge','land','New Land Bridge',box(133.95,-25.5,134.05,-24.5))
    add('inland-sea-split','Divide an inland sea','A land bridge splits one editable water feature into two connected water components.',
        document([sea]),document([sea,bridge]),[1,2],'split_components',
        'Render a clean desert atlas. Preserve the land bridge and the two separated water components.')
    bay=feature('bay','water','Fictional Bay',box(3.3,51.5,4.2,52.1))
    peninsula=feature('headland','land','New Headland',Polygon([(3.3,51.65),(3.8,51.75),(3.85,51.85),(3.3,51.95),(3.3,51.65)]))
    add('coastal-headland','Extend a coastal headland','A land polygon attached to the west bank narrows a bay and creates a new shoreline.',
        document([bay]),document([bay,peninsula]),[1,1],'less_water',
        'Use light coastal terrain shading. Preserve the headland, bay mouth and exact coastline.')
    water=lake('border-lake','Boundary Lake',-98,49,.3,.18)
    border=feature('district-border','border','Fictional District Boundary',LineString([(-98.6,48.7),(-98,49),(-97.4,49.3)]))
    moved=feature('district-border','border','Fictional District Boundary',LineString([(-98.6,48.7),(-98.1,49.25),(-97.4,49.3)]))
    add('border-relocation','Move a district border','Only the fictional border moves; both saved and derived water geometry remain unchanged.',
        document([water,border]),document([water,moved]),[1,1],'border_only',
        'Use a neutral reference-map style. Preserve the water and render the saved boundary clearly.')
    bend=feature('river','water','Meandering River',LineString([(90,23.5),(90.12,23.6),(90,23.72),(90.14,23.84),(90.1,23.95)]).buffer(.025))
    straight=feature('river','water','Reshaped River',LineString([(90,23.5),(90.04,23.7),(90.1,23.95)]).buffer(.025))
    add('river-reshaping','Reshape a river bend','A revised river corridor exposes the old bends and keeps the remaining surroundings detailed.',
        document([bend],[bend]),document([straight],[bend]),[1,1],'changed_shoreline',
        'Create a detailed river atlas. Preserve the new channel position and all unchanged map features.')
    invalid=copy.deepcopy(document([water]));invalid['features'][0]['geometry']={'type':'Polygon','coordinates':[[[-98.2,48.8],[-97.8,49.2],[-98.2,49.2],[-97.8,48.8],[-98.2,48.8]]]}
    add('invalid-bowtie','Reject a crossing shoreline','A self-intersecting polygon is rejected; the current saved map must stay unchanged.',
        document([water]),invalid,[1,None],'reject_invalid',
        'This input must be rejected before generation.')
    # Match the JSON coordinate arrays received by the HTTP/API boundary.
    return json.loads(json.dumps(cases))

def validate_case(case):
    before=normalize_geography(case['before'])
    try:after=normalize_geography(case['after'])
    except ValueError as exc:
        assert case['assertion']=='reject_invalid'
        return {'status':'passed','expected_rejection':True,'error':str(exc),'before_summary':before['summary']}
    assert case['assertion']!='reject_invalid'
    actual=[before['summary']['connected_water_bodies'],after['summary']['connected_water_bodies']]
    assert actual==case['expected'],(case['id'],actual,case['expected'])
    source_water=lambda d:[f['geometry'] for f in d['features'] if f['properties']['kind']=='water']
    rendered_water=lambda d:[shape(f['geometry']) for f in d['render_features'] if f['properties']['kind']=='water']
    kind=case['assertion']
    if kind in ['name_only','border_only','three_holes']:assert source_water(before)==source_water(after)
    if kind=='name_only':assert before['features'][0]['properties']['name']!=after['features'][0]['properties']['name']
    if kind=='larger_water':assert after['summary']['water_area_km2']>before['summary']['water_area_km2']
    if kind=='one_rendered_shoreline':assert len(rendered_water(after))==1
    if kind=='three_holes':assert len(rendered_water(after)[0].interiors)==3
    if kind=='reclaimed_land':
        reclaimed=unary_union([shape(f['geometry']) for f in after['render_features'] if f['properties'].get('role')=='reclaimed-land'])
        original=unary_union([shape(f['geometry']) for f in after['base_water_features']])
        assert not reclaimed.is_empty and reclaimed.difference(original).area<1e-9
    if kind=='less_water':assert after['summary']['water_area_km2']<before['summary']['water_area_km2']
    if kind=='split_components':assert len(rendered_water(after))==2
    if kind=='changed_shoreline':assert source_water(before)!=source_water(after)
    if kind=='border_only':assert before['summary']['water_area_km2']==after['summary']['water_area_km2']
    return {'status':'passed','before_summary':before['summary'],'after_summary':after['summary'],
        'before_sha256':before['sha256'],'after_sha256':after['sha256']}

def main():
    catalog=[];results=[]
    for case in build_cases():
        started=time.perf_counter();result=validate_case(case)
        result.update({'id':case['id'],'validation_ms':round((time.perf_counter()-started)*1000,3)})
        before=case['before'];after=case['after']
        for phase,doc in [('before',before),('after',after)]:
            doc['scenario']=case['id'];doc['provenance'].pop('mlflow_run_id',None)
            write(ROOT/'examples/cases'/case['id']/(phase+'.json'),doc)
        bounds=GeometryCollection([shape(f['geometry']) for d in [before,after] for f in d['features'] if f['properties'].get('role')!='replacement-region']).bounds
        entry={k:case[k] for k in ['id','title','description','expected','assertion','prompt']}
        entry['bounds']=list(bounds);catalog.append(entry);results.append(result)
    write(ROOT/'examples/catalog.json',catalog)
    write(ROOT/'examples/results/geometry-validation.json',{'schema_version':1,'kind':'actual_geometry_validation',
        'cases':results,'passed':sum(r['status']=='passed' for r in results),'total':len(results)})
    print(json.dumps({'examples':len(catalog),'passed':len(results),'gpu_used':False}))

if __name__=='__main__':main()
