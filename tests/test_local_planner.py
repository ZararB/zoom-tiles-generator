import unittest
from zoom_tiles.local_planner import LocalPlanner,validate_outline
from zoom_tiles.text_worlds import plan_text_world

def example():return {'title':'Ocean systems','theme':'science','branches':[{'name':name,'topics':['Structure','Processes','Interactions']} for name in ('Reefs','Plankton','Currents','Coasts')]}

class PlannerContract(unittest.TestCase):
    def test_validated_ai_outline_controls_the_saved_topics(self):
        outline=validate_outline(example());world=plan_text_world('Ocean systems',outline)
        self.assertEqual(world['planner'],'local_ai_outline')
        self.assertTrue(any(n['label']=='Plankton' for n in world['nodes']))
        self.assertFalse(any(n['label']=='Mathematics' for n in world['nodes']))
        self.assertEqual(world['research']['status'],'model_outline_unverified_not_live_research')
    def test_duplicate_and_unbounded_output_rejected(self):
        data=example();data['branches'][1]['name']='Reefs'
        with self.assertRaises(ValueError):validate_outline(data)
        data=example();data['title']='x'*81
        with self.assertRaises(ValueError):validate_outline(data)
    def test_unconfigured_planner_is_explicitly_unavailable(self):
        planner=LocalPlanner('unused');self.assertFalse(planner.available)
        with self.assertRaises(ValueError):planner.plan('Map of science')

if __name__=='__main__':unittest.main()
