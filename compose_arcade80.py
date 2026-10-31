"""Original synthesized techno/arcade-rock lobby music; no recordings or samples."""
from pathlib import Path
import wave,json
import numpy as np
RATE=22050
TRACKS=[dict(file='neon-foundry',title='Neon Foundry',bpm=132,roots=[40,40,48,43,40,47,43,38],riff=[0,7,12,3,7,10,12,7]),dict(file='pixel-rebellion',title='Pixel Rebellion',bpm=144,roots=[45,48,43,40,45,43,41,40],riff=[0,12,7,15,12,7,3,10]),dict(file='rift-drive',title='Rift Drive',bpm=126,roots=[38,41,45,43,38,45,48,41],riff=[0,3,7,12,10,7,15,12])]
def compose(spec):
 beat=60/spec['bpm'];bars=40;size=round(bars*4*beat*RATE);mix=np.zeros((size,2));rng=np.random.default_rng(spec['bpm']);cache={}
 def tone(midi,length,voice):
  key=(midi,round(length,4),voice)
  if key in cache:return cache[key]
  t=np.arange(round(length*RATE))/RATE;phase=2*np.pi*440*2**((midi-69)/12)*t
  if voice=='chip':sound=sum(np.sin(phase*h)/h for h in [1,3,5,7,9])*.6
  elif voice=='guitar':sound=np.tanh(sum(np.sin(phase*h)*np.exp(-t*h*.8)/h for h in range(1,10))*2.4)
  elif voice=='bass':sound=np.sin(phase)+.3*np.sin(phase*2)
  else:sound=sum(np.sin(phase*h)/h**1.6 for h in range(1,8))
  env=np.minimum(1,t/.004)*np.minimum(1,(length-t)/.025)*np.exp(-t*(5 if voice=='guitar' else 2));cache[key]=sound*env;return cache[key]
 def add(sound,at,gain,pan=0):
  start=round(at*RATE);n=min(len(sound),size-start)
  if n<=0:return
  mix[start:start+n,0]+=sound[:n]*gain*np.sqrt((1-pan)/2);mix[start:start+n,1]+=sound[:n]*gain*np.sqrt((1+pan)/2)
 t=np.arange(round(.35*RATE))/RATE;kick=np.sin(2*np.pi*(48*t+2.6*(1-np.exp(-t/.023))))*np.exp(-t*15)
 t=np.arange(round(.19*RATE))/RATE;snare=(rng.normal(size=len(t))*.35+np.sin(2*np.pi*180*t)*.4)*np.exp(-t*24)
 t=np.arange(round(.06*RATE))/RATE;n=rng.normal(size=len(t));hat=np.diff(n,prepend=n[0])*.17*np.exp(-t*60)
 for bar in range(bars):
  start=bar*4*beat;root=spec['roots'][(bar//2)%8];breakdown=16<=bar<20;intro=bar<4
  for step in range(16):
   at=start+step*beat/4
   if step%4==0 and not breakdown:add(kick,at,.65)
   if step in [4,12] and not intro and not breakdown:add(snare,at,.34)
   if step%2==0:add(hat,at,.45 if step%4==2 else .23,.35)
   if not breakdown and step%2==0:
    add(tone(root-12,beat*.42,'bass'),at,.19)
    add(tone(root,beat*.34,'guitar'),at,.085,-.55);add(tone(root+7,beat*.34,'guitar'),at,.07,.55)
   if bar>=4 and (step%2==0 or bar%4==3):
    degree=spec['riff'][(step//2+bar//4)%8];voice='chip' if spec['file']=='pixel-rebellion' else 'synth'
    add(tone(root+24+degree,beat*.32,voice),at,.065 if breakdown else .1,.15)
  if breakdown:
   for chord in [0,7,12]:add(tone(root+12+chord,beat*3.8,'synth'),start,.07)
 dry=mix.copy();delay=round(beat*.75*RATE);mix[delay:,0]+=dry[:-delay,1]*.16;mix[delay:,1]+=dry[:-delay,0]*.16
 mix=np.tanh(mix);mix*=.84/max(.001,np.max(np.abs(mix)));fade=np.minimum(1,np.arange(size)/RATE/.08)*np.minimum(1,(size-1-np.arange(size))/RATE/.7);mix*=fade[:,None]
 path=Path(__file__).with_name('soundtrack-'+spec['file']+'.wav')
 with wave.open(str(path),'wb') as out:out.setparams((2,2,RATE,0,'NONE','not compressed'));out.writeframes((mix*32767).astype('<i2').tobytes())
 print(spec['title'],round(size/RATE,1),'seconds')
if __name__=='__main__':
 for spec in TRACKS:compose(spec)
 Path(__file__).with_name('soundtrack-arcade-catalog.json').write_text(json.dumps(TRACKS,indent=2))
