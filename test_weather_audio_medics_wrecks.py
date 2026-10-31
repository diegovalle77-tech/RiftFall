import copy,math,unittest,wave
from pathlib import Path
import server as g
from test_game import room
class WeatherCombat(unittest.TestCase):
 def world(self):
  r=room();g.start(r)
  for p in r['players']:p.update(auto_idle=False,autopilot=False,ai_next=99999)
  return r,r['players'][0]
 def test_accumulation_persistence_melting_and_drying(self):
  r=dict(elapsed=0,start_hour=12,weather_mode='rain');g.update_weather(r);self.assertEqual(r['weather']['mud'],0);g.update_weather(r,100);self.assertAlmostEqual(r['weather']['mud'],.5)
  r['weather_mode']='clear';g.update_weather(r,10);self.assertGreater(r['weather']['mud'],0);self.assertLess(r['weather']['mud'],.5)
  r.update(weather_mode='snow',weather={'snow':0,'mud':0});g.update_weather(r,100);self.assertAlmostEqual(r['weather']['snow'],.4);r['weather_mode']='clear';g.update_weather(r,30);self.assertGreater(r['weather']['snow'],0);self.assertLess(r['weather']['snow'],.4);self.assertGreater(r['weather']['mud'],0)
 def test_ground_types_and_actual_movement(self):
  c=dict(surface='mud',mud=1,snow=1);tank=g.weather_mobility({'kind':'tank'},c);jeep=g.weather_mobility({'kind':'jeep'},c);self.assertGreater(tank,jeep);self.assertGreaterEqual(jeep,.35);self.assertEqual(g.weather_mobility({'kind':'fighter'},c),1);self.assertGreater(g.weather_mobility({'kind':'jeep'},{**c,'surface':'bridge'}),jeep)
  r,p=self.world();r['weather_mode']='clear';unit=g.entity(r,p,'jeep',1000,1000);unit['goal']=[1200,1000];wet=copy.deepcopy(r);wet['weather']={'kind':'clear','mud':1,'snow':1};g.tick(r,.1);g.tick(wet,.1);wet_unit=next(e for e in wet['entities'] if e['id']==unit['id']);self.assertLess(wet_unit['travel'],unit['travel']*.8);self.assertLess(wet_unit['terrain']['speed_factor'],1)
 def test_medics_auto_heal_only_allies_in_range(self):
  r,p=self.world();medic=g.entity(r,p,'medic',1100,1100);hurt=g.entity(r,p,'hacker',1140,1100);hurt['hp']=30;far=g.entity(r,p,'engineer',1240,1100);far['hp']=40;enemy=g.entity(r,r['players'][1],'engineer',1120,1100);enemy['hp']=30
  g.tick(r,.1);self.assertEqual(hurt['hp'],42);self.assertEqual(far['hp'],40);self.assertEqual(enemy['hp'],30);self.assertEqual(medic['heal_range'],120);self.assertEqual(medic['healing_target'],hurt['id']);g.tick(r,1);self.assertEqual(hurt['hp'],42)
  p['tech'].append('combat_medicine');medic['cool']=0;g.tick(r,.1);self.assertEqual(hurt['hp'],60)
 def test_destroyed_building_persists_and_can_be_salvaged(self):
  r,p=self.world();b=g.entity(r,p,'barracks',5000,1500);b['hp']=0;g.tick(r,.1);wreck=next(w for w in r['wrecks'] if w['building_kind']=='barracks');self.assertEqual(wreck['design'],'bastion');self.assertNotIn(b,r['entities']);self.assertFalse(g.clear_footprint(r,'barracks',5000,1500));r['fires']=[]
  h=g.entity(r,p,'harvester',5000,1500);g.command(r,p,dict(action='gather',ids=[h['id']],resource='metal',node=wreck['id']));count=len(r['nodes']);g.tick(r,5);self.assertNotIn(wreck,r['wrecks']);self.assertEqual(len(r['nodes']),count);self.assertGreater(h['cargo'],0)
 def test_engineer_rebuilds_wreck(self):
  r,p=self.world();p.update(tech=['fieldcraft'],credits=1000,metal=100,wood=100);b=g.entity(r,p,'barracks',5000,1500);b['hp']=0;g.tick(r,.1);wreck=next(w for w in r['wrecks'] if w['building_kind']=='barracks');r['fires']=[];r['craters']=[];engineer=g.entity(r,p,'engineer',5060,1500);g.command(r,p,dict(action='reclaim',ids=[engineer['id']],target=wreck['id']));g.tick(r,30);self.assertNotIn(wreck,r['wrecks']);self.assertTrue(any(e['kind']=='barracks' and e['hp']>0 for e in r['entities']))
 def test_original_music_files_are_playable_stereo(self):
  for name in ['soundtrack-lobby.wav','soundtrack-battle.wav']:
   with wave.open(str(Path(__file__).with_name(name)),'rb') as audio:self.assertEqual(audio.getnchannels(),2);self.assertEqual(audio.getsampwidth(),2);self.assertGreater(audio.getnframes()/audio.getframerate(),25)

class TankAtlas(unittest.TestCase):
 def test_complete_tank_views_do_not_cross_cut_boundaries(self):
  from PIL import Image
  image=Image.open(Path(__file__).with_name('directional-tank.png'));alpha=image.getchannel('A')
  for fraction in [.27,.53,.77]:
   x=int(image.width*fraction);self.assertFalse(any(v>150 for v in alpha.crop((x,0,x+1,image.height)).get_flattened_data()))
  for fraction in [.26,.497,.738]:
   y=int(image.height*fraction);self.assertFalse(any(v>150 for v in alpha.crop((0,y,image.width,y+1)).get_flattened_data()))
