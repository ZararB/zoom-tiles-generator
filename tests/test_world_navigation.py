import base64
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from zoom_tiles.text_worlds import plan_text_world
from zoom_tiles.navigation import WorldEngine,edge_blend,png,atomic_json

class TextWorlds(unittest.TestCase):
    def test_science_history_and_custom_text_have_stable_bounded_nodes(self):
        for prompt in ('map of science','map of history','Ocean ecology; Reefs; Mangroves; Fisheries'):
            world=plan_text_world(prompt)
            self.assertEqual(world,plan_text_world(prompt))
            self.assertGreater(len(world['nodes']),20)
            self.assertTrue(all(0<=n['x']<4096 and 0<=n['y']<4096 for n in world['nodes']))
            self.assertEqual(len({n['id'] for n in world['nodes']}),len(world['nodes']))
            self.assertEqual(world['research']['status'],'curated_outline_not_live_research')
        with self.assertRaises(ValueError):plan_text_world('')
        with self.assertRaises(ValueError):plan_text_world('x'*2001)
    def test_edge_blending_keeps_all_source_boundary_pixels(self):
        source=Image.new('RGB',(256,256),'red');result=Image.new('RGB',(256,256),'blue');combined=edge_blend(source,result)
        for n in range(256):
            for xy in ((n,0),(n,255),(0,n),(255,n)):self.assertEqual(combined.getpixel(xy),(255,0,0))
        self.assertEqual(combined.getpixel((128,128)),(0,0,255))

class Navigation(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.engine=WorldEngine(self.tmp.name,lambda z,x,y:Image.new('RGB',(256,256),'gray'),start_worker=False)
        self.world=self.engine.create('map of science');self.wid=self.world['id']
    def tearDown(self):self.tmp.cleanup()
    def test_world_and_initial_tiles_persist(self):
        reloaded=WorldEngine(self.tmp.name,lambda *args:self.fail('Saved knowledge tiles need no Middle-earth fetch'),start_worker=False)
        self.assertEqual(reloaded.world(self.wid),self.world)
        self.assertEqual(len(list((Path(self.tmp.name)/self.wid/'base').glob('*.png'))),5)
        self.assertEqual(reloaded.base(self.wid,1,0,0).tobytes(),self.engine.base(self.wid,1,0,0).tobytes())
    def test_new_epoch_cancels_queued_work_and_older_epoch_cannot_recreate_it(self):
        one=self.engine.submit(self.wid,[{'z':2,'x':1,'y':1}],'client',1)['jobs'][0]
        two=self.engine.submit(self.wid,[{'z':2,'x':2,'y':1}],'client',2)['jobs'][0]
        self.assertEqual(self.engine.jobs[one['id']]['status'],'cancelled')
        self.assertEqual(self.engine.jobs[two['id']]['status'],'queued')
        self.assertTrue(self.engine.submit(self.wid,[],'client',1)['superseded'])
        with self.assertRaises(ValueError):self.engine.submit(self.wid,[{'z':2,'x':4,'y':0}],'client',3)
    def test_identical_target_deduplicates_and_initial_seed_survives_navigation(self):
        one=self.engine.submit(self.wid,[{'z':0,'x':0,'y':0}],'seed',0,keep=True)['jobs'][0]
        two=self.engine.submit(self.wid,[{'z':0,'x':0,'y':0}],'browser',1)['jobs'][0]
        self.assertEqual(one['id'],two['id'])
        self.engine.submit(self.wid,[],'browser',2)
        self.assertEqual(self.engine.jobs[one['id']]['status'],'queued')
    def test_invalid_batch_does_not_partially_queue_or_advance_viewport(self):
        self.engine.submit(self.wid,[{'z':2,'x':1,'y':1}],'client',1)
        before=list(self.engine.jobs)
        with self.assertRaises(ValueError):self.engine.submit(self.wid,[{'z':2,'x':2,'y':1},{'z':2,'x':9,'y':1}],'client',2)
        self.assertEqual(list(self.engine.jobs),before);self.assertEqual(self.engine.latest['client'],1)
    def test_inherited_parent_crop_and_worker_context_are_provenanced(self):
        folder=self.engine.tile_dir(self.wid,0,0,0);folder.mkdir(parents=True)
        (folder/'blended.png').write_bytes(png(Image.new('RGB',(256,256),'blue')))
        atomic_json(folder/'manifest.json',{'tile':[0,0,0],'draft_only':True})
        child,origin=self.engine.image(self.wid,1,1,0,'blended');self.assertEqual(origin,'inherited_parent');self.assertEqual(child.getpixel((128,128)),(0,0,255))
        job=self.engine.submit(self.wid,[{'z':1,'x':1,'y':0}],'client',1)['jobs'][0]
        class Response:
            status_code=200
            ok=True
            def raise_for_status(self):pass
            def json(self):return {'image_base64':base64.b64encode(png(Image.new('RGB',(256,256),'green'))).decode(),'success':True,'world_revision':job['world_revision'],'elapsed_seconds':1}
        with patch('zoom_tiles.navigation.requests.post',return_value=Response()) as call:
            manifest=self.engine._generate(job)
        self.assertEqual(manifest['source_origin'],'inherited_parent')
        self.assertEqual(call.call_args.kwargs['json']['coordinate_space'],'pixel')
        self.assertTrue(all(d['origin']=='inherited_parent' for d in manifest['context_dependencies'].values()))
        self.assertTrue(manifest['draft_only'])
        # This is a mocked contract check, not an actual CUDA recording.
    def test_rejection_keeps_source_and_does_not_publish_or_repeat_failed_tile(self):
        job=self.engine.submit(self.wid,[{'z':1,'x':0,'y':0}],'client',1)['jobs'][0]
        class Rejected:
            status_code=422
            ok=False
            def json(self):return {'detail':'Image did not pass the model safety checker'}
        with patch('zoom_tiles.navigation.requests.post',return_value=Rejected()):
            with self.assertRaisesRegex(ValueError,'safety checker'):self.engine._generate(job)
        folder=self.engine.tile_dir(self.wid,1,0,0)
        self.assertTrue((folder/'source.png').exists());self.assertTrue((folder/'rejection.json').exists())
        self.assertIsNone(self.engine.metadata(self.wid,1,0,0))
        self.engine.jobs[job['id']]['status']='failed'
        again=self.engine.submit(self.wid,[{'z':1,'x':0,'y':0}],'client',2)['jobs'][0]
        self.assertEqual(again['id'],job['id']);self.assertEqual(again['status'],'failed')

if __name__=='__main__':unittest.main()
