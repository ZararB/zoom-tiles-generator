import base64
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dev-ui'))
from tile_jobs import TileJobs

IMAGE=base64.b64encode(b'test bytes').decode()
def body(x,viewport=1,client='test',priority=0):
    return {'client_id':client,'viewport_id':viewport,'priority':priority,
        'payload':{'image_base64':IMAGE,'z':3,'x':x,'y':1,'prompt':'Preserve detail',
            'world_sha256':'a'*64,'world_revision':'rev1','steps':4}}

class Jobs(unittest.TestCase):
    def test_latest_viewport_cancels_queue_deduplicates_and_persists(self):
        with tempfile.TemporaryDirectory() as folder:
            started=threading.Event();release=threading.Event();calls=[]
            def execute(payload):
                calls.append(payload['x']);started.set();assert release.wait(3)
                return {'success':True,'image_base64':IMAGE,'world_sha256':payload['world_sha256']}
            queue=TileJobs(folder,'http://unused',execute,lambda:{'revision':'model1'})
            first=queue.submit(body(0));assert started.wait(3)
            duplicate=queue.submit(body(0));self.assertEqual(first['id'],duplicate['id'])
            old=queue.submit(body(1));new=queue.submit(body(2,viewport=2))
            self.assertEqual(queue.get(old['id'])['status'],'cancelled')
            queue.cancel('test',1);self.assertEqual(queue.get(new['id'])['status'],'queued')
            queue.cancel('test',2);self.assertEqual(queue.get(new['id'])['status'],'queued')
            with self.assertRaises(ValueError):queue.submit(body(3,viewport=1))
            thread=queue.thread;release.set();thread.join(5);self.assertFalse(thread.is_alive())
            self.assertEqual(calls,[0,2]);self.assertEqual(queue.get(new['id'])['status'],'completed')
            cold=TileJobs(folder,'http://unused',lambda p:self.fail('Cache hit must not infer'),lambda:{'revision':'model1'})
            hit=cold.submit(body(2,viewport=3));self.assertTrue(hit['cache_hit'])
            changed=body(2,viewport=4);changed['payload']['world_sha256']='b'*64
            changed['payload']['steps']=51
            with self.assertRaises(ValueError):cold.submit(changed)

    def test_center_priority_and_world_model_cache_invalidation(self):
        with tempfile.TemporaryDirectory() as folder:
            started=threading.Event();release=threading.Event();calls=[]
            def execute(payload):
                calls.append(payload['x']);started.set();assert release.wait(3)
                return {'success':True,'image_base64':IMAGE}
            queue=TileJobs(folder,'http://unused',execute,lambda:{'revision':'model1'})
            first=queue.submit(body(0));assert started.wait(3)
            far=queue.submit(body(1,client='other',priority=9))
            near=queue.submit(body(2,client='other',priority=1))
            thread=queue.thread;release.set();thread.join(5)
            self.assertEqual(calls,[0,2,1])
            changed=body(0,viewport=2);changed['payload']['world_sha256']='b'*64
            other=queue.submit(changed);self.assertNotEqual(first['id'],other['id'])
            thread=queue.thread
            if thread:thread.join(5)
            model=TileJobs(folder,'http://unused',execute,lambda:{'revision':'model2'})
            regenerated=model.submit(body(0,viewport=3));self.assertNotEqual(first['id'],regenerated['id'])
            thread=model.thread
            if thread:thread.join(5)

if __name__=='__main__':unittest.main()
