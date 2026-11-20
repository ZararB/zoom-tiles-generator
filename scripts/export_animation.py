"""Convert the explicit browser recording into a full MP4 and reusable chapters."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.runtime/animations'

def command(args):
    subprocess.run(args,check=True,capture_output=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path);parser.add_argument('--variant',choices=['original','stacked'],default='original');args=parser.parse_args()
    stacked=args.variant=='stacked'
    source=args.input or OUT/('stacked-every-level.webm' if stacked else 'make-every-level.webm')
    output=OUT/'stacked' if stacked else OUT
    ffmpeg=shutil.which('ffmpeg');probe=shutil.which('ffprobe')
    if not ffmpeg or not probe:raise SystemExit('Install FFmpeg from its official distribution and add it to PATH.')
    if not source.is_file():raise SystemExit('Record the animation in the preview first.')
    output.mkdir(parents=True,exist_ok=True);movie=output/('make-every-level-stacked.mp4' if stacked else 'make-every-level.mp4')
    command([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(source),'-t','36','-an','-r','30',
             '-c:v','libx264','-preset','fast','-crf','21','-pix_fmt','yuv420p','-g','60','-threads','4','-movflags','+faststart',str(movie)])
    chapters=[(0,'01-aligned-zoom-levels'),(10,'02-generate-the-missing-tile'),(20,'03-one-world-across-scales')] if stacked else [(0,'01-tiles-within-tiles'),(10,'02-context-becomes-detail'),(20,'03-one-world-every-level')]
    for start,name in chapters:
        command([ffmpeg,'-hide_banner','-loglevel','error','-y','-ss',str(start),'-i',str(movie),'-an','-frames:v','300',
                 '-c:v','libx264','-preset','fast','-crf','21','-pix_fmt','yuv420p','-r','30','-threads','4',
                 '-movflags','+faststart',str(output/(name+'.mp4'))])
    results=[]
    for path in sorted(output.glob('*.mp4')):
        raw=subprocess.check_output([probe,'-v','error','-show_entries','stream=width,height,codec_name,nb_frames:format=duration','-of','json',str(path)])
        info=json.loads(raw);results.append({'file':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),**info})
    (output/'manifest.json').write_text(json.dumps({'kind':'original-code-rendered-animation','variant':args.variant,'headline':"Don't just make a map. Make every level.",'records':results},indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
