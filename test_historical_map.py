import unittest,math
import server as g
from test_game import room
class HistoricalMap(unittest.TestCase):
 def test_equal_start_packages_and_safe_terrain(self):
  for _ in range(3):
   r=room();r['_experimental_history']=True;g.start(r)
   starts=[n for n in r['nodes'] if n.get('region')=='starter']
   self.assertEqual(len(starts),len(g.START_BASES)*5)
   for slot,base in enumerate(g.START_BASES):
    nodes=[n for n in starts if n['base_slot']==slot];self.assertEqual({n['kind'] for n in nodes},{'food','wood','stone','gold','iron'})
    for n in nodes:
     self.assertTrue(n['finite']);self.assertLessEqual(math.hypot(n['x']-base[0],n['y']-base[1]),1250.01)
     self.assertFalse(g.water_at(n['x'],n['y']));self.assertFalse(g.cliff_at(r,n['x'],n['y']));self.assertFalse(g.route_lane(r,n['x'],n['y'],120))
   central=[n for n in r['nodes'] if n.get('region')=='contested'];self.assertEqual(len(central),6)
   self.assertEqual({n['kind'] for n in central},{'gold','iron','stone'});self.assertTrue(all(n['stock']==100000 and n['finite'] for n in central))
 def test_existing_mode_has_no_historical_deposits(self):
  r=room();g.start(r);self.assertFalse(any(n.get('region') in ('starter','contested') for n in r['nodes']))
 def test_finite_deposits_do_not_respawn(self):
  r=room();r['_experimental_history']=True;g.start(r);n=next(n for n in r['nodes'] if n.get('region')=='starter' and n['kind']=='food');nid=n['id'];n['stock']=0;g.replenish_deposits(r);self.assertFalse(any(o['id']==nid for o in r['nodes']));self.assertFalse(any(job['kind']=='food' for job in r.get('pending_deposits',[])))
if __name__=='__main__':unittest.main()
