import unittest
import server as g
from test_game import room
class HistoricalUnits(unittest.TestCase):
 def world(self):
  r=room();r.update(_experimental_history=True,_map_geometry='continental');g.start(r)
  for p in r['players']:p.update(auto_idle=False,autopilot=False,ai_next=999999)
  p,q=r['players'];spearman=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='infantry');enemy=next(e for e in r['entities'] if e['owner']==q['id'] and e['kind']=='infantry');spearman.update(x=7200,y=3000,cool=0);enemy.update(x=7230,y=3000,cool=999);return r,p,q,spearman,enemy
 def test_melee_has_close_range_and_no_firearms(self):
  r,p,q,s,e=self.world();self.assertEqual((s['historical_role'],s['attack_range']),('spearman',58));before=e['hp'];g.tick(r,.1);self.assertAlmostEqual(e['hp'],before-14*g.UNIT_COMBAT_DAMAGE_FACTOR);self.assertTrue(any(f['kind']=='melee' for f in r['effects']));self.assertFalse(any(f['kind'] in ['muzzle','tracer'] and f['x']==s['x'] and f['y']==s['y'] for f in r['effects']));self.assertEqual(r['projectiles'],[])
 def test_cannot_hit_at_rifle_distance(self):
  r,p,q,s,e=self.world();e['x']=7280;before=e['hp'];g.tick(r,.1);self.assertEqual(e['hp'],before);self.assertFalse(s['engaged'])
 def test_units_keep_equipment_across_era_change(self):
  r,p,q,s,e=self.world();cart=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='harvester');self.assertEqual((cart['historical_role'],cart['cargo_capacity']),('gatherer',750));p['historical']['era']='industrial';new=g.entity(r,p,'infantry',7500,3000);vehicle=g.entity(r,p,'harvester',7500,3200);self.assertEqual(s['historical_role'],'spearman');self.assertEqual(cart['historical_role'],'gatherer');self.assertNotIn('historical_role',new);self.assertNotIn('historical_role',vehicle)
 def test_attacks_building_edge(self):
  r,p,q,s,e=self.world();e.update(x=8000,y=3000);core=next(b for b in r['entities'] if b['owner']==q['id'] and b['kind']=='core');core.update(x=s['x']+g.FOOTPRINTS['core'][0]+30,y=s['y']);g.command(r,p,dict(action='attack',ids=[s['id']],target=core['id']));before=core['hp'];x=s['x'];g.tick(r,.1);self.assertEqual(core['hp'],before-14);self.assertEqual(s['x'],x)
 def test_cannot_attack_aircraft(self):
  r,p,q,s,e=self.world();air=g.entity(r,q,'fighter',s['x']+30,s['y'])
  with self.assertRaisesRegex(AssertionError,'aircraft'):g.command(r,p,dict(action='attack',ids=[s['id']],target=air['id']))
 def test_classic_units_remain_unchanged(self):
  r=room();g.start(r);p=r['players'][0];unit=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='infantry');self.assertNotIn('historical_role',unit);self.assertNotIn('attack_range',unit)
