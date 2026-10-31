import unittest
import server as g
from test_game import room,start_unlocked
class Production(unittest.TestCase):
 def setUp(self):
  self.r=room();start_unlocked(self.r);self.p=self.r['players'][0];self.p.update(credits=10000,metal=1000,wood=1000,riftglass=1000,power=100);self.b=g.entity(self.r,self.p,'barracks',600,600)
 def enqueue(self,kind='infantry'):g.command(self.r,self.p,dict(action='train',kind=kind,producer=self.b['id']))
 def test_timed_fifo_and_payment(self):
  before=len(self.r['entities']);metal=self.p['metal'];self.enqueue();self.enqueue('medic');self.assertEqual(len(self.r['entities']),before);self.assertEqual(self.p['metal'],metal-g.material_costs('infantry')['metal']-g.material_costs('medic')['metal'])
  g.tick_production(self.r,self.p,5);self.assertEqual(len(self.r['entities']),before);self.assertEqual(self.b['production'][0]['progress'],5)
  g.tick_production(self.r,self.p,1);self.assertEqual(self.r['entities'][-1]['kind'],'infantry');self.assertEqual(self.b['production'][0]['kind'],'medic');g.tick_production(self.r,self.p,9);self.assertEqual(self.r['entities'][-1]['kind'],'medic');self.assertEqual(self.b['production'],[])
 def test_pauses_and_destroyed_producer(self):
  self.enqueue();self.b['packed']=True;g.tick_production(self.r,self.p,20);self.assertEqual(self.b['production'][0]['progress'],0);self.b['packed']=False;self.p['power']=-1;g.tick_production(self.r,self.p,20);self.assertEqual(self.b['production'][0]['progress'],0);self.p['power']=100;self.b['hp']=0;g.tick_production(self.r,self.p,20);self.assertEqual(self.b['production'][0]['progress'],0)
 def test_queue_limit(self):
  for _ in range(5):self.enqueue()
  credits=self.p['credits']
  with self.assertRaises(AssertionError):self.enqueue()
  self.assertEqual(self.p['credits'],credits)
