import unittest,math
import server as g
from test_game import room
class WeatherTests(unittest.TestCase):
 def test_shared_dynamic_weather_and_day_cycle(self):
  r=room();g.start(r)
  seen=[]
  for elapsed in [0,150,300,450,600]:
   r['elapsed']=elapsed;g.update_weather(r);kind=r['weather']['kind'];self.assertIn(kind,['clear','rain','snow','dust']);seen.append(kind);g.update_weather(r);self.assertEqual(r['weather']['kind'],kind)
  self.assertTrue(all(a!=b for a,b in zip(seen,seen[1:])))
  r['elapsed']=0;r['start_hour']=0;g.update_weather(r);night=r['weather']['daylight'];r['start_hour']=12;g.update_weather(r);self.assertGreater(r['weather']['daylight'],night)
 def test_fixed_weather_and_snow_accumulation(self):
  r=room();r['weather_mode']='snow';g.start(r);g.update_weather(r,100);self.assertGreater(r['weather']['snow'],0);before=r['weather']['snow'];r['weather_mode']='clear';g.update_weather(r,10);self.assertLess(r['weather']['snow'],before)
 def test_environment_config_host_only(self):
  r=room();g.command(r,r['players'][0],dict(action='config',weather_mode='rain',start_hour=18));g.start(r);self.assertEqual(r['weather']['kind'],'rain');self.assertEqual(r['weather']['phase'],'sunset')
  r=room()
  with self.assertRaises(AssertionError):g.command(r,r['players'][1],dict(action='config',weather_mode='snow'))
class WallTests(unittest.TestCase):
 def setUp(self):
  self.r=room();g.start(self.r);self.p=self.r['players'][0]
  for p in self.r['players']:p.update(auto_idle=False,autopilot=False,ai_next=99999)
  self.p.update(credits=10000,metal=1000,wood=1000,riftglass=1000,tech=['industry'])
 def test_wall_line_and_atomic_cost(self):
  before=self.p['metal'];g.command(self.r,self.p,dict(action='wall_line',x=260,y=400,endx=380,endy=400));walls=[e for e in self.r['entities'] if e['kind']=='wall'];self.assertEqual(len(walls),3);self.assertEqual(before-self.p['metal'],30)
  before=self.p['metal']
  with self.assertRaises(AssertionError):g.command(self.r,self.p,dict(action='wall_line',x=260,y=260,endx=380,endy=260))
  self.assertEqual(self.p['metal'],before);self.assertEqual(len([e for e in self.r['entities'] if e['kind']=='wall']),3)
 def test_walls_block_ground_movement(self):
  g.entity(self.r,self.p,'wall',340,260);unit=g.entity(self.r,self.p,'infantry',340,220);g.command(self.r,self.p,dict(action='move',ids=[unit['id']],x=340,y=320))
  positions=[]
  for _ in range(15):
   old=dict(unit);g.tick(self.r,.1);positions.append((unit['x'],unit['y']))
   if g.dist(old,unit)>.01:self.assertIsNone(g.barrier_hit(self.r,old,unit['x'],unit['y']))
  self.assertTrue(any(abs(x-340)>30 for x,y in positions),'Unit should route around the barrier')
 def test_gates_auto_pass_allies_but_lock_when_closed(self):
  gate=g.entity(self.r,self.p,'gate',340,260);unit=g.entity(self.r,self.p,'infantry',340,220);g.command(self.r,self.p,dict(action='move',ids=[unit['id']],x=340,y=320))
  for _ in range(15):g.tick(self.r,.1)
  self.assertGreater(unit['y'],280);unit.update(x=340,y=220,goal=None);g.command(self.r,self.p,dict(action='gate_mode',building=gate['id'],mode='closed'));g.command(self.r,self.p,dict(action='move',ids=[unit['id']],x=340,y=320))
  positions=[]
  for _ in range(15):
   old=dict(unit);g.tick(self.r,.1);positions.append((unit['x'],unit['y']))
   if g.dist(old,unit)>.01:self.assertIsNone(g.barrier_hit(self.r,old,unit['x'],unit['y']))
  self.assertTrue(any(abs(x-340)>30 for x,y in positions),'Unit should route around the barrier')
 def test_enemy_gate_block_and_destroyed_wall_pass(self):
  enemy=self.r['players'][1];gate=g.entity(self.r,enemy,'gate',340,260);unit=g.entity(self.r,self.p,'harvester',340,220);self.assertIs(g.barrier_hit(self.r,unit,340,280),gate);gate['hp']=0;self.assertIsNone(g.barrier_hit(self.r,unit,340,280))
 def test_rotated_wall_footprints(self):
  g.command(self.r,self.p,dict(action='build',kind='wall',x=420,y=260,angle=math.pi/2));wall=self.r['entities'][-1];self.assertAlmostEqual(wall['angle'],math.pi/2);self.assertFalse(g.clear_footprint(self.r,'wall',420,280))
if __name__=='__main__':unittest.main()

class LongWalls(unittest.TestCase):
 def test_long_drag_and_extension(self):
  r=room();g.start(r);r['props']=[];p=r['players'][0];p.update(credits=10000,metal=2000,wood=2000)
  g.command(r,p,dict(action='wall_line',x=1000,y=1500,endx=2800,endy=1500))
  walls=[e for e in r['entities'] if e['kind']=='wall'];self.assertEqual(len(walls),31)
  self.assertTrue(all(w['x']==1010+i*60 and w['y']==1510 for i,w in enumerate(walls)))
  before=p['metal'];g.command(r,p,dict(action='wall_line',x=2814,y=1510,endx=2934,endy=1510));self.assertEqual(before-p['metal'],20);self.assertEqual(len([e for e in r['entities'] if e['kind']=='wall']),33)
  before=p['credits'];p['metal']=0
  with self.assertRaises(AssertionError):g.command(r,p,dict(action='wall_line',x=1000,y=1800,endx=2800,endy=1800))
  self.assertEqual(before,p['credits']);self.assertEqual(len([e for e in r['entities'] if e['kind']=='wall']),33)
 def test_vertical_wall_continuous_collision(self):
  r=room();g.start(r);r['props']=[];p=r['players'][0];p.update(credits=10000,metal=2000,wood=2000)
  g.command(r,p,dict(action='wall_line',x=1500,y=1000,endx=1500,endy=1780))
  unit=g.entity(r,p,'jeep',1480,1026)
  self.assertIsNotNone(g.barrier_hit(r,unit,1520,1026))
  self.assertTrue(all(abs(w['facing']-math.pi/2)<.001 for w in r['entities'] if w['kind']=='wall'))
