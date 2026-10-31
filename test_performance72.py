import math,random,unittest
import server as g
class PerformanceRegression(unittest.TestCase):
 def test_combat_index_matches_brute_force_in_range(self):
  rng=random.Random(72)
  units=[dict(id=str(i),x=rng.uniform(0,14400),y=rng.uniform(0,9600),hp=100,owner=i%4) for i in range(2400)]
  index=g.CombatIndex(units)
  for e in units[::80]:
   radius=300
   expected={u['id'] for u in units if g.dist(e,u)<radius}
   candidates=list(index.nearby(e,radius))
   actual={u['id'] for u in candidates if g.dist(e,u)<radius}
   self.assertEqual(expected,actual)
   self.assertLess(len(candidates),len(units)//10)
 def test_dead_and_embarked_units_not_in_index(self):
  alive=dict(id='a',x=100,y=100,hp=1)
  index=g.CombatIndex([alive,dict(id='dead',x=100,y=100,hp=0),dict(id='passenger',x=100,y=100,hp=1,embarked='ship')])
  self.assertEqual(list(index.nearby(alive,200)),[alive])
