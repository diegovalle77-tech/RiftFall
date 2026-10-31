import unittest
import server as g
from test_game import room,start_unlocked
class Navigation(unittest.TestCase):
 def setUp(self):
  self.r=room();start_unlocked(self.r)
  for p in self.r['players']:p.update(auto_idle=False,autopilot=False,ai_next=99999)
  self.p=self.r['players'][0]
 def test_ground_unit_detours_around_cliff(self):
  unit=g.entity(self.r,self.p,'jeep',2400,2400);unit['goal']=[3700,2400];path=g.navigation_path(self.r,unit,unit['goal']);self.assertTrue(path);self.assertTrue(any(abs(y-2400)>250 for x,y in path))
  for _ in range(240):
   g.tick(self.r,.1);self.assertFalse(g.cliff_at(self.r,unit['x'],unit['y']))
  self.assertLess(g.dist(unit,dict(x=3700,y=2400)),40)
 def test_buildings_cannot_occupy_cliff(self):
  self.assertTrue(g.cliff_at(self.r,3000,2400));self.assertFalse(g.clear_footprint(self.r,'barracks',3000,2400))
 def test_aircraft_ignores_cliffs_and_private_route_not_exposed(self):
  unit=g.entity(self.r,self.p,'fighter',2400,2400);self.assertEqual(g.navigation_destination(self.r,unit,[3700,2400]),[3700,2400]);unit['_route']=[(1,2)];self.r['_nav_static']={(1,2):(True,False)};v=g.view(self.r,self.p);self.assertNotIn('_nav_static',v);self.assertNotIn('_route',next(e for e in v['entities'] if e['id']==unit['id']))

class MountainRoads(unittest.TestCase):
 def test_main_roads_avoid_impassable_mountains(self):
  for route in g.ROAD_ROUTES:
   for a,b in zip(route,route[1:]):
    steps=max(1,int(g.math.hypot(b[0]-a[0],b[1]-a[1])/20))
    for i in range(steps+1):
     x=a[0]+(b[0]-a[0])*i/steps;y=a[1]+(b[1]-a[1])*i/steps
     self.assertFalse(g.cliff_at({},x,y),(x,y))
