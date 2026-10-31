import copy, unittest
import server as g
from test_game import room
class HistoricalUnlocks(unittest.TestCase):
 def setUp(self):
  self.r=room();self.r.update(_experimental_history=True,_map_geometry='continental');g.start(self.r);self.p=self.r['players'][0]
  for p in self.r['players']:p.update(auto_idle=False,autopilot=False,ai_next=999999)
  self.p['power']=20
 def age(self,key):self.p['historical']['era']=key
 def test_future_abandoned_sites_are_absent_in_all_earlier_eras(self):
  kinds={'abandoned_car','road_business','abandoned'}
  for era in ['stone','ancient','medieval','industrial']:
   self.age(era);g.spawn_future_abandoned_sites(self.r)
   self.assertFalse(any(o['kind'] in kinds for o in self.r['props']))
  self.age('future');g.spawn_future_abandoned_sites(self.r)
  sites=[o for o in self.r['props'] if o['kind'] in kinds]
  self.assertEqual(len(sites),15)
  self.assertTrue(all('parking' in o and 'road_access' in o for o in sites if o['kind']=='road_business'))
  for site in sites:
   self.assertFalse(g.water_at(site['x'],site['y'],r=self.r))
   self.assertFalse(g.road_lane(site['x'],site['y'],site['size']+80,r=self.r))
  before=[o['id'] for o in sites];g.spawn_future_abandoned_sites(self.r)
  self.assertEqual(before,[o['id'] for o in self.r['props'] if o['kind'] in kinds])
 def test_future_sites_wait_for_a_completed_era_advance(self):
  self.age('industrial');self.p['historical']['era_job']={'target':'future','progress':74,'seconds':75}
  g.tick(self.r,.5);self.assertFalse(self.r.get('_future_sites_spawned'))
  g.tick(self.r,.5);self.assertTrue(self.r.get('_future_sites_spawned'))
 def test_any_commander_can_trigger_shared_future_sites(self):
  self.r['players'][1]['historical']['era']='future'
  g.spawn_future_abandoned_sites(self.r)
  self.assertTrue(self.r.get('_future_sites_spawned'))
 def test_early_support_units_keep_their_period_equipment(self):
  self.age('ancient')
  artisan=g.entity(self.r,self.p,'engineer',900,2000);healer=g.entity(self.r,self.p,'medic',1000,2000)
  self.assertEqual(artisan['historical_role'],'artisan');self.assertEqual(healer['historical_role'],'healer')
  self.age('industrial')
  self.assertNotIn('historical_role',g.entity(self.r,self.p,'engineer',1100,2000))
  self.assertNotIn('historical_role',g.entity(self.r,self.p,'medic',1200,2000))
  self.assertEqual(artisan['historical_role'],'artisan');self.assertEqual(healer['historical_role'],'healer')
 def test_knights_require_medieval_and_research_and_train_at_barracks(self):
  self.age('ancient');self.p['tech']=['fieldcraft'];self.assertFalse(g.unlocked(self.p,'knight'))
  self.age('medieval');self.p['tech']=[];self.assertFalse(g.unlocked(self.p,'knight'))
  self.p['tech']=['fieldcraft'];self.p['historical']['resources'].update(food=1000,wood=1000,stone=1000,gold=1000,iron=1000);g.sync_historical_bank(self.p)
  barracks=g.entity(self.r,self.p,'barracks',900,2000)
  g.command(self.r,self.p,dict(action='train',kind='knight',producer=barracks['id']));g.tick_production(self.r,self.p,20)
  knight=next(e for e in self.r['entities'] if e['kind']=='knight')
  self.assertEqual(knight['historical_role'],'knight');self.assertEqual(knight['attack_range'],70)
  self.assertGreater(g.STATS['knight'][1],g.STATS['infantry'][1]);self.assertFalse(g.unlocked({},'knight'))
 def test_industrial_armor_retains_its_equipment_in_future(self):
  self.age('industrial')
  vehicles=[g.entity(self.r,self.p,k,900+i*120,2000) for i,k in enumerate(['tank','walker'])]
  self.age('future')
  self.assertTrue(all(e['historical_role']=='industrial_armor' for e in vehicles))
  self.assertNotIn('historical_role',g.entity(self.r,self.p,'tank',1200,2000))
 def test_existing_research_does_not_bypass_era(self):
  self.p['tech']=list(g.TECHS)
  for kind in ['tank','factory','fighter','hacker','solar','dock']:
   self.assertFalse(g.unlocked(self.p,kind),kind)
  with self.assertRaisesRegex(AssertionError,'Industrial'):g.command(self.r,self.p,dict(action='train',kind='tank'))
  self.age('industrial');self.assertTrue(g.unlocked(self.p,'tank'));self.assertFalse(g.unlocked(self.p,'hacker'))
  self.age('future');self.assertTrue(g.unlocked(self.p,'hacker'))
 def test_dock_and_transport_open_in_ancient_without_industry(self):
  self.age('ancient');self.assertNotIn('industry',self.p['tech']);self.assertTrue(g.unlocked(self.p,'dock'));self.assertTrue(g.unlocked(self.p,'transport'));self.assertFalse(g.unlocked(self.p,'gunboat'))
  self.p['historical']['resources']['gold']=5;before=self.p['wood'];g.command(self.r,self.p,dict(action='build',kind='dock',x=700,y=2000))
  self.assertEqual(self.p['historical']['resources']['gold'],5);self.assertEqual(self.p['riftglass'],0);self.assertEqual(self.p['wood'],before-180)
  self.age('medieval');self.assertTrue(g.unlocked(self.p,'gunboat'))
 def test_ancient_dock_produces_a_transport_and_keeps_its_age(self):
  self.age('ancient');self.p['historical']['resources'].update(gold=100,wood=500);g.sync_historical_bank(self.p,to_history=False)
  g.command(self.r,self.p,dict(action='build',kind='dock',x=700,y=2000))
  dock=next(e for e in self.r['entities'] if e['kind']=='dock' and e['owner']==self.p['id'])
  g.tick(self.r,20)
  g.command(self.r,self.p,dict(action='train',kind='transport',producer=dock['id']))
  g.tick_production(self.r,self.p,30)
  ship=next(e for e in self.r['entities'] if e['kind']=='transport' and e['owner']==self.p['id'])
  self.assertTrue(g.water_at(ship['x'],ship['y'],r=self.r));self.assertEqual(ship['capacity'],8)
  self.age('medieval');self.assertEqual(dock['era_created'],'ancient')
 def test_early_research_uses_gold_and_era_gate_is_atomic(self):
  for kind,x,y in [('academy',900,2000),('barracks',900,2200)]:g.entity(self.r,self.p,kind,x,y)
  self.p['gathered']['wood']=100;self.p['historical']['resources']['gold']=50;before=copy.deepcopy(self.p)
  with self.assertRaisesRegex(AssertionError,'Ancient'):g.command(self.r,self.p,dict(action='research',tech='fieldcraft'))
  self.assertEqual(before,self.p)
  self.age('ancient');before=self.p['historical']['resources']['gold'];g.command(self.r,self.p,dict(action='research',tech='fieldcraft'));self.assertEqual(self.p['historical']['resources']['gold'],before-10);self.assertEqual(self.p['riftglass'],0)
  g.tick_research(self.r,self.p,30);self.assertIn('fieldcraft',self.p['tech']);self.assertTrue(g.unlocked(self.p,'medic'));self.assertFalse(g.unlocked(self.p,'engineer'))
 def test_failed_payment_has_no_partial_charge(self):
  self.age('ancient');self.p['historical']['resources']['stone']=99;before=copy.deepcopy(self.p)
  with self.assertRaisesRegex(AssertionError,'stone'):g.command(self.r,self.p,dict(action='build',kind='dock',x=700,y=2000))
  self.assertEqual(before,self.p)
 def test_extra_bases_still_need_research(self):
  self.age('medieval');self.assertFalse(g.unlocked(self.p,'core'));self.p['tech']=['fieldcraft'];tech=g.tech_for(self.p,'base_expansion');self.assertEqual(tech['requires'],['fieldcraft']);self.p['tech'].append('base_expansion');self.assertTrue(g.unlocked(self.p,'core'))
 def test_public_reasons_and_costs_match_rules(self):
  view=g.view(self.r,self.p);self.assertIn('Industrial',view['lock_reasons']['tank']);self.assertEqual(view['cost_catalog']['academy'],dict(wood=140,stone=120));self.assertNotIn('riftglass',view['cost_catalog']['academy']);self.assertEqual(view['tech_catalog']['base_expansion']['requires'],['fieldcraft'])
  self.age('future');view=g.view(self.r,self.p);self.assertIn('riftglass',view['cost_catalog']['hacker']);self.assertNotIn('gold',view['cost_catalog']['hacker']);self.assertEqual(g.TECHS['base_expansion']['requires'],['industry'])
 def test_classic_rules_and_costs_unchanged(self):
  p=dict(tech=['industry']);self.assertTrue(g.unlocked(p,'dock'));self.assertFalse(g.unlocked(p,'tank'));self.assertEqual(g.commander_costs(p,g.material_costs('academy')),g.material_costs('academy'));self.assertEqual(g.tech_for(p,'base_expansion')['requires'],['industry'])

class HistoricalEarlyGame(unittest.TestCase):
 def test_early_defenses_do_not_require_unavailable_electricity(self):
  r=room();r.update(_experimental_history=True,_map_geometry='continental');g.start(r);p=r['players'][0];p.update(auto_idle=False,autopilot=False,ai_next=999999);p['historical']['era']='ancient'
  for i,kind in enumerate(['academy','barracks','turret','turret']):g.entity(r,p,kind,800+i*200,2000)
  g.tick(r,.1);self.assertEqual(p['power'],20)
 def test_ai_builds_early_barracks_instead_of_locked_reactor(self):
  r=room(1);r.update(_experimental_history=True,_map_geometry='continental');g.start(r);p=next(p for p in r['players'] if p.get('bot'));g.commander_ai(r,p)
  self.assertTrue(any(e['owner']==p['id'] and e['kind']=='barracks' for e in r['entities']));self.assertFalse(any(e['owner']==p['id'] and e['kind']=='power' for e in r['entities']))
