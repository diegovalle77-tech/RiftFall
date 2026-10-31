import json,unittest
import server as g
from test_game import room
class FiveEraMatch81(unittest.TestCase):
 def test_four_factions_advance_and_keep_early_equipment(self):
  r=room(4)
  for p,faction in zip(r['players'],g.era_rules.FACTIONS):p['faction']=faction
  g.command(r,r['players'][0],dict(action='config',map_preset='continental'));g.start(r)
  for p in r['players']:p.update(auto_idle=False,autopilot=False,ai_next=999999)
  starters={p['id']:[e['id'] for e in r['entities'] if e['owner']==p['id'] and e['kind']=='infantry'] for p in r['players']}
  cores={p['id']:next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='core') for p in r['players']}
  positions={pid:(e['x'],e['y']) for pid,e in cores.items()}
  for era in g.era_rules.ERAS[1:]:
   for p in r['players']:
    p['historical']['resources'].update({k:10000 for k in g.era_rules.RESOURCES});g.sync_historical_bank(p,to_history=False)
    g.command(r,p,dict(action='advance_era'))
   # Exercise actual simulation advancement, rather than assigning era metadata.
   g.tick(r,era.seconds)
   for p in r['players']:
    self.assertEqual(p['historical']['era'],era.key);self.assertIsNone(p['historical']['era_job'])
    core=cores[p['id']];self.assertEqual(core['era_created'],era.key);self.assertEqual(core['original_era'],'stone');self.assertEqual((core['x'],core['y']),positions[p['id']])
    snapshot=g.view(r,p);json.dumps(snapshot)
    self.assertEqual(snapshot['cost_catalog']['core'],g.commander_costs(p,g.material_costs('core',p)))
    self.assertNotIn('token',str(snapshot))
    for e in r['entities']:
     if e['id'] in starters[p['id']]:self.assertEqual(e['era_created'],'stone');self.assertEqual(e['historical_role'],'spearman')
  for p in r['players']:
   with self.assertRaisesRegex(AssertionError,'final era'):g.command(r,p,dict(action='advance_era'))
  self.assertEqual(sum(n['kind']=='riftglass' for n in r['nodes']),2)
if __name__=='__main__':unittest.main()
