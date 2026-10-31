import unittest,math
import server as g
from test_game import room
class Naval(unittest.TestCase):
 def world(self):
  r=room();g.start(r);r['props']=[];r['nodes']=[]
  for p in r['players']:p.update(auto_idle=False,autopilot=False,ai_next=99999)
  p=r['players'][0];p.update(tech=['industry'],credits=10000,metal=2000,wood=2000,riftglass=2000,power=100)
  shore=next((dict(x=x,y=3440) for x in range(4100,4400,5) if not g.water_at(x,3440) and g.nearest_water(x,3440,100)),None);self.assertIsNotNone(shore);return r,p,shore
 def test_dock_produces_water_only_ships(self):
  r,p,shore=self.world();dock=g.entity(r,p,'dock',shore['x'],shore['y']);g.command(r,p,dict(action='train',kind='transport',producer=dock['id']));g.tick_production(r,p,20);ship=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='transport');self.assertTrue(g.water_at(ship['x'],ship['y']));self.assertEqual(ship['capacity'],8)
  g.command(r,p,dict(action='train',kind='gunboat',producer=dock['id']));g.tick_production(r,p,20);self.assertTrue(any(e['kind']=='gunboat' and g.water_at(e['x'],e['y']) for e in r['entities']))
  with self.assertRaisesRegex(AssertionError,'water'):g.command(r,p,dict(action='move',ids=[ship['id']],x=shore['x'],y=shore['y']))
 def test_transport_can_board_near_its_producing_dock(self):
  r,p,shore=self.world();dock=g.entity(r,p,'dock',shore['x'],shore['y']);g.command(r,p,dict(action='train',kind='transport',producer=dock['id']));g.tick_production(r,p,20);ship=next(e for e in r['entities'] if e['kind']=='transport');places=g.shore_positions(r,ship,180);self.assertTrue(places);place=min(places,key=lambda point:g.dist(point,ship));troop=g.entity(r,p,'infantry',place['x'],place['y']);g.command(r,p,dict(action='board',ids=[troop['id']],transport=ship['id']));g.tick(r,.1);self.assertEqual(troop['embarked'],ship['id'])
 def test_board_sail_and_unload(self):
  r,p,shore=self.world();water=g.nearest_water(shore['x'],shore['y'],100);ship=g.entity(r,p,'transport',*water);troop=g.entity(r,p,'infantry',shore['x'],shore['y']);g.command(r,p,dict(action='board',ids=[troop['id']],transport=ship['id']));g.tick(r,.1);self.assertEqual(troop['embarked'],ship['id']);self.assertEqual(ship['passengers'],1)
  dest=next((dict(x=ship['x']-d,y=ship['y']) for d in [50,100,150] if g.water_at(ship['x']-d,ship['y'])),None);self.assertIsNotNone(dest);old=ship['x'];g.command(r,p,dict(action='move',ids=[ship['id']],**dest));g.tick(r,.5);self.assertNotEqual(ship['x'],old);self.assertTrue(g.water_at(ship['x'],ship['y']));g.command(r,p,dict(action='unload',transport=ship['id']));self.assertIsNone(troop['embarked']);self.assertFalse(g.water_at(troop['x'],troop['y']));self.assertEqual(ship['passengers'],0)
 def test_selected_distant_troop_walks_to_board(self):
  r,p,shore=self.world();ship=g.entity(r,p,'transport',*g.nearest_water(shore['x'],shore['y'],100));troop=g.entity(r,p,'infantry',shore['x']+180,shore['y']);self.assertFalse(g.water_at(troop['x'],troop['y']));g.command(r,p,dict(action='board',ids=[troop['id']],transport=ship['id']));initial=troop['x']
  for _ in range(120):
   g.tick(r,.25)
   if troop.get('embarked'):break
  self.assertNotEqual(troop['x'],initial);self.assertEqual(troop.get('embarked'),ship['id'])
 def test_board_requires_ship_near_a_shore(self):
  r,p,shore=self.world();ship=g.entity(r,p,'transport',3480,3440);troop=g.entity(r,p,'infantry',shore['x'],shore['y'])
  with self.assertRaisesRegex(AssertionError,'close to shore'):g.command(r,p,dict(action='board',ids=[troop['id']],transport=ship['id']))
 def test_eight_passengers_and_destroyed_transport(self):
  r,p,shore=self.world();ship=g.entity(r,p,'transport',*g.nearest_water(shore['x'],shore['y'],100));troops=[g.entity(r,p,'infantry',shore['x'],shore['y']) for _ in range(9)];g.command(r,p,dict(action='board',ids=[t['id'] for t in troops],transport=ship['id']));g.tick(r,.1);self.assertEqual(ship['passengers'],8);aboard=[t for t in troops if t.get('embarked')];ship['hp']=0;g.tick(r,.1);self.assertTrue(all(t['hp']<=0 for t in aboard));self.assertTrue(troops[-1]['hp']>0)
