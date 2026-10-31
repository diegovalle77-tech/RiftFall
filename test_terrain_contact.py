import unittest
import server as g
from test_game import room,start_unlocked
class TerrainContact(unittest.TestCase):
 def test_crater_deforms_individual_contacts(self):
  r={'craters':[],'props':[]};e=dict(x=1000,y=1000,angle=0);before=g.terrain_contact(r,e);height=g.terrain_height(r,1018,1000);r['craters']=[dict(x=1018,y=1000,size=15,depth=12)];self.assertLess(g.terrain_height(r,1018,1000),height-11);after=g.terrain_contact(r,e);self.assertNotEqual(before['pitch'],after['pitch']);self.assertGreater(after['rough'],before['rough'])
 def test_bridge_contacts_flatten_and_surfaces_match_weather(self):
  r={'craters':[],'props':[],'weather':{'kind':'rain','snow':0}};e=dict(x=1000,y=1000,angle=0);self.assertEqual(g.terrain_contact(r,e)['surface'],'mud');r['weather']['snow']=.4;self.assertEqual(g.terrain_contact(r,e)['surface'],'snow');r['props']=[dict(kind='bridge',x=1000,y=1000,hp=650)];contact=g.terrain_contact(r,e);self.assertEqual((contact['pitch'],contact['roll'],contact['rough']),(0,0,0));self.assertEqual(contact['surface'],'bridge')
 def test_travel_only_advances_with_actual_movement(self):
  r=room();start_unlocked(r)
  for p in r['players']:p.update(auto_idle=False,autopilot=False,ai_next=99999)
  unit=g.entity(r,r['players'][0],'jeep',1000,1000);unit['goal']=[1200,1000];g.tick(r,.2);self.assertGreater(unit['travel'],0);distance=unit['travel'];unit['goal']=None;g.tick(r,.2);self.assertEqual(unit['travel'],distance)
