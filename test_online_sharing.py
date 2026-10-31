import hashlib,io,json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
import online_tunnel as online
import server as g
from test_game import room
class OnlineConnector(unittest.TestCase):
 def test_only_cloudflare_https_addresses_are_accepted(self):
  self.assertEqual(online.tunnel_url('Tunnel ready https://painted-river-bridge.trycloudflare.com |'),'https://painted-river-bridge.trycloudflare.com')
  self.assertIsNone(online.tunnel_url('http://localhost:3018'))
 def test_download_checksum_and_cache(self):
  payload=b'official connector test fixture';checksum=hashlib.sha256(payload).hexdigest()
  with tempfile.TemporaryDirectory() as folder,patch.object(online.shutil,'which',return_value=None),patch.object(online.platform,'system',return_value='Windows'),patch.object(online.platform,'machine',return_value='AMD64'),patch.dict(online.ASSETS,{('Windows','amd64'):('fixture.exe',checksum)}),patch.object(online,'urlopen',return_value=io.BytesIO(payload)) as download:
   executable=online.ensure_client(folder);self.assertEqual(Path(executable).read_bytes(),payload);self.assertEqual(online.ensure_client(folder),executable);self.assertEqual(download.call_count,1)
 def test_corrupt_download_is_never_installed(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(online.shutil,'which',return_value=None),patch.object(online.platform,'system',return_value='Windows'),patch.object(online.platform,'machine',return_value='AMD64'),patch.dict(online.ASSETS,{('Windows','amd64'):('fixture.exe','0'*64)}),patch.object(online,'urlopen',return_value=io.BytesIO(b'corrupt')):
   with self.assertRaisesRegex(RuntimeError,'checksum'):online.ensure_client(folder)
   self.assertEqual(list(Path(folder).iterdir()),[])
 def test_connected_status_requires_registration_and_process_stops(self):
  notifications=[]
  class Process:
   def __init__(self):self.ended=False;self.stdout=iter(['https://friendly-river.trycloudflare.com\n','Registered tunnel connection connIndex=0\n'])
   def poll(self):return 0 if self.ended else None
   def terminate(self):self.ended=True
   def wait(self,timeout=None):return 0
  process=Process();tunnel=None
  def notify(status,url,message):
   notifications.append((status,url))
   if status=='online':tunnel.stop()
  tunnel=online.OnlineTunnel(3018,notify)
  with patch.object(online,'ensure_client',return_value='cloudflared'),patch.object(online.subprocess,'Popen',return_value=process):tunnel.run()
  self.assertIn(('online','https://friendly-river.trycloudflare.com'),notifications);self.assertTrue(process.ended)
 def test_install_failure_shows_error_without_publishing_link(self):
  events=[];tunnel=online.OnlineTunnel(3018,lambda *args:events.append(args))
  with patch.object(online,'ensure_client',side_effect=RuntimeError('Download failed')):tunnel.run()
  self.assertEqual(events[-1][0],'error');self.assertIsNone(events[-1][1])
class ShareHTTP(unittest.TestCase):
 def test_room_token_required_and_only_public_address_is_returned(self):
  r=room();g.ROOMS[r['code']]=r;p=r['players'][0];previous=g.ONLINE_STATUS.copy();server=g.ThreadingHTTPServer(('127.0.0.1',0),g.Handler);threading.Thread(target=server.serve_forever,daemon=True).start();origin='http://127.0.0.1:'+str(server.server_port)
  try:
   g.online_status('online','https://test-riftfall.trycloudflare.com','Ready')
   with urllib.request.urlopen(origin+'/share?room='+r['code']+'&token='+p['token']) as response:data=json.load(response)
   self.assertEqual(data['room'],r['code']);self.assertEqual(data['url'],'https://test-riftfall.trycloudflare.com');self.assertNotIn(p['token'],json.dumps(data));self.assertNotIn('players',data)
   with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(origin+'/share?room='+r['code']+'&token=invalid')
   with urllib.request.urlopen(origin+'/?join='+r['code']) as response:self.assertIn(b'Join friend',response.read())
  finally:server.shutdown();server.server_close();g.ROOMS.pop(r['code'],None);g.ONLINE_STATUS.clear();g.ONLINE_STATUS.update(previous)
