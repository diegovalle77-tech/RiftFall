import unittest
import server as g
from test_game import room
class SmartCombat74(unittest.TestCase):
 def world(self,historical=False):
  r=room();r.update(_experimental_history=historical,_map_geometry='continental' if historical else 'frontier');g.start(r)
  for p in r['players']:p.update(auto_idle=False,autopilot=False,ai_next=999999)
  r.update(fires=[],nodes=[],props=[],hills=[],cliffs=[],weather_mode='sunny');r['entities']=[e for e in r['entities'] if e['kind']=='core']
  return r,*r['players'][:2]
 def test_stone_engineer_research_and_training(self):
  r,p,q=self.world(True);g.entity(r,p,'academy',1000,2000);g.entity(r,p,'barracks',1200,2000)
  self.assertIn('Engineering Basics',g.unlock_reason(p,'engineer'));p['tech']=['stone_tools'];p['gathered']={'wood':100};p['historical']['resources'].update(food=1000,wood=1000,stone=1000,iron=1000);g.sync_historical_bank(p,to_history=False)
  self.assertIsNone(g.research_reason(r,p,'engineering_basics'));g.command(r,p,dict(action='research',tech='engineering_basics'));g.tick_research(r,p,30);self.assertTrue(g.unlocked(p,'engineer'));g.command(r,p,dict(action='train',kind='engineer'));g.tick_production(r,p,10);e=next(e for e in r['entities'] if e['kind']=='engineer');self.assertEqual(e['era_created'],'stone');self.assertEqual(e['historical_role'],'artisan')
 def test_engineer_availability_excludes_busy_and_enemy(self):
  r,p,q=self.world();a=g.entity(r,p,'engineer',1000,2000);b=g.entity(r,p,'engineer',1100,2000);g.entity(r,q,'engineer',1200,2000);b['reclaim_target']='site'
  self.assertEqual(g.engineer_summary(r,p),dict(total=2,available=1,available_ids=[a['id']]));a['goal']=[1400,2000];self.assertEqual(g.view(r,p)['engineers']['available'],0)
 def test_auto_repair_and_manual_override(self):
  r,p,q=self.world();e=g.entity(r,p,'engineer',1000,2000);b=g.entity(r,p,'barracks',1500,2000);b['hp']=200;p.update(metal=1000,wood=1000)
  self.assertEqual(g.engineer_repair_coverage(p),1200);g.tick(r,.1);self.assertEqual(e['repair_target'],b['id']);self.assertTrue(e['moving'])
  e.update(x=1450,y=2000);g.tick(r,.5);self.assertTrue(e['repairing']);self.assertGreater(b['hp'],200);self.assertEqual(g.engineer_summary(r,p)['available'],0)
  g.command(r,p,dict(action='move',ids=[e['id']],x=800,y=2000));g.tick(r,.1);self.assertIsNone(e.get('repair_target'));self.assertLess(e['x'],1450)
 def test_engineer_coverage_scales_with_tower(self):
  r,p,q=self.world();p['tech']=['targeting'];self.assertEqual(g.engineer_repair_coverage(p),1500);e=g.entity(r,p,'engineer',1000,2000);self.assertEqual(next(x for x in g.view(r,p)['entities'] if x['id']==e['id'])['repair_coverage'],1500)
 def test_idle_infantry_defends_at_detection_radius(self):
  r,p,q=self.world();a=g.entity(r,p,'infantry',1000,2000);b=g.entity(r,q,'infantry',1240,2000);g.tick(r,.1);self.assertEqual(a['combat_target_id'],b['id']);self.assertTrue(a['moving']);self.assertGreater(a['x'],1000)
 def test_ai_intercepts_infantry_then_resumes_hq(self):
  r,p,q=self.world();a=g.entity(r,p,'tank',1000,2000);hq=g.entity(r,q,'core',1700,2000);b=g.entity(r,q,'infantry',1120,2000);g.command(r,p,dict(action='attack',ids=[a['id']],target=hq['id']),automatic=True) if False else None
  a.update(attack=hq['id'],attack_order='ai');g.tick(r,.1);self.assertEqual(a['combat_target_id'],b['id']);self.assertEqual(a['attack'],hq['id']);b['hp']=0;g.tick(r,.1);self.assertEqual(a['combat_target_id'],hq['id'])
 def test_ai_intercepts_tower(self):
  r,p,q=self.world();a=g.entity(r,p,'tank',1000,2000);hq=g.entity(r,q,'core',1900,2000);b=g.entity(r,q,'turret',1200,2000);a.update(attack=hq['id'],attack_order='ai');g.tick(r,.1);self.assertEqual(a['combat_target_id'],b['id'])
 def test_manual_retreat_respected(self):
  r,p,q=self.world();a=g.entity(r,p,'infantry',1000,2000);g.entity(r,q,'infantry',1100,2000);g.command(r,p,dict(action='move',ids=[a['id']],x=800,y=2000));g.tick(r,.1);self.assertLess(a['x'],1000);self.assertIsNotNone(a['goal'])
 def test_captured_target_stops_friendly_fire(self):
  r,p,q=self.world();a=g.entity(r,p,'infantry',1000,2000);b=g.entity(r,q,'infantry',1100,2000);a['attack']=b['id'];b['owner']=p['id'];g.tick(r,.1);self.assertIsNone(a['attack']);self.assertEqual(b['hp'],b['maxhp'])
 def test_human_autopilot_removed(self):
  r,p,q=self.world();p['auto_idle']=True;r['elapsed']=100;g.tick(r,.1);self.assertFalse(p['autopilot']);self.assertFalse(p['auto_idle'])
  with self.assertRaisesRegex(AssertionError,'removed'):g.command(r,p,dict(action='autopilot',enabled=True))
 def test_future_riftglass_spawn_once_and_early_costs(self):
  r,p,q=self.world(True)
  for era in ['stone','ancient','medieval','industrial']:
   p['historical']['era']=era
   for kind in g.MATERIAL_COSTS:self.assertFalse(g.commander_costs(p,g.material_costs(kind,p)).get('riftglass'))
   for key in g.TECHS:self.assertFalse(g.tech_for(p,key)['costs'].get('riftglass'))
   g.spawn_future_riftglass(r);self.assertFalse(r['nodes'])
  p['historical']['era']='future';g.spawn_future_riftglass(r);g.spawn_future_riftglass(r);self.assertEqual(len(r['nodes']),2);self.assertTrue(all(n['kind']=='riftglass' for n in r['nodes']))
