import unittest,math
from collections import deque
import historic_map as m
class HistoricMapGeometry(unittest.TestCase):
 def connected(self,start,end,water):
  step=200
  def node(p):return (round(p[0]/step),round(p[1]/step))
  def valid(v):
   x,y=v[0]*step,v[1]*step
   return 0<=x<=m.WIDTH and 0<=y<=m.HEIGHT and (m.is_water(x,y) if water else m.is_land(x,y))
  src,dst=node(start),node(end);todo=deque([src]);seen={src}
  while todo:
   v=todo.popleft()
   if v==dst:return True
   for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
    n=(v[0]+dx,v[1]+dy)
    if n not in seen and valid(n):seen.add(n);todo.append(n)
  return False
 def test_eight_peripheral_starts_equally_distant_and_on_land(self):
  positions=m.starting_positions();self.assertEqual(len(positions),8)
  for p in positions:self.assertTrue(m.is_land(*p));self.assertAlmostEqual(math.dist(p,m.CENTER),m.START_RADIUS)
 def test_equal_starter_resources_and_island_gold(self):
  nodes=m.resource_layout();starter=[n for n in nodes if n['region']=='starter'];self.assertEqual(len(starter),40)
  for i in range(8):
   found=[n for n in starter if n['slot']==i];self.assertEqual({n['kind'] for n in found},set(m.RESOURCE_KINDS));self.assertTrue(all(n['finite'] and m.is_land(n['x'],n['y']) for n in found))
  islands=[n for n in nodes if n['region']=='island'];self.assertEqual(len(islands),2);self.assertTrue(all(n['kind']=='gold' and n['stock']==150000 and m.is_island(n['x'],n['y']) for n in islands))
 def test_land_paths_and_nav_channel(self):
  starts=m.starting_positions()
  for point in starts[1:]:self.assertTrue(self.connected(starts[0],point,False),point)
  self.assertTrue(self.connected((m.CENTER[0],m.CENTER[1]),(m.WIDTH-400,m.CENTER[1]),True))
  for island in m.ISLANDS:
   approach=(island.x,island.y+island.ry+200);self.assertTrue(m.is_water(*approach));self.assertTrue(self.connected(approach,(m.WIDTH-400,m.CENTER[1]),True))
 def test_passes_and_mountains(self):
  self.assertTrue(m.is_mountain(4450,1600));self.assertTrue(m.is_land(4450,3100));self.assertTrue(m.is_water(800,200))
if __name__=='__main__':unittest.main()
