import unittest,time,threading,json,urllib.request
from unittest.mock import patch
import server as g
from test_game import room
class Runtime78(unittest.TestCase):
 def test_local_barrier_candidates_do_not_scan_entire_base(self):
  walls=[dict(id=str(i),kind='wall',x=1000+(i%50)*60,y=1000+(i//50)*100,hp=100,owner='p',angle=0) for i in range(1000)]
  index=g.barrier_index.BarrierIndex(walls);self.assertLess(len(list(index.nearby(1100,1000,1120,1020))),30);self.assertEqual(index.corners,set())
 def test_slow_response_is_sent_after_simulation_lock_is_released(self):
  handler=object.__new__(g.Handler);writes=[]
  def send(body,code):
   check=[]
   def probe():
    acquired=g.LOCK.acquire(timeout=.05);check.append(acquired)
    if acquired:g.LOCK.release()
   t=threading.Thread(target=probe);t.start();t.join();writes.append(check[0]);self.assertEqual(json.loads(body),{'ok':True})
  handler.send_bytes=send
  with handler.game_lock():handler.send({'ok':True});self.assertEqual(writes,[])
  self.assertEqual(writes,[True])
 def test_incremental_path_survives_its_frame_budget(self):
  r=room();g.start(r);p=r['players'][0];e=g.entity(r,p,'jeep',2400,2400);clock=[0]
  def counter():clock[0]+=.0005;return clock[0]
  with patch.object(g.time,'perf_counter',side_effect=counter):
   r['_navigation_deadline']=.003;self.assertEqual(g.navigation_path(r,e,[3700,2400]),[]);self.assertIn('_nav_job',e)
   for _ in range(120):
    r['_navigation_deadline']=clock[0]+.01;path=g.navigation_path(r,e,[3700,2400])
    if path:break
   self.assertTrue(path);self.assertNotIn('_nav_job',e)
 def test_early_worker_footprint_is_smaller_than_machine(self):
  self.assertEqual(g.grid_occupancy.dimensions(dict(kind='harvester',historical_role='gatherer'),g.FOOTPRINTS),(60,60));self.assertEqual(g.grid_occupancy.dimensions(dict(kind='harvester'),g.FOOTPRINTS),(120,120))
 def test_new_frontend_and_art_assets_have_working_routes(self):
  server=g.ThreadingHTTPServer(('127.0.0.1',0),g.Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   for name in ['lobby-cinema.js','lobby-cinema.css','world-artwork.js','wall-artwork.js','responsive-runtime.js','historical-designs/resources-painted-v78.png','historical-designs/era-roads-painted-v78.png','historical-designs/era-barriers-painted-v78.png']:
    with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/'+name) as response:
     self.assertEqual(response.status,200);data=response.read();self.assertGreater(len(data),500)
     if name.endswith('.png'):self.assertTrue(data.startswith(b'\x89PNG\r\n\x1a\n'))
  finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
