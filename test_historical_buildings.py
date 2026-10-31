import math,unittest
import server as g
from test_game import room
class HistoricalBuildings(unittest.TestCase):
 def world(self,n=4):
  r=room(n);r.update(_experimental_history=True,_map_geometry='continental');g.start(r)
  for p in r['players']:p.update(auto_idle=False,autopilot=False,ai_next=999999)
  return r
 def test_starting_units_are_clear_of_core_and_rotation_works(self):
  r=self.world()
  for p in r['players']:
   core=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='core');self.assertEqual(core['era_created'],'stone')
   for unit in [e for e in r['entities'] if e['owner']==p['id'] and e['kind'] not in g.FOOTPRINTS]:
    self.assertFalse(abs(unit['x']-core['x'])<76 and abs(unit['y']-core['y'])<76);self.assertFalse(g.water_at(unit['x'],unit['y'],r=r));self.assertFalse(g.cliff_at(r,unit['x'],unit['y']))
   for turn in range(1,5):
    g.command(r,p,dict(action='rotate_building',building=core['id']));self.assertAlmostEqual(core['facing'],(turn%4)*math.pi/2)
 def test_early_barracks_upgrades_after_advancement_and_keeps_position(self):
  r=self.world(2);p=r['players'][0];core=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='core');point=None
  for radius in (300,400,500):
   for n in range(32):
    x,y=g.snap_building('barracks',core['x']+math.cos(n*math.tau/32)*radius,core['y']+math.sin(n*math.tau/32)*radius)
    if g.clear_footprint(r,'barracks',x,y) and g.water_building(r,p,'barracks',x,y):point=(x,y);break
   if point:break
  self.assertIsNotNone(point);g.command(r,p,dict(action='build',kind='barracks',x=point[0],y=point[1]));b=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='barracks');self.assertEqual(b['era_created'],'stone');g.tick(r,12);p['historical']['era']='ancient';g.upgrade_buildings_for_era(r,p)
  g.command(r,p,dict(action='rotate_building',building=b['id']));self.assertEqual(b['era_created'],'ancient');self.assertEqual(b['original_era'],'stone');self.assertAlmostEqual(b['facing'],math.pi/2)
  for n in range(32):
   x,y=g.snap_building('barracks',b['x']+math.cos(n*math.tau/32)*250,b['y']+math.sin(n*math.tau/32)*250,b['facing'])
   if g.clear_footprint(r,'barracks',x,y,b['id'],angle=b['facing']) and g.water_building(r,p,'barracks',x,y):break
  else:self.fail('No clear relocation point')
  g.command(r,p,dict(action='relocate_building',building=b['id'],x=x,y=y));self.assertEqual(b['era_created'],'ancient');self.assertEqual(b['original_era'],'stone');self.assertAlmostEqual(b['facing'],math.pi/2)
  g.command(r,p,dict(action='demolish',ids=[b['id']]));self.assertEqual(b['hp'],0)
 def test_stone_ruins_keep_their_era_and_offer_salvage(self):
  r=self.world(2);p=r['players'][0];core=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='core');b=g.entity(r,p,'barracks',core['x']+250,core['y']+250);b['facing']=math.pi/2;b['hp']=0;g.tick(r,.1)
  wreck=next(w for w in r['wrecks'] if w['id']=='wreck-'+b['id']);self.assertEqual((wreck['era_created'],wreck['resource'],wreck['facing']),('stone','wood',math.pi/2));self.assertGreater(wreck['stock'],0)
  effect=next(f for f in r['effects'] if f['kind']=='explosion' and f.get('source')=='barracks');self.assertEqual((effect['era_created'],effect['facing']),('stone',math.pi/2))
  cart=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='harvester');g.command(r,p,dict(action='gather',ids=[cart['id']],resource='wood',node=wreck['id']));self.assertEqual(cart['resource_target'],wreck['id'])
  classic=room();g.start(classic);q=classic['players'][0];old=g.entity(classic,q,'barracks',1000,1000);old['hp']=0;g.tick(classic,.1);self.assertEqual(next(w for w in classic['wrecks'] if w['id']=='wreck-'+old['id'])['resource'],'metal')
 def test_engineer_can_rebuild_early_core_with_period_materials(self):
  r=self.world(2);p=r['players'][0];p['historical']['era']='ancient';p['historical']['resources']['gold']=20;p['tech']=['engineering_basics'];core=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='core');g.entity(r,p,'barracks',core['x']+300,core['y']+200);engineer=g.entity(r,p,'engineer',core['x']+75,core['y']);core['hp']=0;g.tick(r,.1);r['fires']=[]
  wreck=next(w for w in r['wrecks'] if w['id']=='wreck-'+core['id']);p['historical']['resources'].update(wood=500,stone=500,iron=200);g.sync_historical_bank(p,to_history=False);before_wood=p['wood'];g.command(r,p,dict(action='reclaim',ids=[engineer['id']],target=wreck['id']));self.assertLess(p['wood'],before_wood);self.assertEqual(p['riftglass'],0);g.tick(r,30)
  rebuilt=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='core' and e['hp']>0);self.assertEqual(rebuilt['era_created'],'ancient');self.assertFalse(any(w['id']==wreck['id'] for w in r['wrecks']))
 def test_historical_warehouse_increases_capacity_and_unloads_mixed_cargo(self):
  r=self.world(2);p=r['players'][0];core=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='core');cart=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='harvester');before_cap=g.storage_capacity(r,p);store=g.entity(r,p,'warehouse',core['x']+300,core['y']+200);self.assertEqual(store['era_created'],'stone');self.assertEqual(g.storage_capacity(r,p)-before_cap,5000)
  cart.update(x=store['x']+80,y=store['y'],goal=None,cargo=100,cargo_loads={'food':40,'wood':60},load_type='wood',storage_blocked=True);before_food=p['historical']['resources']['food'];before_wood=p['wood'];g.tick(r,.1);self.assertEqual(cart['cargo'],0);self.assertEqual(p['historical']['resources']['food'],before_food+40);self.assertEqual(p['wood'],before_wood+60);self.assertEqual(p['historical']['resources']['wood'],p['wood'])
  p['tech'].append('storage_2');g.apply_research_upgrades(r,p);self.assertEqual(store['storage_level'],2);self.assertEqual(g.storage_capacity(r,p)-before_cap,8000)
 def test_stone_academy_conducts_research_after_advancing(self):
  r=self.world(2);p=r['players'][0];core=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='core');academy=g.entity(r,p,'academy',core['x']+250,core['y']+250);g.entity(r,p,'barracks',core['x']+450,core['y']+250);self.assertEqual(academy['era_created'],'stone');self.assertEqual(academy['original_era'],'stone');p['historical']['era']='ancient';p['historical']['resources']['gold']=30;p['gathered']['wood']=100;p['power']=20
  g.command(r,p,dict(action='research',tech='fieldcraft'));self.assertEqual(p['research']['key'],'fieldcraft');g.tick(r,30);self.assertIn('fieldcraft',p['tech']);self.assertEqual(academy['era_created'],'ancient');self.assertEqual(academy['original_era'],'stone')
 def test_service_buildings_can_rotate_and_leave_wood_ruins(self):
  r=self.world(2);p=r['players'][0]
  for kind,x in [('warehouse',3000),('academy',3300)]:
   b=g.entity(r,p,kind,x,3000)
   for turn in range(1,5):g.command(r,p,dict(action='rotate_building',building=b['id']));self.assertAlmostEqual(b['facing'],(turn%4)*math.pi/2)
   b['hp']=0;g.tick(r,.1);wreck=next(w for w in r['wrecks'] if w['id']=='wreck-'+b['id']);self.assertEqual((wreck['era_created'],wreck['resource']),('stone','wood'))
 def test_later_and_classic_buildings_do_not_claim_stone_art(self):
  r=self.world(2);p=r['players'][0];p['historical']['era']='ancient';building=g.entity(r,p,'barracks',3000,3000);self.assertEqual(building['era_created'],'ancient')
  normal=room();g.start(normal);classic=next(e for e in normal['entities'] if e['kind']=='core');self.assertNotIn('era_created',classic)
