"""Inspect real recorded artifacts, including a simple raster seam diagnostic."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

ROOT=Path(__file__).resolve().parents[1]
CASES=[
 ('shire-short-prompt','Middle-earth / Shire — default','pyramid'),
 ('shire-user-gardens','Middle-earth / Shire — user gardens','pyramid'),
 ('shire-adjacent-eval','Middle-earth / Shire — adjacent tile','pyramid'),
 ('shire-deep-eval','Middle-earth / Shire — deeper zoom','pyramid'),
 ('minas-tirith-eval','Middle-earth / Minas Tirith — inferred city','pyramid'),
 ('reservoir-canal','Earth / reservoir and canal','earth'),
 ('coastal-headland','Earth / coastal headland — 4-step legacy','earth'),
 ('earth-coastal-20','Earth / coastal headland — 20-step retest','evaluation')]

def folder(case, kind):
    if kind == 'pyramid':
        runtime = ROOT / '.runtime/pyramid/runs' / case
        if (runtime / 'manifest.json').is_file():
            return runtime
        return ROOT / 'examples/pyramid/middle-earth/recordings' / case
    return ROOT / ({'earth': 'examples/gpu', 'evaluation': '.runtime/evaluation/runs'}[kind]) / case

def seam_error(source,context):
    outside=[context.crop((255,256,256,512)),context.crop((512,256,513,512)),
             context.crop((256,255,512,256)),context.crop((256,512,512,513))]
    inside=[source.crop((0,0,1,256)),source.crop((255,0,256,256)),
            source.crop((0,0,256,1)),source.crop((0,255,256,256))]
    values=[sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)/3 for a,b in zip(inside,outside)]
    return round(sum(values)/4,2)

def catalog():
    records=[]
    for case,title,kind in CASES:
        base=folder(case,kind);manifest=base/'manifest.json'
        if not manifest.is_file():continue
        data=json.loads(manifest.read_text(encoding='utf-8'))
        source=base/'source.png';result=base/'result.png';context=base/'context.png'
        success=data.get('success',False) and result.is_file()
        artifacts={name:f'/api/generation-artifact/{case}/{name}.png' for name in ('source','result','context','parent') if (name!='result' or success) and (base/(name+'.png')).is_file()}
        integrity={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                   'source_hash_matches':hashlib.sha256(source.read_bytes()).hexdigest()==data.get('source_sha256')}
        metrics=None
        if success:
            output=Image.open(result).convert('RGB');original=Image.open(source).convert('RGB')
            integrity.update({'output_sha256':hashlib.sha256(result.read_bytes()).hexdigest(),
                              'output_hash_matches':hashlib.sha256(result.read_bytes()).hexdigest()==data.get('output_sha256'),
                              'output_dimensions':list(output.size)})
            if context.is_file():
                around=Image.open(context).convert('RGB')
                if around.size==(768,768) and original.size==output.size==(256,256):
                    metrics={'source_edge_mismatch':seam_error(original,around),'generated_edge_mismatch':seam_error(output,around),
                             'context_center_matches_source':ImageChops.difference(original,around.crop((256,256,512,512))).getbbox() is None,
                             'units':'mean absolute RGB channel difference / 255; lower is more color-continuous',
                             'limitation':'Raster edge-color diagnostic only; does not establish road, water or canonical geometry correctness.'}
        records.append({'id':case,'title':title,'kind':kind,'success':success,'status':'inference_succeeded' if success else 'rejected',
                        'target':data.get('target',[data.get(k) for k in ('z','x','y')]),
                        'steps':data.get('steps'),'seed':data.get('seed'),'elapsed_seconds':data.get('elapsed_seconds'),
                        'model_revision':data.get('model_revision'),'prompt':data.get('image_prompt',data.get('prompt','')),
                        'user_direction':data.get('user_direction',''),'detail':data.get('detail',''),
                        'artifacts':artifacts,'integrity':integrity,'seam_diagnostic':metrics,
                        'quality_approved':False,'height_data':False,
                        'visual_review':'Speculative raster draft. Review style, text reinterpretation and edge drift. No generated street geometry is saved.'})
    return {'schema_version':1,'kind':'actual_cuda_artifact_evaluation','records':records,
            'view_modes':['isometric','topdown','comparison','stack'],
            'projection_note':'Isometric mode projects the actual flat PNGs; it does not create 3D terrain or run another model.',
            'attribution':'Middle-earth fan-map source via Fraser Marlow; Earth basemap retains OpenStreetMap/OpenFreeMap attribution.'}

if __name__=='__main__':
    report=catalog();output=ROOT/'.runtime/evaluation';output.mkdir(parents=True,exist_ok=True)
    (output/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps([{'case':r['id'],'status':r['status'],'seam':r['seam_diagnostic']} for r in report['records']],indent=2))
