import json, threading, unittest, urllib.request, urllib.error
from unittest.mock import patch
import server as g
from test_game import room
class ConnectionRecovery79(unittest.TestCase):
 def test_combat_scenery_visibility(self):
  r=room();g.start(r);p=r['players'][0];unit=next(e for e in r['entities'] if e['owner']==p['id'])
  for key in ['fires','craters','effects']:r[key]=[dict(x=unit['x'],y=unit['y'],id='near'),dict(x=g.WORLD_W*10,y=g.WORLD_H*10,id='far')]
  v=g.view(r,p)
  for key in ['fires','craters','effects']:self.assertEqual([o['id'] for o in v[key]],['near'])
  json.dumps(v)
 def test_structure_extents_preserved(self):
  self.assertEqual(g.target_extent(dict(kind='bridge',span=600)),300)
  self.assertEqual(g.target_extent(dict(kind='core')),max(g.FOOTPRINTS['core']))
  self.assertEqual(g.target_extent(dict(x=0,y=0)),0)
 def test_internal_failure_does_not_expire_session(self):
  r=room();code='RECOVERY79';r['code']=code;g.ROOMS[code]=r
  server=g.ThreadingHTTPServer(('127.0.0.1',0),g.Handler);threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
  def request(query):
   try:
    with urllib.request.urlopen(base+'/state?'+query) as response:return response.status,json.load(response)
   except urllib.error.HTTPError as error:return error.code,json.load(error)
  try:
   for query in ['',f'room={code}',f'room={code}&token=bad','room=missing&token=secret0']:
    status,data=request(query);self.assertEqual(status,404);self.assertEqual(data['code'],'invalid_session')
   with patch.object(g,'view',side_effect=KeyError('kind')),patch('traceback.print_exc'):
    status,data=request(f'room={code}&token=secret0');self.assertEqual(status,500);self.assertEqual(data['code'],'state_unavailable');self.assertNotIn('session not found',data['error'])
   status,data=request(f'room={code}&token=secret0');self.assertEqual(status,200);self.assertEqual(data['code'],code)
  finally:server.shutdown();server.server_close();g.ROOMS.pop(code,None)
if __name__=='__main__':unittest.main()
