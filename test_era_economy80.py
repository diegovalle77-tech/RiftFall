import copy, unittest
import server as g
from test_game import room
class EraEconomy80(unittest.TestCase):
 def world(self):
  r=room();g.command(r,r['players'][0],dict(action='config',map_preset='continental'));g.start(r)
  for p in r['players']:p.update(auto_idle=False,autopilot=False,ai_next=999999)
  return r,r['players'][0]
 def test_early_available_equipment_needs_no_advanced_resources(self):
  r,p=self.world()
  for era in ['stone','ancient']:
   p['historical']['era']=era
   for kind in g.MATERIAL_COSTS:
    if g.era_rules.kind_era_reason(p['historical'],kind):continue
    costs=g.material_costs(kind,p)
    self.assertFalse(costs.get('iron'),(era,kind));self.assertFalse(costs.get('riftglass'),(era,kind))
 def test_all_five_eras_have_distinct_complete_recipes(self):
  r,p=self.world();core=[]
  for era in g.era_rules.ERAS:
   p['historical']['era']=era.key;core.append(g.material_costs('core',p))
   for kind in g.MATERIAL_COSTS:
    costs=g.material_costs(kind,p);self.assertTrue(costs)
    self.assertTrue(all(k in g.era_rules.RESOURCES and isinstance(v,int) and v>0 for k,v in costs.items()))
  self.assertEqual(len({tuple(sorted(c.items())) for c in core}),5)
 def test_catalog_matches_atomic_payment_each_era(self):
  r,p=self.world()
  for era in g.era_rules.ERAS:
   p['historical']['era']=era.key;p['historical']['resources']={k:5000 for k in g.era_rules.RESOURCES};g.sync_historical_bank(p,to_history=False)
   catalog=g.view(r,p)['cost_catalog']['harvester'];before=dict(p['historical']['resources']);g.pay_materials(p,'harvester')
   self.assertEqual(p['historical']['resources'],{k:v-catalog.get(k,0) for k,v in before.items()})
   p['historical']['resources']={k:0 for k in g.era_rules.RESOURCES};g.sync_historical_bank(p,to_history=False);before=copy.deepcopy(p)
   with self.assertRaises(AssertionError):g.pay_materials(p,'harvester')
   self.assertEqual(p,before)
 def test_cost_results_cannot_mutate_rules(self):
  r,p=self.world();cost=g.material_costs('core',p);cost['wood']=99999;self.assertEqual(g.material_costs('core',p)['wood'],300)
 def test_legacy_economy_unchanged(self):
  for kind in g.MATERIAL_COSTS:self.assertEqual(g.material_costs(kind,dict()),g.material_costs(kind))
 def test_queue_keeps_paid_era_across_advancement(self):
  r,p=self.world();core=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='core')
  g.command(r,p,dict(action='train',kind='harvester'));self.assertEqual(core['production'][0]['era_ordered'],'stone')
  p['historical']['era']='industrial';g.upgrade_buildings_for_era(r,p);before={e['id'] for e in r['entities']};g.tick_production(r,p,100)
  recruit=next(e for e in r['entities'] if e['id'] not in before);self.assertEqual(recruit['era_created'],'stone');self.assertEqual(recruit['historical_role'],'gatherer')
  p['historical']['resources'].update(food=500,iron=500,gold=500);g.sync_historical_bank(p,to_history=False)
  g.command(r,p,dict(action='train',kind='harvester'));before={e['id'] for e in r['entities']};g.tick_production(r,p,100)
  recruit=next(e for e in r['entities'] if e['id'] not in before);self.assertEqual(recruit['era_created'],'industrial');self.assertNotIn('historical_role',recruit)
 def test_future_soldier_requires_future_material(self):
  r,p=self.world();p['historical']['era']='future';self.assertGreater(g.material_costs('infantry',p)['riftglass'],0)
if __name__=='__main__':unittest.main()
