import copy
import json
from pathlib import Path
import sys
import unittest
from shapely.geometry import shape,mapping,Polygon
from shapely.ops import nearest_points
from shapely.geometry import LineString
from shapely import transform
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'dev-ui'))
from geometry_store import normalize_geography


class Geography(unittest.TestCase):
    def setUp(self):
        self.scene=json.loads((ROOT/'dev-ui/scenarios/great-lakes-two.json').read_text())

    def test_five_become_two_valid_separate_lakes(self):
        result=normalize_geography(self.scene)
        self.assertEqual(result['summary']['connected_water_bodies'],2)
        self.assertEqual(result['summary']['water_features'],2)
        self.assertGreater(result['summary']['water_area_km2'],450000)
        water=[shape(f['geometry']) for f in result['render_features'] if f['properties']['kind']=='water']
        self.assertTrue(all(g.is_valid and g.geom_type=='Polygon' for g in water))
        self.assertTrue(water[0].disjoint(water[1]))

    def test_land_edit_cuts_a_real_island_without_mutating_source_water(self):
        baseline=normalize_geography(self.scene)
        west=shape(next(f for f in baseline['features'] if f['id']=='great-lakes-west')['geometry'])
        p=west.representative_point();radius=.02
        island=Polygon([(p.x-radius,p.y-radius),(p.x+radius,p.y-radius),(p.x+radius,p.y+radius),(p.x-radius,p.y+radius)])
        self.assertTrue(west.contains(island))
        edited=copy.deepcopy(self.scene)
        edited['features'].append({'type':'Feature','id':'test-island','properties':{'kind':'land','name':'Test island'},'geometry':mapping(island)})
        # JSON round-trip matches the API coordinate representation.
        edited=json.loads(json.dumps(edited));result=normalize_geography(edited)
        self.assertLess(result['summary']['water_area_km2'],baseline['summary']['water_area_km2'])
        self.assertEqual(result['summary']['connected_water_bodies'],2)
        before=next(f for f in baseline['features'] if f['id']=='great-lakes-west')
        after=next(f for f in result['features'] if f['id']=='great-lakes-west')
        self.assertEqual(before,after)
        rendered=shape(next(f for f in result['render_features'] if f['id']=='great-lakes-west')['geometry'])
        self.assertFalse(rendered.contains(p))

    def test_border_edit_is_saved_independently(self):
        before=normalize_geography(self.scene);edited=copy.deepcopy(self.scene)
        border=next(f for f in edited['features'] if f['properties']['kind']=='border')
        border['geometry']['coordinates'][0][0]+=.1
        after=normalize_geography(edited)
        self.assertNotEqual(before['sha256'],after['sha256'])
        self.assertEqual(before['summary']['water_area_km2'],after['summary']['water_area_km2'])

    def test_drawn_water_connector_has_one_rendered_shoreline(self):
        result=normalize_geography(self.scene)
        water=[shape(f['geometry']) for f in result['features'] if f['properties']['kind']=='water']
        connector=LineString(nearest_points(*water)).buffer(.05)
        scene=copy.deepcopy(self.scene)
        scene['features'].append({'id':'connector','properties':{'kind':'water','name':'Connector'},'geometry':mapping(connector)})
        scene=json.loads(json.dumps(scene));connected=normalize_geography(scene)
        self.assertEqual(connected['summary']['connected_water_bodies'],1)
        self.assertEqual(sum(f['properties']['kind']=='water' for f in connected['render_features']),1)

    def test_invalid_polygon_and_nonfinite_coordinates_rejected(self):
        for coordinates in [[[[0,0],[1,1],[0,1],[1,0],[0,0]]],[[[0,0],[float('nan'),1],[0,1],[0,0]]]]:
            doc={'features':[{'id':'invalid','properties':{'kind':'water','name':'Invalid'},'geometry':{'type':'Polygon','coordinates':coordinates}}]}
            with self.assertRaises(ValueError):normalize_geography(doc)

    def test_reclaimed_land_is_limited_to_original_lake_footprint(self):
        from shapely.ops import unary_union
        scene=copy.deepcopy(self.scene)
        for feature in scene['features']:
            if feature['properties']['kind']=='water':feature['geometry']=mapping(shape(feature['geometry']).buffer(-.5))
        result=normalize_geography(json.loads(json.dumps(scene)))
        reclaimed=shape(next(f for f in result['render_features'] if f['properties'].get('role')=='reclaimed-land')['geometry'])
        original=unary_union([shape(f['geometry']) for f in result['base_water_features']])
        self.assertGreater(reclaimed.area,0)
        self.assertLess(reclaimed.difference(original).area,1e-9)


if __name__=='__main__':unittest.main()
