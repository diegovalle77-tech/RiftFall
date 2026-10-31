import unittest
import server as g
from test_game import room
class BuildingInteractions(unittest.TestCase):
 def setUp(self):
  self.r=room();g.start(self.r);self.p=self.r['players'][0];self.p.update(credits=10000,metal=1000,wood=1000,riftglass=1000,power=100)
 def test_repair_owned_building_and_cost(self):
  b=next(e for e in self.r['entities'] if e['owner']==self.p['id'] and e['kind']=='core');b['hp']-=101
  before=self.p['metal'];g.command(self.r,self.p,dict(action='repair',building=b['id']));self.assertEqual(b['hp'],b['maxhp']);self.assertEqual(before-self.p['metal'],6)
  with self.assertRaises(AssertionError):g.command(self.r,self.p,dict(action='repair',building=b['id']))
 def test_enemy_building_cannot_be_repaired(self):
  b=next(e for e in self.r['entities'] if e['owner']!=self.p['id'] and e['kind']=='core');b['hp']-=100
  with self.assertRaises(AssertionError):g.command(self.r,self.p,dict(action='repair',building=b['id']))
 def test_selected_producer_and_reject_wrong_building(self):
  first=g.entity(self.r,self.p,'barracks',300,350);second=g.entity(self.r,self.p,'barracks',1000,1000)
  g.command(self.r,self.p,dict(action='train',kind='infantry',producer=second['id']));self.assertEqual(second['production'][0]['kind'],'infantry');g.tick_production(self.r,self.p,6);unit=self.r['entities'][-1];self.assertLess(g.dist(unit,second),100);self.assertFalse(list(g.make_occupancy(self.r).blockers(unit,unit['x'],unit['y'])));self.assertGreater(g.dist(unit,first),500)
  with self.assertRaises(AssertionError):g.command(self.r,self.p,dict(action='train',kind='fighter',producer=second['id']))
 def test_frontier_design_identity(self):
  r=room();r['ai_enabled']=True;g.start(r);self.assertEqual([p['design'] for p in r['players'] if p.get('bot')],['ironwatch','nightfall'])
class IdleAndMap(unittest.TestCase):
 def test_human_idle_never_enables_autopilot(self):
  r=room();g.start(r);p=r['players'][0];before=len(r['entities'])
  g.tick(r,31);self.assertFalse(p['autopilot']);self.assertFalse(p['auto_idle']);self.assertEqual(len(r['entities']),before)
  g.command(r,p,dict(action='activity'));self.assertFalse(p['autopilot'])
 def test_idle_assist_can_be_disabled(self):
  r=room();g.start(r);p=r['players'][0];g.command(r,p,dict(action='autopilot',enabled=False));g.tick(r,31);self.assertFalse(p['autopilot'])
 def test_assign_exact_deposit(self):
  r=room();g.start(r);p=r['players'][0];h=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='harvester');node=r['nodes'][2]
  g.command(r,p,dict(action='gather',ids=[h['id']],resource=node['kind'],node=node['id']));self.assertEqual(h['resource_target'],node['id']);g.tick(r,.1);self.assertTrue(h['moving'])
class PlacementTests(unittest.TestCase):
 def test_overlapping_build_rejected_without_charge(self):
  r=room();g.start(r);p=r['players'][0];p['tech']=['industry'];before=p['credits']
  with self.assertRaises(AssertionError):g.command(r,p,dict(action='build',kind='factory',x=320,y=260))
  self.assertEqual(p['credits'],before)
  g.command(r,p,dict(action='build',kind='factory',x=420,y=260));self.assertTrue(g.clear_footprint(r,'power',260,110))
 def test_deploy_overlap_rejected(self):
  r=room();g.start(r);p=r['players'][0];b=g.entity(r,p,'factory',420,260);g.command(r,p,dict(action='pack',ids=[b['id']]));b.update(x=260,y=260)
  with self.assertRaises(AssertionError):g.command(r,p,dict(action='pack',ids=[b['id']]))
  self.assertTrue(b['packed']);b.update(x=420,y=260);g.command(r,p,dict(action='pack',ids=[b['id']]));self.assertFalse(b['packed'])
if __name__=='__main__':unittest.main()
