import array, hashlib, unittest, wave, json
from pathlib import Path
class ExpandedMusic(unittest.TestCase):
 def test_six_distinct_stereo_compositions_have_safe_levels(self):
  hashes=set()
  for name in ['frontier-dawn','after-the-dust','stone-and-steel','stormfront','iron-roads','last-citadel']:
   path=Path(__file__).with_name('soundtrack-'+name+'.wav');data=path.read_bytes();hashes.add(hashlib.sha256(data).hexdigest())
   with wave.open(str(path)) as audio:
    self.assertEqual(audio.getnchannels(),2);self.assertEqual(audio.getsampwidth(),2);self.assertEqual(audio.getframerate(),22050);self.assertGreater(audio.getnframes()/audio.getframerate(),50)
    samples=array.array('h',audio.readframes(audio.getnframes()));peak=max(abs(n) for n in samples[::8]);self.assertGreater(peak,1000);self.assertLess(peak,32767)
  self.assertEqual(len(hashes),6)

 def test_arrangements_have_different_meters_melodies_and_instruments(self):
  catalog=json.loads(Path(__file__).with_name('soundtrack-catalog.json').read_text())
  self.assertEqual(len({s['meter'] for s in catalog}),6);self.assertEqual(len({s['bpm'] for s in catalog}),6);self.assertEqual(len({s['lead'] for s in catalog}),6);self.assertEqual(len({tuple(s['melody']) for s in catalog}),6)
