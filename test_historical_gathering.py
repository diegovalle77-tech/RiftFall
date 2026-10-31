import unittest
import server as g
from test_game import room
class HistoricalGathering(unittest.TestCase):
 def setUp(self):
  self.r=room();self.r['_experimental_history']=True;g.start(self.r);self.p=self.r['players'][0]
  for p in self.r['players']:p.update(auto_idle=False,autopilot=False,ai_next=999999)
  self.h=next(e for e in self.r['entities'] if e['owner']==self.p['id'] and e['kind']=='harvester');self.core=next(e for e in self.r['entities'] if e['owner']==self.p['id'] and e['kind']=='core')
 def test_history_resource_delivery_and_capacity(self):
  self.p['historical']['resources']['food']=1490;self.h.update(x=self.core['x'],y=self.core['y'],cargo=40,cargo_loads={'food':40},load_type='food',storage_blocked=True);g.tick(self.r,.1)
  self.assertEqual(self.p['historical']['resources']['food'],1500);self.assertEqual(self.h['cargo'],30);self.assertTrue(self.h['storage_blocked'])
 def test_early_riftglass_rejected_but_late_allowed(self):
  with self.assertRaisesRegex(AssertionError,'Future Age'):g.command(self.r,self.p,dict(action='gather',ids=[self.h['id']],resource='riftglass'))
  self.p['historical']['era']='future';g.command(self.r,self.p,dict(action='gather',ids=[self.h['id']],resource='riftglass'));self.assertEqual(self.h['gather'],'riftglass')
 def test_manual_food_order_depletes_finite_node(self):
  node={'id':'berry-test','kind':'food','x':1300,'y':1100,'stock':1,'finite':True,'hp':50,'maxhp':50,'owner':None};self.r['nodes'].append(node)
  self.h.update(x=1300,y=1100,cargo=0,cargo_loads={},goal=None);g.command(self.r,self.p,dict(action='gather',ids=[self.h['id']],resource='food',node=node['id']));g.tick(self.r,.1)
  self.assertEqual(self.h['cargo_loads']['food'],1);self.assertFalse(any(n['id']=='berry-test' for n in self.r['nodes']));self.assertFalse(any(n['kind']=='food' for n in self.r.get('pending_deposits',[])))
 def test_original_mode_rejects_history_resource(self):
  self.r['_experimental_history']=False
  with self.assertRaisesRegex(AssertionError,'Unknown gathering resource'):g.command(self.r,self.p,dict(action='gather',ids=[self.h['id']],resource='gold'))
if __name__=='__main__':unittest.main()
