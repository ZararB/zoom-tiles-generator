import unittest
from zoom_tiles.pyramid import PyramidGeometry, plan_context, generation_brief, validate_geometry_proposal


class PyramidTests(unittest.TestCase):
    def setUp(self):
        self.geo = PyramidGeometry(7680, 4386, 2)

    def test_matches_application_shire_fixture(self):
        self.assertEqual(self.geo.grid(2), (30, 18))
        self.assertEqual(self.geo.at_pixel(2, 2772, 1258), (2, 10, 4))
        self.assertEqual(self.geo.at_pixel(4, 2772, 1258), (4, 43, 19))
        self.assertEqual(self.geo.grid(-2), (2, 2))
        with self.assertRaises(ValueError): self.geo.validate(2, 30, 0)

    def test_bounded_context_no_wrap_and_exact_parent_crop(self):
        plan = plan_context(self.geo, 4, 43, 19, [(4, 42, 19)])
        self.assertEqual(len(plan['neighbors']), 8)
        self.assertEqual(len(plan['ancestors']), 3)
        self.assertEqual(len(plan['children']), 4)
        self.assertEqual(plan['ancestors'][0]['target_crop_uv'], [.5, .5, 1, 1])
        self.assertEqual((plan['native_cover'][0]['x'], plan['native_cover'][0]['y']), (10, 4))
        edge = plan_context(self.geo, 4, 0, 0)
        self.assertEqual(len(edge['neighbors']), 3)
        self.assertTrue(all(n['x'] >= 0 and n['y'] >= 0 for n in edge['neighbors']))
        self.assertFalse(edge['wrap_x'])
        self.assertFalse(plan['children'][0]['available'])

    def test_reproducible_brief_changes_with_user_research_and_artifacts(self):
        plan = plan_context(self.geo, 4, 43, 19)
        baseline = generation_brief(plan, {'claims': []})
        self.assertEqual(baseline, generation_brief(plan, {'claims': []}))
        for kwargs in ({'user_direction': 'more gardens'}, {'world_revision': 'rev2'}, {'artifact_hashes': {'parent': 'a'*64}}):
            self.assertNotEqual(baseline['sha256'], generation_brief(plan, {'claims': []}, **kwargs)['sha256'])
        self.assertNotEqual(baseline['sha256'], generation_brief(plan, {'claims': ['small settlement']})['sha256'])

    def test_pixel_geometry_not_limited_to_geographic_degrees(self):
        feature = {'type': 'Feature', 'properties': {'id': 'road-1', 'kind': 'road', 'provenance': 'inferred', 'confidence': .4, 'source_ids': []},
                   'geometry': {'type': 'LineString', 'coordinates': [[2760, 1240], [2780, 1260]]}}
        proposal = {'type': 'FeatureCollection', 'features': [feature]}
        self.assertTrue(validate_geometry_proposal(proposal, [2700, 1200, 2800, 1300])['valid'])
        with self.assertRaises(ValueError): validate_geometry_proposal(proposal, [0, 0, 10, 10])
        with self.assertRaises(ValueError): validate_geometry_proposal(proposal, [2700, 1200, 2800, 1300], {'road-1': {'type': 'Point', 'coordinates': [2770, 1250]}})


if __name__ == '__main__': unittest.main()
