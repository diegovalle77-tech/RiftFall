import unittest,json,threading,urllib.request,math
from pathlib import Path
import server as g
import test_smart_combat74 as baseline
class VehicleArt76(unittest.TestCase):
 def test_hull_heading_survives_stationary_attack(self):
  r,p,q=baseline.SmartCombat74().world();tank=g.entity(r,p,'tank',1000,2000);tank['hull_angle']=.4;target=g.entity(r,q,'engineer',1100,2000);g.command(r,p,dict(action='attack',ids=[tank['id']],target=target['id']));g.tick(r,.1)
  self.assertEqual(tank['hull_angle'],.4);self.assertEqual(tank['combat_target_id'],target['id']);self.assertEqual(tank['turret_angle'],0)
 def test_travel_records_chassis_heading(self):
  r,p,q=baseline.SmartCombat74().world();jeep=g.entity(r,p,'jeep',1000,2000);g.command(r,p,dict(action='move',ids=[jeep['id']],x=1000,y=2300));g.tick(r,.1);self.assertTrue(jeep['moving']);self.assertAlmostEqual(jeep['hull_angle'],math.pi/2)
 def test_vehicle_layers_and_scripts_are_served(self):
  metadata=Path('vehicle-art-atlases.js').read_text().split('const vehicleArtLayouts=')[1].split(';')[0];layouts=json.loads(metadata);self.assertEqual(sum(len(v['cells']) for v in layouts.values()),128)
  server=g.ThreadingHTTPServer(('127.0.0.1',0),g.Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   for file in ['formations.js','vehicle-motion.js','vehicle-art-atlases.js']:
    with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/'+file) as response:self.assertEqual(response.status,200);self.assertIn('javascript',response.headers['Content-Type']);self.assertGreater(len(response.read()),1000)
   for key,layout in layouts.items():
    self.assertEqual(len(layout['cells']),32 if key.endswith('turrets') else 16)
    with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/historical-designs/vehicle-{key}.png') as response:self.assertTrue(response.read().startswith(b'\x89PNG\r\n\x1a\n'))
    if key.endswith('turrets'):
     for pivot,width in zip(layout['pivots'],layout['body_widths']):self.assertTrue(all(v>=0 for v in pivot));self.assertGreater(width,20)
  finally:server.shutdown();server.server_close()
