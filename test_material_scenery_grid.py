import math,unittest
import server as g
from test_game import room
class MaterialsGrid(unittest.TestCase):
 def world(self):
  r=room();g.start(r)
  for p in r['players']:p.update(auto_idle=False,autopilot=False,ai_next=99999)
  return r,r['players'][0]
 def test_collect_scenery_and_respawn(self):
  for kind in ['tree','rock','ruin']:
   r,p=self.world();source=next(o for o in r['props'] if o['kind']==kind);resource=g.material_kind(source);self.assertEqual(source['stock'],40000)
   h=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='harvester');h.update(x=source['x'],y=source['y'])
   g.command(r,p,dict(action='gather',ids=[h['id']],resource=resource,node=source['id']));g.tick(r,.5)
   self.assertEqual(h['load_type'],resource);self.assertEqual(h['cargo'],10);self.assertEqual(source['stock'],39990)
   core=next(e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='core');h.update(x=core['x'],y=core['y'],cargo=g.HARVESTER_CAPACITY);before=p[resource];g.tick(r,.1);self.assertGreater(p[resource],before)
   source['stock']=0;g.replenish_deposits(r);self.assertNotIn(source,r['props']);self.assertEqual(r['nodes'][-1]['kind'],resource);self.assertEqual(r['nodes'][-1]['stock'],g.deposit_stock(resource))
 def test_bridges_have_clear_lanes(self):
  r,p=self.world();bridges=[b for b in r['props'] if b['kind']=='bridge']
  for obj in r['nodes']+[o for o in r['props'] if o['kind']!='bridge']:self.assertFalse(g.road_lane(obj['x'],obj['y'],100,r=r) or g.bridge_lane(r,obj['x'],obj['y'],100),obj)
  for bridge in bridges:
   a=bridge['angle'];x=bridge['x']+math.cos(a)*(bridge['span']/2+200);y=bridge['y']+math.sin(a)*(bridge['span']/2+200)
   self.assertFalse(g.clear_footprint(r,'wall',x,y));self.assertFalse(g.clear_footprint(r,'turret',x,y))
 def assert_grid(self,e):
  w,h=g.FOOTPRINTS[e['kind']]
  if abs(math.sin(e.get('facing',0)))>.7:w,h=h,w
  self.assertEqual((e['x']-w)%20,0);self.assertEqual((e['y']-h)%20,0)
 def test_grid_placement_rotation_and_relocation(self):
  r,p=self.world();r['props']=[];p.update(credits=10000,metal=2000,wood=2000,riftglass=2000,tech=list(g.TECHS))
  self.assertEqual(g.FOOTPRINTS['turret'],(40,40))
  for i,kind in enumerate(['turret','warehouse','barracks','airfield']):
   g.command(r,p,dict(action='build',kind=kind,x=1803+i*400,y=1407));e=r['entities'][-1];self.assert_grid(e);e['construction']['progress']=e['construction']['seconds']
   g.command(r,p,dict(action='rotate_building',building=e['id']));self.assert_grid(e)
   g.command(r,p,dict(action='relocate_building',building=e['id'],x=1807+i*400,y=1703,angle=e['facing']));self.assert_grid(e)
  self.assertEqual(g.view(r,p)['grid_size'],20)
 def test_steeper_hills(self):
  r,p=self.world();hill=r['hills'][0];x,y=hill['x'],hill['y'];self.assertGreater(hill['height'],60)
  self.assertGreater(g.terrain_height(r,x,y)-g.terrain_height({**r,'hills':[]},x,y),60)
