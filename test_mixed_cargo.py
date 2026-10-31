import unittest
import server as g
from test_storage import StorageTests
class MixedCargo(unittest.TestCase):
 def test_redirect_preserves_mixed_cargo_and_clears_route(self):
  r,p,h,core=StorageTests().setup_world();h.update(cargo=200,load_type='metal',cargo_loads={'metal':200},goal=[100,100],_route=[[100,100]],_route_key='old')
  wood=next(n for n in r['nodes'] if n['kind']=='wood')
  g.command(r,p,dict(action='gather',ids=[h['id']],resource='wood',node=wood['id']))
  self.assertIsNone(h['goal']);self.assertNotIn('_route',h);self.assertEqual(h['load_type'],'wood')
  h.update(x=wood['x'],y=wood['y']);g.tick(r,.5)
  self.assertEqual(h['cargo_loads']['metal'],200);self.assertEqual(h['cargo_loads']['wood'],10);self.assertEqual(h['cargo'],210)
  h.update(x=core['x'],y=core['y'],storage_blocked=True);before=(p['wood'],p['metal']);g.tick(r,.1)
  self.assertEqual(p['wood'],before[0]+10);self.assertEqual(p['metal'],before[1]+200);self.assertEqual(h['cargo'],0)
 def test_expansion_levels_and_ownership(self):
  r,p,h,core=StorageTests().setup_world();p.update(credits=50000,metal=50000,wood=50000);w=g.entity(r,p,'warehouse',1000,1000)
  self.assertEqual(g.storage_capacity(r,p),6500)
  for level in range(2,6):
   p.setdefault('tech',[]).append('storage_'+str(level));g.apply_research_upgrades(r,p);self.assertEqual(w['storage_level'],level);self.assertEqual(g.storage_capacity(r,p),1500+g.WAREHOUSE_CAPACITIES[level])
  self.assertEqual(g.entity(r,p,'warehouse',1400,1000)['storage_level'],5)
