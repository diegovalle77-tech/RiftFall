"""End-to-end HTTP checks using temporary accounts and a live game server."""
import json, os, subprocess, sys, tempfile, time, unittest, urllib.request, urllib.error
from pathlib import Path
class LobbyTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();env=os.environ.copy();env['RIFTFALL_ACCOUNT_DB']=str(Path(cls.temp.name)/'accounts.db')
  cls.proc=subprocess.Popen([sys.executable,str(Path(__file__).with_name('server.py')),'--port','3000'],env=env,stdout=subprocess.DEVNULL)
  for _ in range(50):
   try:urllib.request.urlopen('http://localhost:3000/',timeout=1);return
   except OSError:time.sleep(.1)
  raise RuntimeError('Server did not start')
 @classmethod
 def tearDownClass(cls):
  cls.proc.terminate();cls.proc.wait();cls.temp.cleanup()
 def test_language_selector_and_script_route(self):
  with urllib.request.urlopen('http://localhost:3000/') as response:
   html=response.read().decode();self.assertIn('id="languageDialog"',html);self.assertIn('Español',html);self.assertIn('/language.js?v=',html)
  with urllib.request.urlopen('http://localhost:3000/language.js?v=2d61') as response:
   self.assertIn('javascript',response.headers['Content-Type']);self.assertEqual(response.read(),Path(__file__).with_name('language.js').read_bytes())
 def test_approved_resource_art_route(self):
  with urllib.request.urlopen('http://localhost:3000/resources-approved-sprites.png?v=2d22') as response:
   self.assertEqual(response.headers['Content-Type'],'image/png');self.assertIn('no-store',response.headers['Cache-Control']);self.assertEqual(response.read(),Path(__file__).with_name('resources-approved-sprites.png').read_bytes())
 def test_warehouse_directional_art_route(self):
  with urllib.request.urlopen('http://localhost:3000/directional-warehouse.png?v=2d33') as response:
   self.assertEqual(response.headers['Content-Type'],'image/png');self.assertEqual(response.read(),Path(__file__).with_name('directional-warehouse.png').read_bytes())
 def test_complete_turret_art_route(self):
  with urllib.request.urlopen('http://localhost:3000/turret-complete-sprites.png?v=2d33') as response:
   self.assertEqual(response.headers['Content-Type'],'image/png');self.assertEqual(response.read(),Path(__file__).with_name('turret-complete-sprites.png').read_bytes())
 def test_new_harvester_and_bridge_art_routes(self):
  for asset in ['wall-vertical-sprites.png','ships-sprites.png','harvester-parts-sprites.png','bridge-painted-sprites.png','cliffs-painted-sprites.png','mine-sprites.png','wreck-industrial-sprites.png','wreck-infrastructure-sprites.png','wreck-defenses-sprites.png','combat-fx-sprites.png']:
   with urllib.request.urlopen('http://localhost:3000/'+asset+'?v=2d34') as response:
    self.assertEqual(response.headers['Content-Type'],'image/png');self.assertEqual(response.read(),Path(__file__).with_name(asset).read_bytes())
 def test_original_soundtrack_routes(self):
  for name in ['soundtrack-lobby.wav','soundtrack-battle.wav','soundtrack-frontier-dawn.wav','soundtrack-after-the-dust.wav','soundtrack-stone-and-steel.wav','soundtrack-stormfront.wav','soundtrack-iron-roads.wav','soundtrack-last-citadel.wav']:
   with urllib.request.urlopen('http://localhost:3000/'+name+'?v=2d35') as response:
    self.assertEqual(response.headers['Content-Type'],'audio/wav');data=response.read();self.assertEqual(data[:4],b'RIFF');self.assertEqual(len(data),int(response.headers['Content-Length']))
 def post(self,**data):
  q=urllib.request.Request('http://localhost:3000/api',data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
  try:return json.load(urllib.request.urlopen(q))
  except urllib.error.HTTPError as e:return json.load(e)
 def directory(self,account,search=''):
  q=urllib.request.Request('http://localhost:3000/directory?search='+search,headers={'Authorization':'Bearer '+account})
  return json.load(urllib.request.urlopen(q))['matches']
 def test_username_only_lobby_and_match_flow(self):
  for asset in ['lobby-wallpaper.png','bastion-soldier.png']:
   response=urllib.request.urlopen('http://localhost:3000/'+asset);self.assertEqual(response.headers['Content-Type'],'image/png');self.assertTrue(response.read(8).startswith(b'\x89PNG'))
  accounts=[self.post(action='guest',username='Commander'+str(i)) for i in range(5)]
  self.assertTrue(all('account' in a for a in accounts))
  duplicate=self.post(action='guest',username='COMMANDER0');self.assertIn('error',duplicate)
  login=accounts[0]
  self.assertIn('error',self.post(action='guest',username=''))
  self.assertIn('error',self.post(action='create',account='bad'))
  host=self.post(action='create',account=login['account']);self.post(**host,action='config',map_preset='frontier');self.assertIn('room',host)
  same=self.post(action='create',account=login['account']);self.assertEqual(host,same)
  listing=self.directory(accounts[1]['account'],'commander0');self.assertEqual(listing[0]['host'],'Commander0');self.assertNotIn('token',str(listing))
  peer=self.post(action='join',account=accounts[1]['account'],room=listing[0]['room']);self.assertIn('id',peer)
  third=self.post(action='join',account=accounts[2]['account'],room=host['room'])
  self.assertTrue(self.post(**third,action='leave')['ok'])
  self.assertEqual(len(self.directory(accounts[1]['account'],'commander0')[0]['players']),2)
  third=self.post(action='join',account=accounts[2]['account'],room=host['room']);fourth=self.post(action='join',account=accounts[3]['account'],room=host['room'])
  self.assertTrue(self.directory(accounts[4]['account'],'commander0')[0]['full'])
  self.assertIn('error',self.post(action='join',account=accounts[4]['account'],room=host['room']))
  self.assertIn('error',self.post(**peer,action='start'))
  self.assertTrue(self.post(**host,action='config',mode='teams',ai_enabled=False)['ok']);self.assertTrue(self.post(**host,action='start')['ok'])
  self.assertTrue(self.directory(accounts[4]['account'],'commander0')[0]['full'])
  state=json.load(urllib.request.urlopen('http://localhost:3000/state?room='+host['room']+'&token='+host['token']));self.assertEqual(state['phase'],'intro');self.assertNotIn('account_user',str(state));self.assertNotIn('token',str(state))
  self.assertIn('error',self.post(**host,action='leave'))
 def test_solo_start_and_drop_in_during_intro_and_battle(self):
  users=[self.post(action='guest',username='DropIn'+str(i)) for i in range(5)]
  host=self.post(action='create',account=users[0]['account']);self.post(**host,action='config',map_preset='frontier');self.post(**host,action='config',ai_enabled=False,mode='teams');self.assertTrue(self.post(**host,action='start')['ok'])
  def state(seat):return json.load(urllib.request.urlopen('http://localhost:3000/state?room='+seat['room']+'&token='+seat['token']))
  initial=state(host);self.assertTrue(initial['ai_enabled']);self.assertEqual(sum(bool(p.get('bot')) for p in initial['players']),2)
  peer=self.post(action='join',account=users[1]['account'],room=host['room']);self.assertIn('id',peer)
  deadline=time.monotonic()+14
  while state(host)['phase']=='intro' and time.monotonic()<deadline:time.sleep(.1)
  self.assertEqual(state(host)['phase'],'battle')
  listing=self.directory(users[2]['account'],'dropin0');self.assertEqual(listing[0]['phase'],'battle');self.assertFalse(listing[0]['full'])
  third=self.post(action='join',account=users[2]['account'],room=host['room']);fourth=self.post(action='join',account=users[3]['account'],room=host['room'])
  snapshot=state(third);humans=[p for p in snapshot['players'] if not p.get('bot')];self.assertEqual(len(humans),4);self.assertEqual(len({p['spawn_slot'] for p in humans}),4);self.assertEqual(sorted(p['team'] for p in humans),[1,1,2,2])
  own=next(p for p in humans if p['id']==third['id']);self.assertEqual(own['tech'],[]);self.assertIsNone(own['research']);self.assertFalse(own['autopilot']);self.assertEqual(own['metal'],190)
  self.assertEqual(sum(e['owner']==third['id'] for e in snapshot['entities']),5)
  self.assertIn('error',self.post(action='join',account=users[4]['account'],room=host['room']))

 def test_continental_eight_player_http_drop_in_and_asset_routes(self):
  users=[self.post(action='guest',username='EightEra'+str(i)) for i in range(9)]
  host=self.post(action='create',account=users[0]['account'])
  self.assertTrue(self.post(**host,action='config',map_preset='continental',mode='teams')['ok'])
  self.assertTrue(self.post(**host,action='start')['ok'])
  for i in range(1,8):
   joined=self.post(action='join',account=users[i]['account'],room=host['room'],faction=['Bastion','Vesper','Ironwatch','Nightfall'][i%4]);self.assertIn('id',joined,joined)
  state=json.load(urllib.request.urlopen('http://localhost:3000/state?room='+host['room']+'&token='+host['token']))
  self.assertEqual(state['player_capacity'],8);self.assertEqual(len(state['players']),8);self.assertFalse(any(p.get('bot') for p in state['players']))
  self.assertEqual(len({p['map_slot'] for p in state['players']}),8)
  self.assertIn('error',self.post(action='join',account=users[8]['account'],room=host['room']))
  listing=self.directory(users[8]['account'],'EightEra0')[0];self.assertTrue(listing['full']);self.assertEqual(listing['capacity'],8)
  assets=list(Path(__file__).with_name('historical-designs').glob('industrial-*-directions.png'))
  assets+=[Path(__file__).with_name('historical-designs')/name for name in ['medieval-dock-directions.png','future-gunboat-directions.png','future-transport-directions.png','knight-directions.png','historical-masonry-wrecks-directions.png','early-defense-wrecks-directions.png']]
  for asset in assets:
   with urllib.request.urlopen('http://localhost:3000/historical-designs/'+asset.name) as response:self.assertEqual(response.headers['Content-Type'],'image/png');self.assertEqual(response.read()[:8],b'\x89PNG\r\n\x1a\n')

 def test_new_room_starts_in_stone_age_by_default(self):
  user=self.post(action='guest',username='StoneStart72');host=self.post(action='create',account=user['account'])
  def snapshot():return json.load(urllib.request.urlopen('http://localhost:3000/state?room='+host['room']+'&token='+host['token']))
  self.assertEqual(snapshot()['map_preset'],'continental')
  self.assertTrue(self.post(**host,action='start')['ok']);v=snapshot();p=next(p for p in v['players'] if p['id']==host['id'])
  self.assertEqual(p['historical']['era'],'stone');self.assertEqual(p['tech'],[])
  own=[e for e in v['entities'] if e['owner']==p['id']]
  self.assertTrue(all(e['era_created']=='stone' for e in own))
  self.assertTrue(all(e['historical_role']=='spearman' for e in own if e['kind']=='infantry'))
  self.assertTrue(all(e['historical_role']=='gatherer' for e in own if e['kind']=='harvester'))
  self.assertIn('Industrial',v['lock_reasons']['tank'])

if __name__=='__main__':unittest.main()
