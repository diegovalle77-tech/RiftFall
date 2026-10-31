import unittest
import server as g
class RoomMap(unittest.TestCase):
 def test_geometry_is_per_room(self):
  historical={'_map_geometry':'continental'};classic={}
  self.assertTrue(g.water_at(200,200,r=historical));self.assertFalse(g.water_at(200,200,r=classic));self.assertFalse(g.water_at(200,200))
  self.assertTrue(g.cliff_at(historical,4450,1600));self.assertFalse(g.cliff_at(classic,4450,1600))
 def test_land_unit_respects_continental_water(self):
  r={'_map_geometry':'continental','props':[]};unit={'kind':'infantry'}
  self.assertFalse(g.passable_water(r,unit,200,200));self.assertTrue(g.passable_water(r,{'kind':'gunboat'},200,200))
if __name__=='__main__':unittest.main()

class ContinentalMatch(unittest.TestCase):
 def world(self,n=4):
  from test_game import room
  r=room(n);r.update(_experimental_history=True,_map_geometry='continental');g.start(r);return r
 def test_starting_units_are_on_safe_land(self):
  r=self.world();self.assertEqual(len(r['nodes']),42)
  self.assertEqual(len({p['map_slot'] for p in r['players']}),4)
  for e in r['entities']:
   self.assertFalse(g.water_at(e['x'],e['y'],r=r));self.assertFalse(g.cliff_at(r,e['x'],e['y']))
  self.assertTrue(all(n['finite'] for n in r['nodes']))
 def test_solo_ai_and_late_join_have_distinct_slots(self):
  r=self.world(1);self.assertEqual(len(r['players']),3)
  p=dict(id='late',name='Late',faction='Vesper',team=1);r['players'].append(p);g.initialize_commander(r,p,1)
  self.assertEqual(len({q['map_slot'] for q in r['players']}),4)
 def test_naval_spawn_uses_room_geometry(self):
  r=self.world();spot=g.nearest_water(700,2000,r=r);self.assertIsNotNone(spot);self.assertTrue(g.water_at(*spot,r=r))
  self.assertIsNone(g.nearest_water(700,2000))
 def test_old_roads_do_not_block_new_map(self):
  self.assertTrue(g.road_lane(260,260));self.assertFalse(g.route_lane(self.world(),260,260))
 def test_geometry_is_serialized_without_private_switch(self):
  import json
  r=self.world();v=g.view(r,r['players'][0]);self.assertEqual(v['map_geometry']['kind'],'continental');self.assertNotIn('_map_geometry',v);json.dumps(v)
