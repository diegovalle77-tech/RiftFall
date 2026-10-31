import unittest
import server as g
from test_game import room

class StorageTests(unittest.TestCase):
 def setup_world(self):
  r=room();g.start(r)
  for p in r['players']:p.update(autopilot=False,auto_idle=False,ai_next=99999)
  p=r['players'][0];h=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='harvester');core=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='core')
  return r,p,h,core
 def test_new_capacity_and_gathering_past_old_limit(self):
  r,p,h,core=self.setup_world();n=next(n for n in r['nodes'] if n['kind']=='metal' and n.get('parking_spots'));anchor=g.mining_anchor(r,n,h);h.update(x=anchor['x'],y=anchor['y'],cargo=80,load_type='metal',resource_target=n['id']);g.tick(r,.5)
  self.assertEqual(h['cargo'],90);self.assertFalse(h['returning']);self.assertEqual(h['cargo_capacity'],750)
  h['cargo']=749;g.tick(r,.5);self.assertEqual(h['cargo'],750)
 def test_partial_unload_then_warehouse_accepts_remaining(self):
  r,p,h,core=self.setup_world();p['metal']=1490;h.update(x=core['x'],y=core['y'],cargo=750,load_type='metal');g.tick(r,.1)
  self.assertEqual(p['metal'],1500);self.assertEqual(h['cargo'],740);self.assertTrue(h['storage_blocked'])
  metal=p['metal'];g.tick(r,.1);self.assertEqual(h['cargo'],740);self.assertEqual(p['metal'],metal)
  warehouse=g.entity(r,p,'warehouse',core['x']+160,core['y']);h.update(x=warehouse['x'],y=warehouse['y']);g.tick(r,.1)
  self.assertEqual(p['metal'],2240);self.assertEqual(h['cargo'],0);self.assertFalse(h['storage_blocked']);self.assertEqual(g.storage_capacity(r,p),6500)
  g.entity(r,p,'warehouse',800,300);self.assertEqual(g.storage_capacity(r,p),11500)
  warehouse['hp']=0;self.assertEqual(g.storage_capacity(r,p),6500)
 def test_stock_spacing_and_respawn(self):
  r,p,h,core=self.setup_world()
  for n in r['nodes']:
   self.assertEqual(n['stock'],g.deposit_stock(n['kind']))
   self.assertTrue(all(g.dist(n,dict(x=x,y=y))>=650 for x,y in g.START_BASES))
  for kind in ['metal','wood','riftglass']:
   self.assertTrue(any(n['kind']==kind and 650<=g.dist(n,core)<=1100 for n in r['nodes']))
  for i,n in enumerate(r['nodes']):
   self.assertTrue(all(g.dist(n,other)>=400 for other in r['nodes'][i+1:]))
  old=r['nodes'][0];old['stock']=0;g.replenish_deposits(r);self.assertEqual(r['nodes'][-1]['stock'],g.deposit_stock(r['nodes'][-1]['kind']))
 def test_build_warehouse_before_research(self):
  r,p,h,core=self.setup_world();g.command(r,p,dict(action='build',kind='warehouse',x=500,y=270));g.tick(r,12);self.assertEqual(g.storage_capacity(r,p),6500)
