import unittest
import server as g
from test_game import room
class Specialists(unittest.TestCase):
 def setUp(self):
  self.r=room();g.start(self.r);self.p=self.r['players'][0];self.enemy=self.r['players'][1]
  for p in self.r['players']:p.update(auto_idle=False,autopilot=False,ai_next=99999,tech=list(g.TECHS))
  self.p.update(credits=10000,metal=1000,wood=1000,riftglass=1000)
 def site(self):return next(o for o in self.r['props'] if o['kind']=='abandoned')
 def test_city_generation_and_seed_variation(self):
  sites=[o for o in self.r['props'] if o['kind']=='abandoned'];self.assertEqual(len(sites),6);self.assertEqual(len({o['id'] for o in self.r['props']}),len(self.r['props']));self.assertTrue(all(o['building_kind'] in g.FOOTPRINTS for o in sites));self.assertNotEqual([(s['x'],s['y']) for s in sites],[(s['x'],s['y']) for s in g.scenery() if s['kind']=='abandoned'])
 def test_reclaim_needs_engineer_and_research(self):
  site=self.site()
  with self.assertRaisesRegex(AssertionError,'engineers first'):g.command(self.r,self.p,dict(action='reclaim',ids=[],target=site['id']))
  e=g.entity(self.r,self.p,'engineer',site['x']+80,site['y']);self.p['tech']=[]
  with self.assertRaisesRegex(AssertionError,'Field Operations'):g.command(self.r,self.p,dict(action='reclaim',ids=[e['id']],target=site['id']))
 def test_capture_waits_for_engineer_and_transfers_building(self):
  site=self.site();e=g.entity(self.r,self.p,'engineer',site['x']+80,site['y']);before=self.p['metal'];g.command(self.r,self.p,dict(action='reclaim',ids=[e['id']],target=site['id']));self.assertLess(self.p['metal'],before);g.tick(self.r,10);self.assertIn(site,self.r['props']);self.assertGreater(site['rebuild']['progress'],0);g.tick(self.r,20.1);self.assertNotIn(site,self.r['props']);self.assertTrue(any(b['owner']==self.p['id'] and b['kind']==site['building_kind'] and g.dist(b,site)<1 for b in self.r['entities']))
 def test_lost_engineer_pauses_and_resumes_without_second_payment(self):
  site=self.site();e=g.entity(self.r,self.p,'engineer',site['x']+80,site['y']);g.command(self.r,self.p,dict(action='reclaim',ids=[e['id']],target=site['id']));g.tick(self.r,5);e['hp']=0;progress=site['rebuild']['progress'];g.tick(self.r,1);self.assertEqual(site['rebuild']['progress'],progress);replacement=g.entity(self.r,self.p,'engineer',site['x']+80,site['y']);credits=self.p['credits'];g.command(self.r,self.p,dict(action='reclaim',ids=[replacement['id']],target=site['id']));self.assertEqual(self.p['credits'],credits)
 def test_bridge_wreck_survives_and_can_be_rebuilt(self):
  bridge=next(p for p in self.r['props'] if p['kind']=='bridge');bridge['hp']=0;g.tick(self.r,.1);self.assertIn(bridge,self.r['props']);self.assertTrue(bridge['wrecked']);e=g.entity(self.r,self.p,'engineer',bridge['x']-95,bridge['y']);g.command(self.r,self.p,dict(action='reclaim',ids=[e['id']],target=bridge['id']));g.tick(self.r,30.1);self.assertEqual(bridge['hp'],bridge['maxhp']);self.assertNotIn('wrecked',bridge)
 def test_abandoned_footprints_block_new_buildings(self):
  site=self.site();self.assertFalse(g.clear_footprint(self.r,'barracks',site['x'],site['y']));self.assertTrue(g.clear_footprint(self.r,site['building_kind'],site['x'],site['y'],site['id']))
 def test_hack_timed_takeover_and_old_owner_loses_control(self):
  h=g.entity(self.r,self.p,'hacker',800,800);target=g.entity(self.r,self.enemy,'medic',850,800);g.command(self.r,self.p,dict(action='hack',ids=[h['id']],target=target['id']));g.tick(self.r,5);self.assertEqual(target['owner'],self.enemy['id']);g.tick(self.r,7.1);self.assertEqual(target['owner'],self.p['id']);g.command(self.r,self.p,dict(action='move',ids=[target['id']],x=950,y=900));goal=target['goal'];g.command(self.r,self.enemy,dict(action='move',ids=[target['id']],x=100,y=100));self.assertEqual(target['goal'],goal)
 def test_manual_move_interrupts_hack(self):
  h=g.entity(self.r,self.p,'hacker',800,800);target=g.entity(self.r,self.enemy,'medic',850,800);g.command(self.r,self.p,dict(action='hack',ids=[h['id']],target=target['id']));g.tick(self.r,3);progress=target['hack']['progress'];g.command(self.r,self.p,dict(action='move',ids=[h['id']],x=100,y=100));g.tick(self.r,15);self.assertEqual(target['owner'],self.enemy['id']);self.assertEqual(target['hack']['progress'],progress)
 def test_hackers_cannot_take_buildings_or_friendly_units(self):
  h=g.entity(self.r,self.p,'hacker',800,800)
  for target in [g.entity(self.r,self.enemy,'core',850,800),g.entity(self.r,self.p,'infantry',850,800)]:
   with self.assertRaisesRegex(AssertionError,'mobile unit'):g.command(self.r,self.p,dict(action='hack',ids=[h['id']],target=target['id']))
if __name__=='__main__':unittest.main()
