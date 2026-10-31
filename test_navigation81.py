import unittest
from unittest.mock import patch
import server as g
from test_game import room
class NavigationBudget81(unittest.TestCase):
 def test_budget_yield_retries_next_frame_without_unreachable_cooldown(self):
  r=room();g.start(r);p=r['players'][0];unit=g.entity(r,p,'infantry',2400,2000);destination=[2600,2000]
  r['_navigation_deadline']=1
  with patch.object(g,'ground_line_clear',return_value=False),patch.object(g.time,'perf_counter',return_value=2):
   self.assertEqual(g.navigation_destination(r,unit,destination),destination)
   self.assertEqual(unit['_route_retry'],r['elapsed']);self.assertNotIn('_nav_job',unit)
  r['elapsed']+=.1;r['_navigation_deadline']=10
  with patch.object(g,'ground_line_clear',return_value=False),patch.object(g.time,'perf_counter',return_value=2),patch.object(g,'navigation_path',return_value=[(2500,2100),tuple(destination)]) as search:
   self.assertEqual(g.navigation_destination(r,unit,destination),(2500,2100));search.assert_called_once()
 def test_exhausted_search_keeps_backoff(self):
  r=room();g.start(r);unit=g.entity(r,r['players'][0],'infantry',2400,2000);r['_navigation_deadline']=10
  with patch.object(g,'ground_line_clear',return_value=False),patch.object(g.time,'perf_counter',return_value=2),patch.object(g,'navigation_path',return_value=[]) as search:
   g.navigation_destination(r,unit,[2600,2000]);self.assertEqual(unit['_route_retry'],r['elapsed']+2)
   g.navigation_destination(r,unit,[2600,2000]);self.assertEqual(search.call_count,1)
 def test_local_detour_resumes_across_small_frame_budgets(self):
  r=room();g.start(r);p=r['players'][0];r['entities']=[]
  unit=g.entity(r,p,'infantry',2000,2000);g.entity(r,p,'wall',2080,2000)
  index=g.make_occupancy(r);clock=[0]
  def counter():clock[0]+=.0015;return clock[0]
  with patch.object(g.time,'perf_counter',side_effect=counter):
   r['_navigation_deadline']=.02;path=index.detour(unit,[2200,2000]);self.assertFalse(path);self.assertIn('_traffic_job',unit)
   for _ in range(100):
    r['_navigation_deadline']=clock[0]+.02;path=index.detour(unit,[2200,2000])
    if path:break
  self.assertTrue(path);self.assertNotIn('_traffic_job',unit)
  proxy=dict(unit)
  for x,y in path:
   self.assertTrue(index.move(proxy,x,y))
 def test_new_order_clears_pending_local_search(self):
  r=room();g.start(r);p=r['players'][0];unit=g.entity(r,p,'infantry',2400,2000);unit['_traffic_job']={'key':'old'}
  g.command(r,p,dict(action='move',ids=[unit['id']],x=2600,y=2000));self.assertNotIn('_traffic_job',unit)
if __name__=='__main__':unittest.main()
