"""Run real checks and retain compact, machine-independent results."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--cpu-python');args=parser.parse_args()
    checks=[('python_tests',[sys.executable,'-m','unittest','discover','-s','tests']),
        ('name_invariance',['node','tests/test_labels.mjs']),('detail_cache_viewport',['node','tests/test_detail_rendering.mjs'])]
    if args.cpu_python:checks.append(('fresh_cpu_only',[args.cpu_python,'-m','unittest','discover','-s','tests']))
    results=[]
    for name,command in checks:
        completed=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
        output=completed.stdout+completed.stderr;match=re.search(r'Ran (\d+) tests',output)
        skipped=re.search(r'skipped=(\d+)',output)
        record={'name':name,'status':'passed' if completed.returncode==0 else 'failed'}
        if match:record['tests_run']=int(match.group(1));record['skipped_optional_modules']=int(skipped.group(1)) if skipped else 0
        results.append(record);print(json.dumps(record),flush=True)
        if completed.returncode:print(output);raise SystemExit(completed.returncode)
    (ROOT/'examples/results/test-validation.json').write_text(json.dumps({'schema_version':1,'checks':results},indent=2),encoding='utf-8')
if __name__=='__main__':main()
