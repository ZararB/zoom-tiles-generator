from pathlib import Path
import sys
import unittest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from generation_results import seam_error

class EdgeDiagnostic(unittest.TestCase):
    def test_identical_black_edges_and_full_white_discontinuity(self):
        context=Image.new('RGB',(768,768),'black')
        self.assertEqual(seam_error(Image.new('RGB',(256,256),'black'),context),0)
        self.assertEqual(seam_error(Image.new('RGB',(256,256),'white'),context),255)

    def test_single_red_neighbor_edge_contributes_one_quarter(self):
        context=Image.new('RGB',(768,768),'black')
        context.paste((255,0,0),(255,256,256,512))
        self.assertEqual(seam_error(Image.new('RGB',(256,256),'black'),context),21.25)

if __name__=='__main__':unittest.main()
