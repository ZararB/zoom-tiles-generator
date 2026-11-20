"""Local text-to-topic-map planner. Layout is deterministic; facts are not invented.

This scaffold is replaceable by an application's research/structured-AI provider.
The provenance explicitly distinguishes curated demo outlines from user text.
"""
import hashlib
import math
import re

SCIENCE={
 'Physics':['Mechanics','Thermodynamics','Electromagnetism','Quantum physics','Relativity','Optics'],
 'Chemistry':['Organic chemistry','Inorganic chemistry','Physical chemistry','Analytical chemistry','Materials','Biochemistry'],
 'Biology':['Cell biology','Genetics','Evolution','Ecology','Physiology','Microbiology'],
 'Mathematics':['Algebra','Geometry','Analysis','Probability','Statistics','Logic'],
 'Earth & space':['Geology','Climate','Oceanography','Astronomy','Planetary science','Geophysics'],
 'Computing':['Algorithms','AI & learning','Computer systems','Networks','Software','Theory'],
 'Human sciences':['Psychology','Sociology','Economics','Anthropology','Linguistics','Cognitive science']}
HISTORY={
 'Early societies':['Agriculture','Cities','Writing','Oral traditions','Archaeology','Settlement'],
 'States & empires':['Governance','Law','Administration','Conflict','Diplomacy','Political change'],
 'Trade & exchange':['Trade routes','Migration','Maritime networks','Markets','Cultural exchange','Money'],
 'Belief & culture':['Religion','Philosophy','Art','Literature','Education','Everyday life'],
 'Technology & work':['Tools','Craft','Industry','Transport','Communication','Labor'],
 'Global connections':['Colonialism','Decolonization','International institutions','Social movements','Environment','Globalization']}

ENTERTAINMENT = {
    'Film': ['Film production', 'Screenwriting', 'Cinematography', 'Editing', 'Film distribution', 'Documentary'],
    'Television & streaming': ['Series', 'Broadcasting', 'Streaming platforms', 'Animation', 'Reality TV', 'Scheduling'],
    'Music': ['Songwriting', 'Recording', 'Music publishing', 'Streaming audio', 'Soundtracks', 'Live music'],
    'Video games': ['Game design', 'Worldbuilding', 'Game development', 'Esports', 'Game publishing', 'Interactive narrative'],
    'Audio & podcasts': ['Radio', 'Podcast production', 'Audio drama', 'Interviews', 'Voice acting', 'Audiobooks'],
    'Publishing': ['Books', 'Magazines', 'Comics', 'Digital publishing', 'Editorial', 'Adaptation'],
    'Live entertainment': ['Theater', 'Concerts', 'Festivals', 'Stand-up comedy', 'Dance', 'Stage production'],
}


def plan_text_world(prompt,ai_outline=None):
    if not isinstance(prompt,str) or not 3<=len(prompt.strip())<=2000:raise ValueError('Enter 3–2000 characters')
    prompt=prompt.strip();lower=prompt.lower()
    if ai_outline is not None:
        title=ai_outline['title'];theme=ai_outline['theme'];outline={b['name']:b['topics'] for b in ai_outline['branches']};provenance='local_ai_outline'
    elif re.match(r"^(?:a )?(?:map of )?media\s*(?:&|and)\s*entertainment\b", lower):
        outline=ENTERTAINMENT;theme='entertainment';title='Media & entertainment';provenance='curated_demo_outline'
    elif any(word in lower for word in ('science','scientific','biology','physics','chemistry')):
        outline=SCIENCE;theme='science';title='Map of science';provenance='curated_demo_outline'
    elif any(word in lower for word in ('history','historical')):
        outline=HISTORY;theme='history';title='Map of history';provenance='curated_demo_outline'
    else:
        topics=[s.strip(' -•')[:70] for s in re.split(r'[\n;,]',prompt) if s.strip(' -•')]
        if len(topics)==1:topics=list(dict.fromkeys(re.findall(r'[\w-]{4,}',prompt)))[:8]
        if not topics:topics=[prompt[:70]]
        outline={topic:['Questions','Methods','Connections','Examples'] for topic in topics[:8]}
        theme='custom';title=prompt[:70];provenance='user_text_scaffold'
    nodes=[{'id':'root','label':title,'x':2048,'y':2048,'min_z':0,'depth':0,'parent':None}]
    edges=[];count=len(outline)
    for i,(name,children) in enumerate(outline.items()):
        angle=-math.pi/2+i*2*math.pi/count;x=2048+1280*math.cos(angle);y=2048+1280*math.sin(angle)
        parent=f'topic-{i}';nodes.append({'id':parent,'label':name,'x':round(x,2),'y':round(y,2),'min_z':0,'depth':1,'parent':'root'});edges.append(['root',parent])
        for j,label in enumerate(children):
            a=angle-1.6+j*3.2/max(1,len(children)-1);cx=x+380*math.cos(a);cy=y+380*math.sin(a);cid=f'{parent}-{j}'
            nodes.append({'id':cid,'label':label,'x':round(cx,2),'y':round(cy,2),'min_z':2,'depth':2,'parent':parent});edges.append([parent,cid])
            for k,detail in enumerate(('Questions','Methods','Connections')):
                da=a+(k-1)*1.6;did=f'{cid}-{k}'
                nodes.append({'id':did,'label':detail,'x':round(cx+105*math.cos(da),2),'y':round(cy+105*math.sin(da),2),
                              'min_z':4,'depth':3,'parent':cid});edges.append([cid,did])
    return {'title':title,'prompt':prompt,'theme':theme,'planner':provenance,'nodes':nodes,'edges':edges,
            'geometry':{'map_width_px':4096,'map_height_px':4096,'native_max_z':4,'extended_min_z':0,'extended_max_z':7},
            'generation_prompt': 'Refine an abstract science atlas, subtle blue terrain texture, preserve the diagram layout. No text.' if theme=='science' else 'Refine a dark amber media and entertainment atlas with cinematic landmark art. Preserve the topic layout. No text.' if theme=='entertainment' else 'Refine a parchment knowledge atlas, subtle terrain texture, preserve the diagram layout. No text.',
            'research':{'status':'model_outline_unverified_not_live_research' if ai_outline else 'curated_outline_not_live_research','sources':[],
                        'limitations':['Conceptual grouping, not an exhaustive taxonomy or measured geography.','Layout connections are illustrative; no generated factual claims.','A research/AI planner can replace this local scaffold through the same world schema.']},
            'layout_seed':hashlib.sha256(prompt.encode()).hexdigest(),'planner_metadata':ai_outline.get('_provenance',{}) if ai_outline else {}}
