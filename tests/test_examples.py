import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import io
import base64
from PIL import Image
from http.server import ThreadingHTTPServer
import requests
from scripts.generate_examples import build_cases,validate_case

ROOT=Path(__file__).resolve().parents[1]

class Examples(unittest.TestCase):
    def test_every_recorded_geometry_scenario(self):
        cases=build_cases();self.assertEqual(len(cases),11)
        for case in cases:
            with self.subTest(case=case['id']):self.assertEqual(validate_case(case)['status'],'passed')

    def test_actual_http_save_rejection_and_conflict_contract(self):
        spec=importlib.util.spec_from_file_location('example_server',ROOT/'dev-ui/serve_dev_ui.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            data=Path(directory);module.GEOGRAPHY=data/'world.json';module.MAP_EDITS=data/'names.json';module.PROPOSALS=data/'proposals'
            module.RECORDINGS=data/'recordings'
            server=ThreadingHTTPServer(('127.0.0.1',0),module.DevUiHandler)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            base='http://127.0.0.1:'+str(server.server_address[1])
            try:
                catalog=requests.get(base+'/api/examples',timeout=5).json();self.assertEqual(len(catalog),11)
                self.assertEqual(requests.post(base+'/api/record-source',json={},timeout=5).status_code,403)
                for case in catalog:
                    for phase in ['before','after']:
                        with self.subTest(case=case['id'],phase=phase):
                            current=requests.get(base+'/api/geography',timeout=5).json()
                            candidate=requests.get(base+f"/api/examples/{case['id']}/{phase}",timeout=5).json()
                            response=requests.post(base+'/api/geography',json={**candidate,'expected_revision':current['revision']},timeout=5)
                            if case['assertion']=='reject_invalid' and phase=='after':
                                self.assertEqual(response.status_code,422)
                                self.assertEqual(requests.get(base+'/api/geography',timeout=5).json()['sha256'],current['sha256'])
                            else:
                                self.assertEqual(response.status_code,200,response.text)
                                self.assertEqual(response.json()['summary']['connected_water_bodies'],case['expected'][0 if phase=='before' else 1])
                response=requests.post(base+'/api/geography',json={'expected_revision':'obsolete','features':[]},timeout=5)
                self.assertEqual(response.status_code,409)
                current=requests.get(base+'/api/geography',timeout=5).json()
                candidate=requests.get(base+'/api/examples/reservoir-canal/after',timeout=5).json()
                world=requests.post(base+'/api/geography',json={**candidate,'expected_revision':current['revision']},timeout=5).json()
                buffer=io.BytesIO();Image.new('RGB',(256,256),'blue').save(buffer,'PNG')
                payload={'case_id':'reservoir-canal','world_sha256':world['sha256'],'world_revision':world['revision'],
                    'z':7,'x':62,'y':48,'image_base64':base64.b64encode(buffer.getvalue()).decode()}
                with patch.dict(module.os.environ,{'ZOOM_TILE_RECORD_EXAMPLES':'1'}):
                    recorded=requests.post(base+'/api/record-source',json=payload,timeout=5)
                    self.assertEqual(recorded.status_code,201,recorded.text)
                    self.assertTrue((module.RECORDINGS/'reservoir-canal/source.png').is_file())
                    stale=requests.post(base+'/api/record-source',json={**payload,'world_sha256':'0'*64},timeout=5)
                    self.assertEqual(stale.status_code,409)
            finally:
                server.shutdown();thread.join(3);server.server_close()

if __name__=='__main__':unittest.main()
