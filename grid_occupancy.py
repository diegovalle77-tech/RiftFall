"""Server-authoritative square footprints, local avoidance and formation slots.
Movement stays continuous. Grid-aligned destinations are reserved separately;
an animation never changes an entity's physical position.
"""
import math,heapq,time

FORMATIONS=('box','line','column','wedge','spread')
UNIT_CELLS={'infantry':(2,2),'grenadier':(2,2),'marksman':(2,2),'medic':(2,2),'engineer':(2,2),'hacker':(2,2),'knight':(5,5),'harvester':(6,6),'tank':(6,6),'walker':(5,5),'jeep':(4,4),'scout':(4,4),'lancer':(6,6),'transport':(7,7),'gunboat':(7,7),'fighter':(6,6),'bomber':(7,7)}

def dimensions(e,footprints,cell=20):
 if e['kind'] in footprints and not e.get('packed'):
  w,h=footprints[e['kind']]
  if abs(math.sin(e.get('facing',e.get('angle',0))))>.7:w,h=h,w
  return w*2,h*2
 cols,rows=(3,3) if e['kind']=='harvester' and e.get('historical_role')=='gatherer' else UNIT_CELLS.get(e['kind'],(4,4))
 return cols*cell,rows*cell

def snap(e,x,y,footprints,cell=20):
 w,h=dimensions(e,footprints,cell);ox=(w/2)%cell;oy=(h/2)%cell
 return (math.floor((x-ox)/cell+.5)*cell+ox,math.floor((y-oy)/cell+.5)*cell+oy)

class Occupancy:
 def __init__(self,room,footprints,terrain,gate_pass,width=14400,height=9600,cell=20):
  self.room=room;self.footprints=footprints;self.terrain=terrain;self.gate_pass=gate_pass;self.width=width;self.height=height;self.cell=cell;self.buckets={};self.members={}
  for e in room.get('entities',[]):
   if e.get('hp',0)>0 and not e.get('embarked'):self.add(e)
 def keys(self,e,x,y):
  w,h=dimensions(e,self.footprints,self.cell);c=self.cell
  return [(cx,cy) for cx in range(math.floor((x-w/2)/c),math.floor((x+w/2-.001)/c)+1) for cy in range(math.floor((y-h/2)/c),math.floor((y+h/2-.001)/c)+1)]
 def remove(self,e):
  for key in self.members.pop(e['id'],[]):
   bucket=self.buckets.get(key)
   if bucket:
    bucket.pop(e['id'],None)
    if not bucket:self.buckets.pop(key,None)
 def add(self,e):
  self.remove(e);keys=self.keys(e,e['x'],e['y']);self.members[e['id']]=keys
  for key in keys:self.buckets.setdefault(key,{})[e['id']]=e
 def nearby(self,e,x,y):
  found={}
  for key in self.keys(e,x,y):found.update(self.buckets.get(key,{}))
  return found.values()
 def blockers(self,e,x,y,static_only=False):
  w,h=dimensions(e,self.footprints,self.cell)
  for other in self.nearby(e,x,y):
   if other['id']==e['id'] or other.get('hp',0)<=0 or other.get('embarked'):continue
   if static_only and (other['kind'] not in self.footprints or other.get('packed')):continue
   if other['kind']=='gate' and self.gate_pass(e,other):continue
   ow,oh=dimensions(other,self.footprints,self.cell)
   # Each touched grid cell is reserved for the whole movement substep.
   # nearby() already intersects the exact cell keys, including fractional positions.
   yield other
 def allowed(self,e,x,y,static_only=False,terrain=True):
  w,h=dimensions(e,self.footprints,self.cell)
  if x-w/2<0 or y-h/2<0 or x+w/2>self.width or y+h/2>self.height:return False
  if terrain and not self.terrain(e,x,y):return False
  return next(self.blockers(e,x,y,static_only),None) is None
 def nearest(self,e,x,y,rings=18,reserved=None,static_only=False):
  x,y=snap(e,x,y,self.footprints,self.cell);reserved=reserved or set()
  for radius in range(rings+1):
   points=[(x,y)] if radius==0 else [(x+dx*self.cell,y+dy*self.cell) for dx in range(-radius,radius+1) for dy in range(-radius,radius+1) if max(abs(dx),abs(dy))==radius]
   points.sort(key=lambda p:(math.hypot(p[0]-x,p[1]-y),math.hypot(p[0]-e['x'],p[1]-e['y'])))
   for px,py in points:
    if not self.allowed(e,px,py,static_only):continue
    if reserved.intersection(self.keys(e,px,py)):continue
    return px,py
  return None
 def move(self,e,x,y):
  # Substeps prevent fast units tunnelling through a thin wall or another unit.
  sx,sy=e['x'],e['y'];n=max(1,math.ceil(math.hypot(x-sx,y-sy)/8))
  for i in range(1,n+1):
   if not self.allowed(e,sx+(x-sx)*i/n,sy+(y-sy)*i/n):return False
  e['x']=x;e['y']=y;self.add(e);return True

 def detour(self,e,destination,limit=2600):
  """Bounded 20-cell A*: stationary traffic is a real obstacle, not a push target."""
  goal=snap(e,*destination,self.footprints,self.cell);start=snap(e,e['x'],e['y'],self.footprints,self.cell)
  if not self.allowed(e,*goal):e.pop('_traffic_job',None);return []
  key=(start,goal,self.room.get('_nav_topology',0))
  job=e.get('_traffic_job')
  if not job or job['key']!=key:
   job=dict(key=key,frontier=[(0,0,start)],cost={start:0},prev={},visited=0);e['_traffic_job']=job
  frontier=job['frontier'];cost=job['cost'];prev=job['prev'];visited=job['visited']
  global_deadline=self.room.get('_navigation_deadline');deadline=min(global_deadline,time.perf_counter()+.004) if global_deadline is not None else None
  while frontier and visited<limit:
   if deadline is not None and visited%8==0 and time.perf_counter()>=deadline:return []
   _,paid,node=heapq.heappop(frontier)
   if paid!=cost[node]:continue
   visited+=1;job['visited']=visited
   if node==goal:
    e.pop('_traffic_job',None)
    out=[]
    while node!=start:out.append(node);node=prev[node]
    return list(reversed(out))
   for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
    nxt=(node[0]+dx*self.cell,node[1]+dy*self.cell)
    if abs(nxt[0]-start[0])>800 or abs(nxt[1]-start[1])>800 or not self.allowed(e,*nxt):continue
    new=paid+1
    if new>=cost.get(nxt,float('inf')):continue
    cost[nxt]=new;prev[nxt]=node;heuristic=(abs(goal[0]-nxt[0])+abs(goal[1]-nxt[1]))/self.cell
    heapq.heappush(frontier,(new+heuristic,new,nxt))
  e.pop('_traffic_job',None)
  return []

def offsets(count,kind,spacing):
 if kind=='line':return [((i-(count-1)/2)*spacing,0) for i in range(count)]
 if kind=='column':return [(0,(i-(count-1)/2)*spacing) for i in range(count)]
 if kind=='wedge':
  out=[(0,0)]
  for i in range(1,count):
   rank=(i+1)//2;out.append(((-1 if i%2 else 1)*rank*spacing,rank*spacing))
 else:
  cols=math.ceil(math.sqrt(count));out=[((i%cols-(cols-1)/2)*spacing,(i//cols-(math.ceil(count/cols)-1)/2)*spacing) for i in range(count)]
 if kind=='wedge':
  mean=sum(p[1] for p in out)/count;out=[(x,y-mean) for x,y in out]
 return out

def formation_slots(index,movers,x,y,kind='box',angle=0):
 if kind not in FORMATIONS:raise AssertionError('Choose box, line, column, wedge or spread')
 if not movers:raise AssertionError('Select mobile units first')
 spacing=math.ceil((max(max(dimensions(e,index.footprints,index.cell)) for e in movers)+index.cell)/index.cell)*index.cell
 if kind=='spread':spacing*=2
 points=sorted(offsets(len(movers),kind,spacing),key=lambda p:p[0]*p[0]+p[1]*p[1]);remaining=list(movers);reserved=set();result=[]
 for unit in movers:index.remove(unit)
 for ox,oy in points:
  tx=x+ox*math.cos(angle)-oy*math.sin(angle);ty=y+ox*math.sin(angle)+oy*math.cos(angle)
  # Nearest unit takes each slot: fewer crossing paths, stable tie-break by ID.
  unit=min(remaining,key=lambda e:(math.hypot(tx-e['x'],ty-e['y']),e['id']));remaining.remove(unit)
  slot=index.nearest(unit,tx,ty,rings=24,reserved=reserved,static_only=False)
  if slot is None:raise AssertionError('Not enough clear grid space for this formation')
  reserved.update(index.keys(unit,*slot));result.append((unit,slot))
 return result
