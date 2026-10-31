import unittest
import server as g
from test_game import room,start_unlocked
class WaterRules(unittest.TestCase):
 def setUp(self):
  self.r=room();start_unlocked(self.r);self.p=self.r['players'][0];self.p.update(credits=10000,metal=1000,wood=1000,riftglass=1000);self.x,self.y=g.river_point(.52)
 def test_water_construction_requires_shore_dock(self):
  self.r['props']=[];self.r['nodes']=[]  # Isolate shoreline rules from random obstacles.
  self.assertTrue(g.water_at(self.x,self.y))
  with self.assertRaises(AssertionError):g.command(self.r,self.p,dict(action='build',kind='power',x=self.x,y=self.y))
  with self.assertRaises(AssertionError):g.command(self.r,self.p,dict(action='build',kind='dock',x=500,y=500))
  with self.assertRaises(AssertionError):g.command(self.r,self.p,dict(action='build',kind='dock',x=self.x,y=self.y))
  g.command(self.r,self.p,dict(action='build',kind='dock',x=self.x+285,y=self.y));g.tick(self.r,12)
  g.command(self.r,self.p,dict(action='build',kind='power',x=self.x,y=self.y))
  dock=next(e for e in self.r['entities'] if e['kind']=='dock');dock['hp']=0
  self.assertFalse(g.water_building(self.r,self.p,'barracks',self.x,self.y+130))
 def test_only_tanks_cross_open_water(self):
  for kind in ['infantry','engineer','hacker','harvester','walker','scout','jeep']:
   self.assertFalse(g.passable_water(self.r,dict(kind=kind),self.x,self.y),kind)
  for kind in ['tank','fighter','bomber']:self.assertTrue(g.passable_water(self.r,dict(kind=kind),self.x,self.y))
 def test_bridge_must_be_intact(self):
  bridge=dict(kind='bridge',x=self.x,y=self.y,hp=650);self.r['props'].append(bridge)
  self.assertTrue(g.passable_water(self.r,dict(kind='infantry'),self.x,self.y));bridge['hp']=0
  self.assertFalse(g.passable_water(self.r,dict(kind='infantry'),self.x,self.y));self.assertTrue(g.passable_water(self.r,dict(kind='tank'),self.x,self.y))
if __name__=='__main__':unittest.main()
