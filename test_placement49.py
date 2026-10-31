import unittest
import server as g
from test_game import room
class Placement(unittest.TestCase):
 def setUp(self):
  self.r=room();g.start(self.r);self.r['props']=[];self.r['nodes']=[];self.p=self.r['players'][0];self.p.update(credits=10000,metal=1000,wood=1000,riftglass=1000)
 def test_resources_scenery_and_ground_units_block_buildings(self):
  x,y=1500,1000;self.assertTrue(g.clear_footprint(self.r,'barracks',x,y));node={'id':'ore','kind':'riftglass','x':x+65,'y':y,'hp':100,'stock':200,'size':30};self.r['nodes'].append(node);self.assertFalse(g.clear_footprint(self.r,'barracks',x,y));node['stock']=0;self.assertTrue(g.clear_footprint(self.r,'barracks',x,y));self.r['props'].append({'id':'tree','kind':'tree','x':x,'y':y,'hp':100,'stock':100,'size':30});self.assertFalse(g.clear_footprint(self.r,'barracks',x,y));self.r['props'].clear();troop=g.entity(self.r,self.p,'infantry',x,y);self.assertFalse(g.clear_footprint(self.r,'barracks',x,y));troop['hp']=0;self.assertTrue(g.clear_footprint(self.r,'barracks',x,y))
 def test_rotate_and_move_respect_other_buildings_and_units(self):
  b=g.entity(self.r,self.p,'barracks',*g.snap_building('barracks',1500,1000));block=g.entity(self.r,self.p,'infantry',1500,1080)
  with self.assertRaisesRegex(AssertionError,'overlap'):g.command(self.r,self.p,dict(action='rotate_building',building=b['id']))
  self.assertEqual(b.get('facing',0),0);block['x']=1800;block['y']=1400;g.command(self.r,self.p,dict(action='rotate_building',building=b['id']));self.assertAlmostEqual(b['facing'],g.math.pi/2)
  with self.assertRaisesRegex(AssertionError,'overlap'):g.command(self.r,self.p,dict(action='relocate_building',building=b['id'],x=1800,y=1400))
  block['x']=2100;block['y']=1700;g.command(self.r,self.p,dict(action='relocate_building',building=b['id'],x=1800,y=1400));self.assertEqual((b['x'],b['y']),(1810,1400))
