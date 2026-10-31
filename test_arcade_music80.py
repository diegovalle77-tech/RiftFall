import array,hashlib,json,threading,unittest,urllib.request,wave
from pathlib import Path
import server as g
class ArcadeMusic80(unittest.TestCase):
 def test_original_tracks_and_playable_routes(self):
  root=Path(__file__).parent;catalog=json.loads((root/'soundtrack-arcade-catalog.json').read_text());hashes=set()
  server=g.ThreadingHTTPServer(('127.0.0.1',0),g.Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   for spec in catalog:
    name='soundtrack-'+spec['file']+'.wav';data=(root/name).read_bytes();hashes.add(hashlib.sha256(data).hexdigest())
    with wave.open(str(root/name)) as audio:
     self.assertEqual(audio.getnchannels(),2);self.assertEqual(audio.getframerate(),22050);self.assertEqual(audio.getsampwidth(),2);self.assertGreater(audio.getnframes()/22050,60)
     samples=array.array('h',audio.readframes(audio.getnframes()));self.assertLess(max(abs(x) for x in samples),32767);self.assertGreater(max(samples),20000)
    with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/{name}?v=80') as response:
     self.assertEqual(response.headers['Content-Type'],'audio/wav');self.assertEqual(response.read(),data)
    self.assertIn(name,(root/'index.html').read_text())
   self.assertEqual(len(hashes),3)
  finally:server.shutdown();server.server_close()
