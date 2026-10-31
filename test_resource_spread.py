import unittest
import server as g
from test_game import room
class ResourceSpread(unittest.TestCase):
 def test_materials_cover_every_quadrant_and_avoid_blocked_ground(self):
  r=room(4);g.start(r)
  for kind in ['metal','wood','riftglass']:
   deposits=[n for n in r['nodes'] if n['kind']==kind];self.assertGreaterEqual(len(deposits),16)
   for side_x in [0,1]:
    for side_y in [0,1]:self.assertTrue(any(int(n['x']>=g.WORLD_W/2)==side_x and int(n['y']>=g.WORLD_H/2)==side_y for n in deposits),(kind,side_x,side_y))
  for n in r['nodes']:self.assertFalse(g.water_at(n['x'],n['y']));self.assertFalse(g.cliff_at(r,n['x'],n['y']))
