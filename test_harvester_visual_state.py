import unittest
import server as g
from test_game import room,start_unlocked
class HarvesterVisualState(unittest.TestCase):
 def test_work_state_and_unloading(self):
  r=room();start_unlocked(r)
  for p in r['players']:p.update(auto_idle=False,autopilot=False,ai_next=99999)
  p=r['players'][0];h=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='harvester');n=next(n for n in r['nodes'] if n['kind']=='metal');h.update(x=n.get('parking_spots',[n])[0]['x'],y=n.get('parking_spots',[n])[0]['y'],cargo=0,gather='metal');g.tick(r,.5);self.assertTrue(h['harvesting']);self.assertEqual(h['load_type'],'metal');self.assertEqual(h['cargo'],10)
  h['goal']=[h['x']+100,h['y']];g.tick(r,.1);self.assertFalse(h['harvesting']);h['goal']=None;core=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='core');g.entity(r,p,'warehouse',core['x']+160,core['y']);h.update(x=core['x'],y=core['y'],cargo=g.HARVESTER_CAPACITY);g.tick(r,.1);self.assertEqual(h['cargo'],0);self.assertFalse(h['harvesting'])
