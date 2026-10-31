import unittest
import server as g
from test_game import room
class HistoricalArchers(unittest.TestCase):
 def world(self):
  r=room();r.update(_experimental_history=True,_map_geometry='continental');g.start(r)
  for p in r['players']:p.update(auto_idle=False,autopilot=False,ai_next=999999)
  p,q=r['players'];p['historical']['era']='ancient';p['tech']=['fieldcraft'];archer=g.entity(r,p,'marksman',7200,3000);enemy=next(e for e in r['entities'] if e['owner']==q['id'] and e['kind']=='infantry');enemy.update(x=7300,y=3000,cool=999);return r,p,q,archer,enemy
 def test_ancient_research_unlock_and_retained_role(self):
  r,p,q,a,e=self.world();p['tech']=[];self.assertFalse(g.unlocked(p,'marksman'));p['tech']=['fieldcraft'];self.assertTrue(g.unlocked(p,'marksman'));self.assertEqual((a['historical_role'],a['attack_range']),('archer',230));p['historical']['era']='industrial';new=g.entity(r,p,'marksman',8000,3000);self.assertNotIn('historical_role',new);self.assertEqual(a['historical_role'],'archer')
 def test_arrow_travels_and_hits_only_its_target(self):
  r,p,q,a,e=self.world();witness=g.entity(r,q,'infantry',7310,3000);witness['cool']=999;before=e['hp'];g.tick(r,.1);self.assertEqual(e['hp'],before);self.assertEqual([s['kind'] for s in r['projectiles']],['arrow']);self.assertFalse(any(f['kind'] in ['muzzle','tracer','explosion'] for f in r['effects']));g.tick(r,.5);self.assertAlmostEqual(e['hp'],before-18*g.UNIT_COMBAT_DAMAGE_FACTOR);self.assertEqual(witness['hp'],100);self.assertFalse(r['fires']);self.assertFalse(r['craters'])
 def test_arrow_can_miss_a_moving_target(self):
  r,p,q,a,e=self.world();g.tick(r,.1);e['y']+=150;before=e['hp'];g.tick(r,.5);self.assertEqual(e['hp'],before);self.assertFalse(any(f['kind']=='explosion' for f in r['effects']))
 def test_embarked_target_is_protected_from_an_incoming_arrow(self):
  r,p,q,a,e=self.world();g.tick(r,.1);ship=g.entity(r,q,'transport',e['x'],e['y']);e['embarked']=ship['id'];before=e['hp'];g.tick(r,.5);self.assertEqual(e['hp'],before)
 def test_archer_cannot_attack_aircraft(self):
  r,p,q,a,e=self.world();air=g.entity(r,q,'fighter',a['x']+30,a['y']);
  with self.assertRaisesRegex(AssertionError,'archers cannot attack aircraft'):g.command(r,p,dict(action='attack',ids=[a['id']],target=air['id']))
 def test_classic_marksmen_stay_modern(self):
  r=room();g.start(r);p=r['players'][0];a=g.entity(r,p,'marksman',1000,1000);self.assertNotIn('historical_role',a);self.assertNotIn('attack_range',a)
 def test_enemy_ai_can_research_early_archers(self):
  r=room(1);r.update(_experimental_history=True,_map_geometry='continental');g.start(r);p=next(p for p in r['players'] if p.get('bot'));p['historical']['era']='ancient';p['historical']['resources']['gold']=100;p['gathered']['wood']=100;p['power']=20;base=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='core')
  for i,kind in enumerate(['academy','barracks','harvester']+['infantry']*5):g.entity(r,p,kind,base['x']+i*50,base['y']+200)
  g.commander_ai(r,p);self.assertEqual(p['research']['key'],'fieldcraft')
