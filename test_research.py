import unittest
import server as g
from test_game import room
class ResearchTests(unittest.TestCase):
 def setUp(self):
  self.r=room();g.start(self.r);self.p=self.r['players'][0]
  for p in self.r['players']:p.update(auto_idle=False,autopilot=False,ai_next=99999)
  self.p.update(credits=10000,metal=1000,wood=1000,riftglass=1000,power=100)
  self.facility=g.entity(self.r,self.p,'power',420,260);g.entity(self.r,self.p,'academy',600,450)
 def test_academy_is_basic_and_required_for_research(self):
  self.assertTrue(g.unlocked(self.p,'academy'));self.p['gathered']={'metal':100}
  for e in self.r['entities']:
   if e['owner']==self.p['id'] and e['kind']=='academy':e['hp']=0
  self.assertIn('academy',g.research_reason(self.r,self.p,'industry'))
 def gathered(self,amount=100):self.p['gathered']={'metal':amount,'wood':0,'riftglass':0}
 def research(self,key):g.command(self.r,self.p,dict(action='research',tech=key))
 def test_locked_build_and_unit_cannot_bypass_research(self):
  before=self.p['credits'];metal=self.p['metal']
  with self.assertRaisesRegex(AssertionError,'Industry'):g.command(self.r,self.p,dict(action='build',kind='factory',x=260,y=110))
  g.entity(self.r,self.p,'factory',600,260)
  with self.assertRaisesRegex(AssertionError,'Armored'):g.command(self.r,self.p,dict(action='train',kind='tank'))
  self.assertEqual(self.p['credits'],before);self.assertEqual(self.p['metal'],metal)
 def test_starting_supplies_do_not_satisfy_gathering_gate(self):
  with self.assertRaisesRegex(AssertionError,'gathered'):self.research('industry')
  self.assertIsNone(self.p['research']);self.assertEqual(self.p['credits'],10000)
 def test_harvester_deliveries_count_toward_progress(self):
  h=next(e for e in self.r['entities'] if e['owner']==self.p['id'] and e['kind']=='harvester');h.update(x=260,y=260,cargo=g.HARVESTER_CAPACITY,load_type='metal')
  self.p['metal']=100;g.tick(self.r,.1);self.assertEqual(self.p['gathered']['metal'],750);self.research('industry');self.assertEqual(self.p['research']['key'],'industry')
 def test_timed_completion_cost_once_and_reject_duplicate(self):
  self.gathered();before=dict(self.p);self.research('industry');self.assertNotIn('industry',self.p['tech'])
  for resource in ['metal','wood','riftglass']:self.assertEqual(self.p[resource],before[resource]-g.TECHS['industry'][resource])
  after=self.p['metal']
  with self.assertRaisesRegex(AssertionError,'already running'):self.research('fieldcraft')
  self.assertEqual(self.p['metal'],after);g.tick_research(self.r,self.p,29);self.assertNotIn('industry',self.p['tech']);g.tick_research(self.r,self.p,1);self.assertIn('industry',self.p['tech']);self.assertIsNone(self.p['research'])
  with self.assertRaisesRegex(AssertionError,'already completed'):self.research('industry')
 def test_missing_or_enemy_facility_not_accepted(self):
  self.gathered();self.facility['owner']=self.r['players'][1]['id']
  with self.assertRaisesRegex(AssertionError,'deployed power'):self.research('industry')
 def test_research_pauses_for_lost_facility_or_power(self):
  self.gathered();self.research('industry');g.tick_research(self.r,self.p,5);self.facility['packed']=True;g.tick_research(self.r,self.p,50);self.assertEqual(self.p['research']['progress'],5);self.assertTrue(self.p['research']['paused'])
  self.facility['packed']=False;self.p['power']=-1;g.tick_research(self.r,self.p,50);self.assertEqual(self.p['research']['progress'],5)
  self.p['power']=20;g.tick_research(self.r,self.p,25);self.assertIn('industry',self.p['tech'])
 def test_full_dependency_tree_and_per_player_unlocks(self):
  self.gathered();g.entity(self.r,self.p,'barracks',260,420)
  with self.assertRaisesRegex(AssertionError,'Complete'):self.research('aviation')
  for key in ['industry','fieldcraft','armor','aviation','stormtech','base_expansion']:
   facility=g.TECHS[key]['facility']
   if not g.research_facility(self.r,self.p,facility):g.entity(self.r,self.p,facility,800,800)
   self.research(key);g.tick_research(self.r,self.p,g.TECHS[key]['seconds'])
  self.assertTrue(all(g.unlocked(self.p,k) for k in g.STATS if k!='knight'));self.assertFalse(g.unlocked(self.r['players'][1],'factory'))
 def test_insufficient_materials_do_not_partially_charge(self):
  self.gathered();self.p['riftglass']=0;before={k:self.p[k] for k in ['metal','wood','riftglass']}
  with self.assertRaisesRegex(AssertionError,'riftglass'):self.research('industry')
  self.assertEqual(before,{k:self.p[k] for k in before})
 def test_ai_obeys_same_research_gate(self):
  self.p.update(bot=True,autopilot=True,metal=300,wood=300,riftglass=300);self.r['elapsed']=40;self.p['auto_idle']=True;g.entity(self.r,self.p,'barracks',260,420);g.commander_ai(self.r,self.p)
  self.assertFalse(any(e['kind']=='factory' and e['owner']==self.p['id'] for e in self.r['entities']));self.assertIsNone(self.p['research'])
  self.gathered();g.commander_ai(self.r,self.p);self.assertEqual(self.p['research']['key'],'industry')
if __name__=='__main__':unittest.main()
