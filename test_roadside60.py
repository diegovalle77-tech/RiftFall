import unittest,math
import server as g
from test_game import room,start_unlocked
class Roadside(unittest.TestCase):
 def setUp(self):
  self.r=room();start_unlocked(self.r);self.p=self.r['players'][0]
  for p in self.r['players']:p.update(auto_idle=False,autopilot=False,ai_next=999999)
 def test_scenery_sits_next_to_roads_without_blocking_them(self):
  cars=[o for o in self.r['props'] if o['kind']=='abandoned_car'];businesses=[o for o in self.r['props'] if o['kind']=='road_business'];self.assertEqual(len(cars),9);self.assertEqual(len(businesses),3)
  for obj in cars+businesses:
   self.assertTrue(g.road_lane(obj['x'],obj['y'],260));self.assertFalse(g.road_lane(obj['x'],obj['y'],80));self.assertFalse(g.bridge_lane(self.r,obj['x'],obj['y'],100));self.assertFalse(g.water_at(obj['x'],obj['y']));self.assertFalse(g.cliff_at(self.r,obj['x'],obj['y']))
  self.assertTrue(all('parking' in o for o in businesses))
 def test_units_can_attack_and_destroy_abandoned_car(self):
  car=next(o for o in self.r['props'] if o['kind']=='abandoned_car');soldier=g.entity(self.r,self.p,'infantry',car['x']+50,car['y']);car['hp']=15
  g.command(self.r,self.p,dict(action='attack',ids=[soldier['id']],target=car['id']));self.assertEqual(soldier['attack'],car['id'])
  for _ in range(35):g.tick(self.r,.2)
  self.assertFalse(any(o['id']==car['id'] for o in self.r['props']))
if __name__=='__main__':unittest.main()
