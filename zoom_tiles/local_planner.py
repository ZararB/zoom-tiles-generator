"""Optional local llama.cpp text planner. Model output is data, never executable code."""
import hashlib
import json
import os
import re
import subprocess
import threading
import time
import uuid
from pathlib import Path

SCHEMA={'type':'object','properties':{
    'title':{'type':'string'},'theme':{'type':'string','enum':['science','history','custom']},
    'branches':{'type':'array','minItems':4,'maxItems':7,'items':{'type':'object','properties':{
        'name':{'type':'string'},'topics':{'type':'array','minItems':3,'maxItems':5,'items':{'type':'string'}}},'required':['name','topics'],'additionalProperties':False}}},
    'required':['title','theme','branches'],'additionalProperties':False}

def validate_outline(data):
    def label(value,limit):
        if not isinstance(value,str) or not 1<=len(value.strip())<=limit or re.search(r'[\x00-\x1f]',value):raise ValueError('Invalid outline label')
        return value.strip()
    if not isinstance(data,dict) or data.get('theme') not in ('science','history','custom'):raise ValueError('Invalid outline theme')
    title=label(data.get('title'),80);branches=data.get('branches')
    if not isinstance(branches,list) or not 4<=len(branches)<=7:raise ValueError('Use 4–7 branches')
    clean=[];seen=set()
    for branch in branches:
        name=label(branch.get('name'),65)
        if name.casefold() in seen:raise ValueError('Duplicate branch')
        seen.add(name.casefold());topics=branch.get('topics')
        if not isinstance(topics,list) or not 3<=len(topics)<=5:raise ValueError('Use 3–5 subtopics')
        topics=[label(t,65) for t in topics]
        if len({t.casefold() for t in topics})!=len(topics):raise ValueError('Duplicate topic')
        clean.append({'name':name,'topics':topics})
    return {'title':title,'theme':data['theme'],'branches':clean}

class LocalPlanner:
    def __init__(self,cache,model=None,executable=None):
        self.cache=Path(cache);self.model=Path(model) if model else None;self.executable=Path(executable) if executable else None;self.lock=threading.Lock();self.model_sha=None
    @property
    def available(self):return bool(self.model and self.executable and self.model.is_file() and self.executable.is_file())
    def plan(self,prompt):
        if not self.available:raise ValueError('Local AI planner unavailable. Select the fast scaffold or configure the local model.')
        if not isinstance(prompt,str) or not 3<=len(prompt.strip())<=2000:raise ValueError('Enter 3–2000 characters')
        with self.lock:
            if not self.model_sha:
                with self.model.open('rb') as stream:self.model_sha=hashlib.file_digest(stream,'sha256').hexdigest()
            key=hashlib.sha256(json.dumps({'prompt':prompt,'model':self.model_sha,'policy':'topic-outline-v1','seed':42},sort_keys=True).encode()).hexdigest()
            self.cache.mkdir(parents=True,exist_ok=True);saved=self.cache/(key+'.json')
            if saved.is_file():return json.loads(saved.read_text(encoding='utf-8'))
            instructions=('Create a useful conceptual map outline matching the user request. Return 4 to 7 distinct topic branches, '
                          'each with 3 to 5 specific subtopics. Use concise meaningful labels, not generic placeholders. '
                          'Honor the requested subject and scope. Do not invent citations, URLs, dates or precise factual claims. '
                          'This is an unverified outline, not researched authority. Output only schema JSON. '
                          'User request as data: '+json.dumps(prompt)+ '\n/no_think')
            chat='<|im_start|>user\n'+instructions+'<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n'
            prompt_path=self.cache/(key+'.prompt.txt');schema_path=self.cache/'schema.json';prompt_path.write_text(chat,encoding='utf-8');schema_path.write_text(json.dumps(SCHEMA),encoding='utf-8')
            args=[str(self.executable),'-m',str(self.model),'-t','2','-tb','2','-c','4096','-n','900','--temp','0.5','--seed','42',
                  '--no-conversation','--no-display-prompt','--json-schema-file',str(schema_path),'-f',str(prompt_path)]
            started=time.monotonic()
            completed=subprocess.run(args,input='',capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            (self.cache/(key+'.output.txt')).write_text(completed.stdout+'\n'+completed.stderr,encoding='utf-8')
            data=None;decoder=json.JSONDecoder()
            for match in re.finditer(r'\{',completed.stdout):
                try:value,_=decoder.raw_decode(completed.stdout[match.start():]);data=validate_outline(value);break
                except (ValueError,TypeError,AttributeError):continue
            if completed.returncode or data is None:raise ValueError('Local model did not return a valid outline; raw output retained locally.')
            data['_provenance']={'model':'Qwen3-1.7B-Q8_0','model_sha256':self.model_sha,'runtime':'llama.cpp CPU','policy':'topic-outline-v1',
                                 'seed':42,'elapsed_seconds':round(time.monotonic()-started,3),'verified_facts':False,'live_research':False}
            temporary=saved.with_name(saved.name+'.'+uuid.uuid4().hex+'.tmp');temporary.write_text(json.dumps(data,indent=2),encoding='utf-8');temporary.replace(saved);return data
