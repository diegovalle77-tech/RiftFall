import unittest
import server as g
from test_game import room,start_unlocked
class BaseDestruction(unittest.TestCase):
 def test_core_loss_keeps_buildings_and_units_alive(self):
  r=room();start_unlocked(r)
  for p in r['players']:p.update(auto_idle=False,autopilot=False,ai_next=99999)
  p=r['players'][1];extra=g.entity(r,p,'wall',6000,4000)
  for e in r['entities']:
   if e['owner']==p['id'] and e['kind']=='core':e['hp']=0
  g.tick(r,.1);self.assertTrue(p['alive']);self.assertEqual(r['phase'],'battle');self.assertIn(extra,r['entities'])
  for e in r['entities']:
   if e['owner']==p['id'] and e['kind'] in g.FOOTPRINTS:e['hp']=0
  g.tick(r,.1);self.assertFalse(p['alive']);self.assertEqual(r['phase'],'finished')
 def test_bot_pursues_expansion_and_waits_between_raids(self):
  r=room(1);r.update(ai_enabled=True,difficulty='normal');start_unlocked(r);bot=next(p for p in r['players'] if p.get('bot'));human=r['players'][0]
  for e in r['entities']:
   if e['owner']==human['id']:e['hp']=0
  target=g.entity(r,human,'factory',1000,1800)
  army=[g.entity(r,bot,'tank',3000+i*40,2400) for i in range(4)]
  r['elapsed']=300;g.commander_ai(r,bot)
  self.assertTrue(all(e['goal']==e.get('formation_slot') for e in army));self.assertEqual(len({tuple(e['goal']) for e in army}),len(army));self.assertTrue(all(not list(g.make_occupancy(r).blockers(e,*e['goal'],static_only=True)) for e in army));self.assertEqual(bot['next_raid'],450)
  for e in army:e['goal']=None
  r['elapsed']=320;g.commander_ai(r,bot);self.assertTrue(all(e['goal'] is None for e in army))
  for e in army:e['attack']='destroyed-building'
  r['elapsed']=450;g.commander_ai(r,bot);self.assertTrue(all(e['goal']==e.get('formation_slot') for e in army));self.assertEqual(len({tuple(e['goal']) for e in army}),len(army));self.assertTrue(all(not list(g.make_occupancy(r).blockers(e,*e['goal'],static_only=True)) for e in army))
 def test_difficulty_is_slower_at_every_level(self):
  for d in g.DIFFICULTIES.values():self.assertGreaterEqual(d['decision'],10);self.assertGreaterEqual(d['raid_after'],180);self.assertGreaterEqual(d['raid_interval'],90)
