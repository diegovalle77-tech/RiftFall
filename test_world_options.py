import unittest
import server as g
from test_game import room
class WorldOptions(unittest.TestCase):
 def test_expanded_map_and_sparse_ruins(self):
  self.assertEqual((g.WORLD_W,g.WORLD_H),(14400,9600));r=room(4);g.start(r);self.assertEqual(sum(o['kind']=='abandoned' for o in r['props']),6)
  for p in r['players']:
   core=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='core');self.assertTrue(any(n['kind']=='metal' and 650<=g.dist(n,core)<=1100 for n in r['nodes']))
 def test_every_faction_selectable_without_research(self):
  r=room();p=r['players'][0]
  for faction in ['Bastion','Vesper','Ironwatch','Nightfall']:g.command(r,p,dict(action='config',faction=faction));self.assertEqual(p['faction'],faction)
  g.start(r);self.assertEqual(p['tech'],[]);e=next(e for e in r['entities'] if e['owner']==p['id']);self.assertEqual(e['design'],'nightfall')
 def test_all_difficulties_and_host_validation(self):
  r=room();p=r['players'][0]
  for difficulty in g.DIFFICULTIES:g.command(r,p,dict(action='config',difficulty=difficulty));self.assertEqual(r['difficulty'],difficulty)
  with self.assertRaises(AssertionError):g.command(r,r['players'][1],dict(action='config',difficulty='easy'))
  with self.assertRaises(AssertionError):g.command(r,p,dict(action='config',difficulty='invalid'))
 def test_ai_cadence_and_harvest_differences(self):
  for difficulty,tuning in g.DIFFICULTIES.items():
   r=room(1);r.update(ai_enabled=True,difficulty=difficulty);g.start(r);bot=next(p for p in r['players'] if p.get('bot'));h=next(e for e in r['entities'] if e['owner']==bot['id'] and e['kind']=='harvester');node=next(n for n in r['nodes'] if n['kind']=='metal');anchor=g.mining_anchor(r,node,h);h.update(x=anchor['x'],y=anchor['y'],gather='metal',resource_target=node['id']);g.tick(r,.1);self.assertAlmostEqual(h['cargo'],2*tuning['harvest']);self.assertAlmostEqual(bot['ai_next'],.1+tuning['decision'])
 def test_captured_units_preserve_original_design(self):
  r=room();g.start(r);enemy=r['players'][1];e=g.entity(r,enemy,'medic',900,900);self.assertEqual(e['design'],'vesper');e['owner']=r['players'][0]['id'];self.assertEqual(e['design'],'vesper')
if __name__=='__main__':unittest.main()
