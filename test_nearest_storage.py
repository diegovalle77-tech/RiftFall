import unittest
import server as g
from test_game import room
class NearestStorage(unittest.TestCase):
 def world(self):
  r=room();g.start(r)
  for p in r['players']:p.update(auto_idle=False,autopilot=False,ai_next=99999)
  p=r['players'][0];h=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='harvester');w=g.entity(r,p,'warehouse',3100,1000);h.update(x=2850,y=1000,cargo=750,cargo_loads={'metal':400,'wood':350},load_type='metal',goal=None)
  return r,p,h,w
 def test_nearby_warehouse_selected_and_mixed_cargo_unloaded(self):
  r,p,h,w=self.world();g.tick(r,.1);self.assertEqual(h['unload_target'],w['id']);self.assertEqual(h['unload_kind'],'warehouse');self.assertTrue(h['moving'])
  anchor=g.unload_anchor(w,h);self.assertLess(anchor['x'],w['x']-g.FOOTPRINTS['warehouse'][0]);h.update(x=anchor['x'],y=anchor['y']);before=(p['metal'],p['wood']);g.tick(r,.1);self.assertEqual(h['cargo'],0);self.assertEqual((p['metal'],p['wood']),(before[0]+400,before[1]+350))
 def test_destroyed_warehouse_falls_back_to_core(self):
  r,p,h,w=self.world();w['hp']=0;core=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='core');g.tick(r,.1);self.assertEqual(h['unload_target'],core['id'])
