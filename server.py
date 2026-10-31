import json, math, secrets, threading, time, random, os, re, heapq
import barrier_index
from contextlib import contextmanager
import grid_occupancy
import era_rules
import historic_map
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
ONLINE_STATUS={'status':'local','url':None,'message':'For a friend on another network, close this server and run start-online.bat.'}
def online_status(status,url,message):
 ONLINE_STATUS.update(status=status,url=url,message=message)
WORLD_W=14400; WORLD_H=9600
GRID_SIZE=20
WALL_SPAN=60
NAVAL={'transport','gunboat'}
TRANSPORTABLE={'infantry','grenadier','marksman','medic','engineer','hacker'}
TRANSPORT_CAPACITY=8
MEDIC_RANGE=120
INTRO_DURATION=10.0
HARVESTER_CAPACITY=750
DEPOSIT_STOCK=40000
MINE_STOCK=250000
def deposit_stock(kind):return MINE_STOCK if kind=='metal' else DEPOSIT_STOCK
START_BASES=[(260,260),(WORLD_W-260,WORLD_H-260),(WORLD_W-260,260),(260,WORLD_H-260),(WORLD_W/2+900,260),(WORLD_W/2+900,WORLD_H-260)]
def river_point(u):
 second=u>.5;v=(u-.5)*2 if second else u*2;k=1-v
 a,b,c,d=([(2000,1250),(2240,1660),(1580,2070),(1790,2400)] if second else [(1680,0),(2110,500),(1450,850),(2000,1250)])
 return (4*(k**3*a[0]+3*k*k*v*b[0]+3*k*v*v*c[0]+v**3*d[0]),4*(k**3*a[1]+3*k*k*v*b[1]+3*k*v*v*c[1]+v**3*d[1]))
RIVER_SAMPLES=[river_point(i/240) for i in range(241)]
RIVER_BUCKETS={}
for rx,ry in RIVER_SAMPLES:
 for bucket in range(int(ry//200)-2,int(ry//200)+3):RIVER_BUCKETS.setdefault(bucket,[]).append((rx,ry))
def water_at(x,y,r=None):
 if r and r.get('_map_geometry')=='continental':return historic_map.is_water(x,y)
 if any(abs(y-ry)<250 and (x-rx)**2+(y-ry)**2<230**2 for rx,ry in RIVER_BUCKETS.get(int(y//200),[])):return True
 for i,(lx,ly) in enumerate([(3480,3440),(10800,6120),(3120,6320),(11400,3280)]):
  a=i*.7;dx=x-lx;dy=y-ly;u=dx*math.cos(a)+dy*math.sin(a);v=-dx*math.sin(a)+dy*math.cos(a)
  if (u/700)**2+(v/340)**2<1:return True
 return False
def water_building(r,p,kind,x,y):
 w,h=FOOTPRINTS[kind];wet=any(water_at(x+ox,y+oy,r=r) for ox,oy in [(0,0),(-w,-h),(w,-h),(-w,h),(w,h)])
 if kind=='dock':return not water_at(x,y,r=r) and any(water_at(x+math.cos(a)*150,y+math.sin(a)*150,r=r) for a in [i*math.tau/12 for i in range(12)])
 return not wet or any(e['kind']=='dock' and e['hp']>0 and not under_construction(e) and ally(r,p['id'],e['owner']) and dist(e,dict(x=x,y=y))<320 for e in r['entities'])
def bridge_contains(bridge,x,y,margin=0):
 a=bridge.get('angle',0);dx=x-bridge['x'];dy=y-bridge['y'];along=dx*math.cos(a)+dy*math.sin(a);across=-dx*math.sin(a)+dy*math.cos(a)
 return abs(along)<=bridge.get('span',480)/2+margin and abs(across)<=bridge.get('deck_width',100)/2+margin
ROAD_ROUTES=[[(260, 260), (1800, 1500), (2100, 2900), (4500, 3300), (6000, 3400), (6500, 4600), (8800, 6000), (10000, 7000), (10100, 8700), (12200, 9000), (14140, 9340)], [(260, 9340), (2200, 8700), (2600, 7000), (4400, 6400), (6000, 5000), (9600, 3200), (10000, 1500), (12200, 1200), (14140, 260)]]
def road_lane(x,y,margin=0,r=None):
 for route in (r.get('road_routes',[]) if r and r.get('_map_geometry')=='continental' else ROAD_ROUTES):
  for (ax,ay),(bx,by) in zip(route,route[1:]):
   dx=bx-ax;dy=by-ay;t=max(0,min(1,((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
   if math.hypot(x-(ax+t*dx),y-(ay+t*dy))<80+margin:return True
 return False
def roadside_lane(r,x,y,margin=0):
 for site in r.get('props',[]):
  if site['kind']!='road_business' or site.get('hp',0)<=0:continue
  park=site.get('parking');access=site.get('road_access')
  if park:
   a=park.get('angle',0);dx=x-park['x'];dy=y-park['y']
   if abs(dx*math.cos(a)+dy*math.sin(a))<100+margin and abs(-dx*math.sin(a)+dy*math.cos(a))<50+margin:return True
  if access:
   for start in [site]+([park] if park else []):
    dx=access['x']-start['x'];dy=access['y']-start['y'];t=max(0,min(1,((x-start['x'])*dx+(y-start['y'])*dy)/(dx*dx+dy*dy or 1)))
    if math.hypot(x-start['x']-dx*t,y-start['y']-dy*t)<22+margin:return True
 return False
def route_lane(r,x,y,margin=0):return road_lane(x,y,margin,r=r) or bridge_lane(r,x,y,margin) or roadside_lane(r,x,y,margin)
def bridge_lane(r,x,y,margin=0):
 for bridge in r.get('props',[]):
  if bridge['kind']!='bridge':continue
  a=bridge.get('angle',0);dx=x-bridge['x'];dy=y-bridge['y'];along=dx*math.cos(a)+dy*math.sin(a);across=-dx*math.sin(a)+dy*math.cos(a)
  if abs(along)<=bridge.get('span',480)/2+460+margin and abs(across)<=bridge.get('deck_width',100)/2+120+margin:return True
 return False

def prepare_mine(r,node):
 if node['kind']!='metal':return
 node['max_stock']=MINE_STOCK;node['site']='mine';spots=[]
 for ox,oy in [(125,65),(-125,65),(0,110),(0,-175),(175,-20),(-175,-20)]:
  x,y=grid_occupancy.snap(dict(kind='harvester'),node['x']+ox,node['y']+oy,FOOTPRINTS)
  if not grid_terrain(r,dict(kind='harvester'),x,y):continue
  if not (50<x<WORLD_W-50 and 50<y<WORLD_H-50) or water_at(x,y,r=r) or cliff_at(r,x,y) or route_lane(r,x,y,55):continue
  spots.append(dict(x=x,y=y))
  if len(spots)==2:break
 node['parking_spots']=spots
 # A mine includes a cleared work yard, so decorative resources never cover its loading bays.
 r['props']=[prop for prop in r.get('props',[]) if prop['kind'] not in ['tree','rock','ruin'] or (math.hypot(prop['x']-node['x'],prop['y']-node['y'])>170 and all(math.hypot(prop['x']-spot['x'],prop['y']-spot['y'])>100 for spot in spots))]

def mining_anchor(r,node,e):
 spots=node.get('parking_spots',[])
 if not spots:return node
 if e.get('_mine_node')!=node['id']:
  counts=[sum(other.get('_mine_node')==node['id'] and other.get('_mine_slot')==i for other in r['entities'] if other is not e and other['kind']=='harvester') for i in range(len(spots))]
  e['_mine_slot']=min(range(len(spots)),key=lambda i:(counts[i],dist(e,spots[i])));e['_mine_node']=node['id']
 return spots[e.get('_mine_slot',0)%len(spots)]
def material_sources(r):
 return r['nodes']+[prop for prop in r.get('props',[]) if 'stock' in prop]+r.get('wrecks',[])
def material_kind(source):return source.get('resource',source['kind'])
def passable_water(r,e,x,y):
 if e['kind'] in NAVAL:return water_at(x,y,r=r)
 return e['kind'] in ['tank','fighter','bomber'] or not water_at(x,y,r=r) or any(b['kind']=='bridge' and b['hp']>0 and bridge_contains(b,x,y,2) for b in r.get('props',[]))
CLIFFS=[dict(id='cliff-'+str(i),points=[(cx-400,cy-160),(cx-170,cy-310),(cx+260,cy-240),(cx+480,cy+30),(cx+180,cy+290),(cx-330,cy+200)]) for i,(cx,cy) in enumerate([(3000,2400),(10900,2400),(3600,7600),(11000,8000)])]
HILLS=[dict(x=x,y=y,radius=radius,height=height) for x,y,radius,height in [(1800,3500,650,75),(12500,5000,750,90),(5000,8000,700,80),(10000,3800,600,70)]]
def in_polygon(x,y,points):
 inside=False;j=len(points)-1
 for i,(px,py) in enumerate(points):
  qx,qy=points[j]
  if (py>y)!=(qy>y) and x<(qx-px)*(y-py)/(qy-py)+px:inside=not inside
  j=i
 return inside
def cliff_at(r,x,y):
 if r.get('_map_geometry')=='continental':return historic_map.is_mountain(x,y)
 return any(in_polygon(x,y,c['points']) for c in r.get('cliffs',CLIFFS))
def ground_line_clear(r,e,x0,y0,x1,y1):
 occupancy=r.get('_occupancy') or make_occupancy(r)
 n=max(1,int(math.hypot(x1-x0,y1-y0)/28)+1)
 for i in range(1,n+1):
  x=x0+(x1-x0)*i/n;y=y0+(y1-y0)*i/n
  if not occupancy.allowed(e,x,y,static_only=True):return False
 proxy={**e,'x':x0,'y':y0}
 return barrier_hit(r,proxy,x1,y1) is None
NAV_CELL=80
def navigation_path(r,e,destination):
 width=math.ceil(WORLD_W/NAV_CELL);height=math.ceil(WORLD_H/NAV_CELL);static=r.setdefault('_nav_static',{});bridges=[b for b in r.get('props',[]) if b['kind']=='bridge' and b['hp']>0];amphibious=e['kind']=='tank';naval=e['kind'] in NAVAL
 occupancy=r.get('_occupancy') or make_occupancy(r)
 def center(node):return((node[0]+.5)*NAV_CELL,(node[1]+.5)*NAV_CELL)
 def allowed(node):
  if not(0<=node[0]<width and 0<=node[1]<height):return False
  if node not in static:
   x,y=center(node);static[node]=(cliff_at(r,x,y),water_at(x,y,r=r))
  cliff,water=static[node]
  if cliff or (naval and not water) or not occupancy.allowed(e,*center(node),static_only=True):return False
  if not amphibious and not naval and water:
   if not any(bridge_contains(b,*center(node),2) for b in bridges):return False
  return True
 def nearest(x,y):
  node=(int(x//NAV_CELL),int(y//NAV_CELL))
  if allowed(node):return node
  for radius in range(1,5):
   candidates=[]
   for dx in range(-radius,radius+1):
    for dy in range(-radius,radius+1):
     test=(node[0]+dx,node[1]+dy)
     if allowed(test):
      tx,ty=center(test);candidates.append(((tx-x)**2+(ty-y)**2,test))
   if candidates:return min(candidates)[1]
  return node
 budget=r.get('_navigation_deadline')
 if budget is not None and time.perf_counter()>=budget:return []
 start=nearest(e['x'],e['y']);goal=nearest(*destination);topology=r.get('_nav_topology',0);key=(start,goal,amphibious,naval,e['owner'],grid_occupancy.dimensions(e,FOOTPRINTS),topology);cache=r.setdefault('_route_cache',{})
 if key in cache:e.pop('_nav_job',None);return list(cache[key])
 job=e.get('_nav_job')
 if not job or job['key']!=key:
  if budget is not None and not job and sum(bool(u.get('_nav_job')) for u in r['entities'])>=16:return []
  job=dict(key=key,frontier=[(0,start)],cost={start:0},previous={},visits=0);e['_nav_job']=job
 frontier=job['frontier'];cost=job['cost'];previous=job['previous'];found=False;deadline=min(budget,time.perf_counter()+.004) if budget is not None else None
 while frontier and job['visits']<12000:
  if deadline is not None and job['visits']%8==0 and time.perf_counter()>=deadline:return []
  _,node=heapq.heappop(frontier);job['visits']+=1
  if node==goal:found=True;break
  x,y=center(node)
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   nxt=(node[0]+dx,node[1]+dy)
   if not allowed(nxt):continue
   nx,ny=center(nxt)
   if cliff_at(r,(x+nx)/2,(y+ny)/2) or (not amphibious and not passable_water(r,e,(x+nx)/2,(y+ny)/2)):continue
   if dx and dy and cliff_at(r,x+dx*NAV_CELL,y) and cliff_at(r,x,y+dy*NAV_CELL):continue
   if barrier_hit(r,{**e,'x':x,'y':y},nx,ny):continue
   amount=cost[node]+(1.4142 if dx and dy else 1)
   if amount>=cost.get(nxt,float('inf')):continue
   cost[nxt]=amount;previous[nxt]=node;heuristic=math.hypot(goal[0]-nxt[0],goal[1]-nxt[1]);heapq.heappush(frontier,(amount+heuristic,nxt))
 e.pop('_nav_job',None)
 if not found:path=[]
 else:
  nodes=[];node=goal
  while node!=start:nodes.append(node);node=previous[node]
  nodes.reverse();path=[];last=start;old_direction=None
  for node in nodes:
   direction=(node[0]-last[0],node[1]-last[1])
   if old_direction is not None and direction!=old_direction:path.append(center(last))
   last=node;old_direction=direction
  if nodes:path.append(center(nodes[-1]))
  path.append(tuple(destination))
 cache[key]=list(path)
 if len(cache)>96:cache.pop(next(iter(cache)))
 return path

def navigation_destination(r,e,destination):
 if e['kind'] in ['fighter','bomber']:return destination
 key=(round(destination[0]/50),round(destination[1]/50));route=e.get('_route',[])
 if key!=e.get('_route_key'):route=[]
 while route and math.hypot(e['x']-route[0][0],e['y']-route[0][1])<12:route.pop(0)
 if route:
  target=route[0]
  if ground_line_clear(r,e,e['x'],e['y'],*target):e['_route']=route;return target
  route=[]
 dx=destination[0]-e['x'];dy=destination[1]-e['y'];d=max(1,math.hypot(dx,dy));step=min(100,d);probe=(e['x']+dx/d*step,e['y']+dy/d*step)
 if ground_line_clear(r,e,e['x'],e['y'],*probe):e['_route']=[];e.pop('_nav_job',None);return destination
 if r['elapsed']+1e-8<e.get('_route_retry',-1) and not e.get('_nav_job'):return destination
 route=navigation_path(r,e,destination);e['_route']=route;e['_route_key']=key
 # A frame budget yield is not a failed search. Retry next frame instead of
 # imposing the unreachable-destination cooldown on a unit that never searched.
 yielded=not route and (e.get('_nav_job') or time.perf_counter()>=r.get('_navigation_deadline',float('inf')))
 e['_route_retry']=r['elapsed']+(0 if yielded else 2)
 return route[0] if route else destination
DIFFICULTIES={'easy':dict(label='Easy',decision=40,raid_after=360,raid_size=4,raid_interval=180,harvest=.8),'normal':dict(label='Normal',decision=20,raid_after=300,raid_size=6,raid_interval=150,harvest=1),'hard':dict(label='Hard',decision=15,raid_after=240,raid_size=8,raid_interval=120,harvest=1.15),'brutal':dict(label='Brutal',decision=10,raid_after=180,raid_size=10,raid_interval=90,harvest=1.3)}
ROOMS={}; LOCK=threading.RLock()
SESSIONS={}
def guest(username):
 username=str(username).strip();key=username.casefold()
 assert re.fullmatch(r'[A-Za-z0-9_]{1,20}',username),'Use 1–20 letters, numbers, or underscores'
 assert not any(u['username']==key and u['expires']>time.time() for u in SESSIONS.values()),'That username is in use. Choose another name.'
 token=secrets.token_hex(32);SESSIONS[token]=dict(username=key,display=username,expires=time.time()+86400)
 return dict(account=token,username=username)
def account(token):
 a=SESSIONS.get(token)
 assert a and a['expires']>time.time(),'Choose a username to continue'
 return a
STATS={'warehouse':(900,0,0,300),'dock':(800,0,0,350),'wall':(450,0,0,50),'gate':(650,0,0,100),'hacker':(90,74,0,220),'engineer':(110,68,0,140),'core':(1600,0,0,0),'power':(450,0,0,250),'factory':(650,0,0,400),'turret':(500,0,150,300),'harvester':(240,65,0,200),'tank':(400,55,115,250),'walker':(270,80,145,230),'scout':(140,115,90,130),'infantry':(100,72,110,80),'lancer':(300,46,240,340),'solar':(350,0,0,300),'airfield':(900,0,0,500),'fighter':(220,160,200,300),'bomber':(380,110,220,420),'grenadier':(120,65,145,110),'barracks':(600,0,0,250),'academy':(650,0,0,350),'marksman':(85,65,230,150),'medic':(110,72,0,120),'jeep':(200,140,110,180)}
MATERIAL_COSTS={'warehouse':(20,0,25),'dock':(20,5,30),'wall':(5,0,2),'gate':(12,0,5),'hacker':(4,8,2),'engineer':(5,0,3),'jeep':(8,0,0),'barracks':(15,0,15),'academy':(20,10,15),'marksman':(5,3,0),'medic':(3,3,0),'grenadier':(4,2,0),'solar':(15,0,10),'airfield':(30,15,20),'fighter':(15,10,0),'bomber':(22,18,0),'core':(40,15,25),'power':(10,5,12),'factory':(25,10,20),'turret':(15,8,8),'harvester':(8,0,5),'tank':(12,5,0),'walker':(10,8,0),'scout':(5,0,0),'infantry':(2,0,0),'lancer':(18,12,0)}


STATS.update({'knight':(210,98,48,200),'transport':(300,65,0,240),'gunboat':(350,75,170,330)})
MATERIAL_COSTS.update({'knight':(12,0,8),'transport':(14,0,20),'gunboat':(25,8,15)})
# Match-local technology progression. Costs and gates are authoritative on the server.
TECHS={
 'industry':dict(name='Industry',requires=[],facility='power',credits=200,metal=20,wood=10,riftglass=5,seconds=30,gathered=8),
 'fieldcraft':dict(name='Field Operations',requires=[],facility='barracks',credits=180,metal=15,wood=15,riftglass=10,seconds=30,gathered=8),
 'armor':dict(name='Armored Warfare',requires=['industry'],facility='factory',credits=300,metal=40,wood=10,riftglass=20,seconds=45,gathered=24),
 'aviation':dict(name='Aviation',requires=['armor','fieldcraft'],facility='academy',credits=450,metal=60,wood=20,riftglass=35,seconds=60,gathered=48),
 'stormtech':dict(name='Storm Technology',requires=['aviation'],facility='airfield',credits=550,metal=80,wood=20,riftglass=50,seconds=75,gathered=72)
}
# Specialized optional upgrades supplement the five building/unit unlock branches.
TECHS.update({
 'base_expansion':dict(name='Base Expansion',category='Economy',pictures=['core'],description='Unlock additional command cores to establish new bases.',requires=['industry'],facility='academy',credits=500,metal=50,wood=40,riftglass=25,seconds=45,gathered=40),
 'logistics':dict(name='Expanded Cargo Beds',category='Economy',pictures=['harvester'],description='Increase every harvester cargo bed from 750 to 1,000.',requires=['industry'],facility='warehouse',credits=250,metal=25,wood=20,riftglass=5,seconds=35,gathered=24),
 'extraction':dict(name='Efficient Extraction',category='Economy',pictures=['mine','harvester'],description='Gather metal, wood and Riftglass 25% faster.',requires=['industry'],facility='power',credits=280,metal=30,wood=10,riftglass=15,seconds=40,gathered=32),
 'warehousing':dict(name='High Density Storage',category='Economy',pictures=['warehouse'],description='Increase warehouse storage by 25% at every level.',requires=['logistics'],facility='warehouse',credits=350,metal=35,wood=30,riftglass=10,seconds=45,gathered=48),
 'infantry_drills':dict(name='Combat March Drills',category='Infantry',pictures=['infantry','grenadier','marksman'],description='Soldiers and field medics move 15% faster.',requires=['fieldcraft'],facility='barracks',credits=220,metal=15,wood=10,riftglass=10,seconds=30,gathered=24),
 'combat_medicine':dict(name='Advanced Field Medicine',category='Infantry',pictures=['medic'],description='Medics restore 18 health per treatment instead of 12.',requires=['fieldcraft'],facility='barracks',credits=260,metal=15,wood=15,riftglass=25,seconds=40,gathered=32),
 'composite_armor':dict(name='Composite Vehicle Armor',category='Armor',pictures=['tank','lancer','jeep'],description='Ground vehicles and walkers gain 20% maximum health.',requires=['armor'],facility='factory',credits=350,metal=50,wood=5,riftglass=25,seconds=50,gathered=48),
 'stabilizers':dict(name='Autoloaders and Stabilizers',category='Armor',pictures=['tank','walker','lancer'],description='Tanks, walkers and missile lancers have 20% shorter firing cooldowns.',requires=['armor'],facility='factory',credits=380,metal=40,wood=5,riftglass=30,seconds=50,gathered=56),
 'fortifications':dict(name='Reinforced Base Defenses',category='Defenses',pictures=['wall','gate','turret'],description='Walls and gates gain 40% maximum health; other buildings gain 20%.',requires=['industry'],facility='power',credits=300,metal=40,wood=35,riftglass=10,seconds=45,gathered=40),
 'targeting':dict(name='Long Range Targeting',category='Defenses',pictures=['turret'],description='Defense turrets gain 25% attack range.',requires=['armor'],facility='factory',credits=320,metal=25,wood=10,riftglass=35,seconds=45,gathered=48),
 'field_engineering':dict(name='Heavy Repair Equipment',category='Engineering',pictures=['engineer','dock'],description='Engineers repair buildings, rebuild bridges and reclaim abandoned facilities 50% faster.',requires=['fieldcraft','industry'],facility='academy',credits=280,metal=25,wood=30,riftglass=10,seconds=40,gathered=32),
 'aviation_engines':dict(name='High Thrust Engines',category='Air power',pictures=['fighter','bomber'],description='Interceptors and bombers fly 20% faster.',requires=['aviation'],facility='airfield',credits=380,metal=35,wood=10,riftglass=40,seconds=55,gathered=64),
 'electronic_warfare':dict(name='Accelerated Intrusion',category='Advanced',pictures=['hacker'],description='Combat hackers capture enemy units in 9 seconds instead of 12.',requires=['stormtech'],facility='academy',credits=400,metal=20,wood=10,riftglass=55,seconds=60,gathered=80)
})
for key,category,pictures,description in [
 ('industry','Economy',['factory','dock','jeep'],'Unlock factories, docks, solar power, jeeps, scouts and gates.'),
 ('fieldcraft','Infantry',['engineer','medic','marksman'],'Unlock engineers, medics, grenadiers and marksmen.'),
 ('armor','Armor',['tank','turret','lancer'],'Unlock tanks, walkers, defense turrets and missile lancers.'),
 ('aviation','Air power',['airfield','fighter'],'Unlock airfields and interceptors.'),
 ('stormtech','Advanced',['hacker','bomber'],'Unlock combat hackers and storm bombers.')]:TECHS[key].update(category=category,pictures=pictures,description=description)
WAREHOUSE_CAPACITIES={1:5000,2:8000,3:12000,4:18000,5:25000}
TECHS.update({
 'stone_tools':dict(name='Knapped Gathering Tools',historical_only=True,category='Economy',pictures=['harvester'],description='Gather all materials 10% faster.',requires=[],facility='core',credits=0,metal=0,wood=50,stone=40,riftglass=0,seconds=25,gathered=0),
 'basic_drills':dict(name='Basic Footwork',historical_only=True,category='Infantry',pictures=['infantry'],description='Foot soldiers and field medics move 5% faster.',requires=[],facility='barracks',credits=0,metal=0,wood=40,food=40,riftglass=0,seconds=25,gathered=0),
 'infantry_weapons':dict(name='Infantry Weapons',category='Infantry',pictures=['infantry','marksman'],description='Infantry, archers and marksmen deal 15% more damage.',requires=['fieldcraft'],facility='barracks',credits=300,metal=40,wood=30,riftglass=15,seconds=40,gathered=100),
 'field_armor':dict(name='Infantry Protection',category='Infantry',pictures=['infantry','medic'],description='Foot soldiers and specialists gain 15% maximum health.',requires=['fieldcraft'],facility='barracks',credits=300,metal=35,wood=25,riftglass=10,seconds=40,gathered=100),
 'cavalry_training':dict(name='Cavalry Training',category='Cavalry',pictures=['knight'],description='Knights move 15% faster and deal 20% more damage.',requires=['fieldcraft'],facility='barracks',credits=400,metal=45,wood=35,riftglass=20,seconds=50,gathered=160),
 'naval_hulls':dict(name='Reinforced Hulls',category='Naval',pictures=['transport','gunboat'],description='Transports and warships gain 25% maximum health.',requires=['fieldcraft'],facility='dock',credits=400,metal=60,wood=90,riftglass=15,seconds=50,gathered=160),
 'naval_engines':dict(name='Improved Marine Propulsion',category='Naval',pictures=['transport','gunboat'],description='Transports and warships sail 20% faster.',requires=['naval_hulls'],facility='dock',credits=450,metal=70,wood=50,riftglass=20,seconds=55,gathered=220),
 'vehicle_weapons':dict(name='Armor Piercing Munitions',category='Armor',pictures=['tank','walker','lancer'],description='Armed ground vehicles deal 15% more damage.',requires=['armor'],facility='factory',credits=500,metal=100,wood=20,riftglass=40,seconds=60,gathered=280),
 'air_munitions':dict(name='Precision Air Munitions',category='Air power',pictures=['fighter','bomber'],description='Interceptors and bombers deal 15% more damage.',requires=['aviation'],facility='airfield',credits=550,metal=110,wood=20,riftglass=50,seconds=65,gathered=320)
})
GROUND_VEHICLES=['harvester','tank','walker','jeep','scout','lancer']
for level in range(2,6):
 TECHS['storage_'+str(level)]=dict(name='Warehouse Expansion '+str(level),category='Economy',pictures=['warehouse'],description=f'Expand all current and future warehouses to level {level}: {WAREHOUSE_CAPACITIES[level]:,} storage per material.',requires=['industry'] if level==2 else ['storage_'+str(level-1)],facility='warehouse',credits=500*(level-1),metal=50*(level-1),wood=40*(level-1),riftglass=10*(level-1),seconds=30+level*10,gathered=24*(level-1))
for tech in TECHS.values():
 tech['metal']+=math.ceil(tech.pop('credits')/10)
def warehouse_level(p):return max([1]+[level for level in range(2,6) if 'storage_'+str(level) in p.get('tech',[])])
def harvester_capacity(p):return 1000 if 'logistics' in p.get('tech',[]) else HARVESTER_CAPACITY
TECHS['engineering_basics']=dict(name='Engineering Basics',category='Engineering',pictures=['engineer'],description='Unlock Stone Age craftsman engineers. Repair buildings automatically and rebuild bridges.',requires=['stone_tools'],facility='academy',metal=0,wood=60,food=40,stone=50,riftglass=0,seconds=30,gathered=50,historical_only=True)
for kind,ran in dict(infantry=180,marksman=290,grenadier=200,jeep=175,scout=160,tank=190,walker=215,lancer=300,fighter=260,bomber=280,gunboat=240,turret=300).items():
 h,speed,old,cost=STATS[kind];STATS[kind]=(h,speed,ran,cost)

def upgraded_hp(p,kind,hp):
 tech=p.get('tech',[])
 if kind in ['infantry','grenadier','marksman','medic','engineer','hacker'] and 'field_armor' in tech:hp*=1.15
 if kind in ['transport','gunboat'] and 'naval_hulls' in tech:hp*=1.25
 if kind in GROUND_VEHICLES and 'composite_armor' in tech:hp*=1.2
 if kind in FOOTPRINTS and 'fortifications' in tech:hp*=1.4 if kind in ['wall','gate'] else 1.2
 return round(hp)
def weapon_damage(p,e,base):
 tech=p.get('tech',[]);kind=e['kind']
 bonus=.2 if kind=='knight' and 'cavalry_training' in tech else .15 if (kind in ['infantry','grenadier','marksman'] and 'infantry_weapons' in tech or kind in GROUND_VEHICLES and 'vehicle_weapons' in tech or kind in ['fighter','bomber'] and 'air_munitions' in tech) else 0
 return base*(1+bonus)
def apply_research_upgrades(r,p):
 for e in r['entities']:
  if e['owner']!=p['id'] or e['hp']<=0:continue
  maximum=upgraded_hp(p,e['kind'],STATS[e['kind']][0]);ratio=e['hp']/max(1,e['maxhp']);e['maxhp']=maximum;e['hp']=min(maximum,maximum*ratio)
  if e['kind']=='harvester':e['cargo_capacity']=harvester_capacity(p)
  if e['kind']=='warehouse':e['storage_level']=warehouse_level(p)
UNLOCKS={'knight':'fieldcraft','transport':'industry','gunboat':'industry','dock':'industry','gate':'industry','hacker':'stormtech','engineer':'fieldcraft','factory':'industry','solar':'industry','core':'base_expansion','scout':'industry','jeep':'industry','medic':'fieldcraft','grenadier':'fieldcraft','marksman':'fieldcraft','tank':'armor','walker':'armor','turret':'armor','lancer':'armor','airfield':'aviation','fighter':'aviation','bomber':'stormtech'}
def unlock_reason(p,kind):
 if kind=='knight' and not p.get('historical_shared'):return 'Available in Continental era mode'
 if p.get('historical_shared'):
  reason=era_rules.kind_era_reason(p['historical'],kind)
  if reason:return reason
  if kind in era_rules.ERA_ONLY_KINDS:return None
 required='engineering_basics' if kind=='engineer' and p.get('historical_shared') else UNLOCKS.get(kind)
 return 'Research '+TECHS[required]['name']+' to unlock '+kind if required and required not in p.get('tech',[]) else None
def unlocked(p,kind):return unlock_reason(p,kind) is None

def tech_for(p,key):
 tech={**TECHS[key]}
 if p.get('historical_shared'):
  tech.update(era_rules.TECH_OVERRIDES.get(key,{}));tech['minimum_era']=era_rules.TECH_ERAS.get(key,'future')
  if key=='industry':tech['description']='Unlock factories, military jeeps and scouts. Early docks, transports and gates are opened by their eras.'
  if key=='fieldcraft':tech['description']='Unlock medics and archers. Engineers use Engineering Basics in the Stone Age.'
 tech['costs']=commander_costs(p,{resource:tech[resource] for resource in ['metal','wood','riftglass','food','stone'] if tech.get(resource,0)})
 return tech

def under_construction(e):return bool(e.get('construction') and e['construction']['progress']<e['construction']['seconds'])
def begin_construction(e):
 seconds=3 if e['kind'] in ['wall','gate'] else 8 if e['kind'] in ['solar','turret'] else 12
 e['construction']=dict(progress=0,seconds=seconds)
def research_facility(r,p,kind):return any(e['owner']==p['id'] and e['kind']==kind and e['hp']>0 and not e.get('packed') and not under_construction(e) for e in r['entities'])
def research_reason(r,p,key):
 tech=tech_for(p,key)
 if tech.get('historical_only') and not p.get('historical_shared'):return 'Available in Continental era mode'
 if p.get('historical_shared'):
  reason=era_rules.tech_era_reason(p['historical'],key)
  if reason:return reason
 missing=[TECHS[k]['name'] for k in tech['requires'] if k not in p.get('tech',[])]
 if missing:return 'Complete '+', '.join(missing)+' first'
 if sum(p.get('gathered',{}).values())+1e-7<tech['gathered']:return 'Deliver '+str(tech['gathered'])+' gathered materials in total (starting supplies do not count)'
 if not research_facility(r,p,tech['facility']):return 'Requires a deployed '+tech['facility']
 if not research_facility(r,p,'academy'):return 'Build an academy to conduct research'
 if p.get('power',20)<0:return 'Restore power to begin research'
 bank=p['historical']['resources'] if p.get('historical_shared') else p
 for resource,cost in tech['costs'].items():
  if bank.get(resource,0)<cost:return 'Need '+str(cost)+' '+resource
 return None
def tick_research(r,p,dt):
 job=p.get('research')
 if not job or not p['alive']:return
 tech=tech_for(p,job['key'])
 job['paused']=('Rebuild the academy' if not research_facility(r,p,'academy') else 'Rebuild or deploy the '+tech['facility'] if not research_facility(r,p,tech['facility']) else 'Restore power' if p.get('power',20)<0 else None)
 if job['paused']:return
 job['progress']=min(tech['seconds'],job['progress']+dt)
 if job['progress']+1e-7>=tech['seconds']:
  p.setdefault('tech',[]).append(job['key']);apply_research_upgrades(r,p);p['research']=None;p['research_notice']=tech['name']+' complete — new technology unlocked'

FOOTPRINTS={'warehouse':(70,60),'dock':(60,50),'wall':(30,10),'gate':(30,10),'core':(60,60),'power':(60,60),'factory':(60,60),'turret':(40,40),'solar':(50,50),'airfield':(80,60),'barracks':(60,50),'academy':(60,60)}
def unload_anchor(building,harvester):
 w,h=FOOTPRINTS[building['kind']]
 if abs(math.sin(building.get('facing',0)))>.7:w,h=h,w
 dx=harvester['x']-building['x'];dy=harvester['y']-building['y']
 margin=max(grid_occupancy.dimensions(harvester,FOOTPRINTS))/2+4
 if abs(dx)<=w+margin+8 and abs(dy)<=h+margin+8 and (abs(dx)>=w+margin-8 or abs(dy)>=h+margin-8):return dict(x=harvester['x'],y=harvester['y'])
 if abs(dx)/w>=abs(dy)/h:return dict(x=building['x']+math.copysign(w+margin,dx),y=building['y']+max(-h,min(h,dy)))
 return dict(x=building['x']+max(-w,min(w,dx)),y=building['y']+math.copysign(h+margin,dy))
def storage_grid_anchor(r,building,harvester):
 index=r.get('_occupancy') or make_occupancy(r);w,h=FOOTPRINTS[building['kind']]
 if abs(math.sin(building.get('facing',0)))>.7:w,h=h,w
 reach=max(grid_occupancy.dimensions(harvester,FOOTPRINTS))/2+GRID_SIZE
 candidates=[]
 for side in [-1,1]:
  for along in [-1,0,1]:
   for x,y in [(building['x']+side*(w+reach),building['y']+along*h),(building['x']+along*w,building['y']+side*(h+reach))]:
    x,y=grid_occupancy.snap(harvester,x,y,FOOTPRINTS)
    if index.allowed(harvester,x,y):candidates.append(dict(x=x,y=y))
 return min(candidates,key=lambda spot:dist(harvester,spot)) if candidates else unload_anchor(building,harvester)

def storage_capacity(r,p):
 return 1500+sum(round(WAREHOUSE_CAPACITIES[warehouse_level(p)]*(1.25 if 'warehousing' in p.get('tech',[]) else 1)) for e in r['entities'] if e['owner']==p['id'] and e['kind']=='warehouse' and e['hp']>0 and not e.get('packed') and not under_construction(e))

UNLIMITED_BUILDINGS={'solar','power','turret','wall','gate'}
def building_limit_reason(r,p,kind,exclude_site=None):
 if kind in UNLIMITED_BUILDINGS or kind=='core' and 'base_expansion' in p.get('tech',[]):return None
 if any(e['owner']==p['id'] and e['kind']==kind and e['hp']>0 for e in r['entities']):return 'Only one '+kind+' is allowed per commander'
 if any(site.get('id')!=exclude_site and site.get('hp',0)>0 and site.get('building_kind')==kind and (site.get('rebuild') or {}).get('owner')==p['id'] for site in r.get('props',[])+r.get('wrecks',[])):return 'Already rebuilding a '+kind
 return None

def snap_building(kind,x,y,angle=0):
 w,h=FOOTPRINTS[kind]
 if abs(math.sin(angle))>.7:w,h=h,w
 ox=w%GRID_SIZE;oy=h%GRID_SIZE
 return math.floor((x-ox)/GRID_SIZE+.5)*GRID_SIZE+ox,math.floor((y-oy)/GRID_SIZE+.5)*GRID_SIZE+oy

def grid_terrain(r,e,x,y):
 if e['kind'] in ['fighter','bomber']:return True
 # Corners reserve the complete contact area, not just the sprite centre.
 w,h=grid_occupancy.dimensions(e,FOOTPRINTS)
 rx=min(w/2-2,32) if e['kind'] not in NAVAL else w/2-2;ry=min(h/2-2,32) if e['kind'] not in NAVAL else h/2-2
 return all(not cliff_at(r,px,py) and passable_water(r,e,px,py) for px,py in [(x,y),(x-rx,y-ry),(x+rx,y-ry),(x-rx,y+ry),(x+rx,y+ry)])
def make_occupancy(r):
 return grid_occupancy.Occupancy(r,FOOTPRINTS,lambda e,x,y:grid_terrain(r,e,x,y),lambda e,g:g.get('gate_mode','auto')=='open' or g.get('gate_mode','auto')=='auto' and ally(r,e['owner'],g['owner']),WORLD_W,WORLD_H,GRID_SIZE)
def footprint_destination(r,e,destination):
 index=r.get('_occupancy') or make_occupancy(r)
 destination=list(grid_occupancy.snap(e,*destination,FOOTPRINTS))
 if not index.allowed(e,*destination,static_only=True):
  slot=index.nearest(e,*destination,rings=18,static_only=True)
  if slot:return list(slot)
 return destination

def clear_footprint(r,kind,x,y,ignore=None,angle=0,ignore_units=False):
 w,h=FOOTPRINTS[kind]
 if abs(math.sin(angle))>.7:w,h=h,w
 restoring=any(o.get('id')==ignore and o.get('kind') in ['abandoned','wreck'] for o in r.get('props',[])+r.get('wrecks',[])) if ignore else False
 if bridge_lane(r,x,y,max(w,h)) or roadside_lane(r,x,y,max(w,h)):return False
 for mine in r.get('nodes',[]):
  if mine.get('site')!='mine' or mine.get('stock',0)<=0:continue
  if abs(x-mine['x'])<w+90 and abs(y-mine['y'])<h+75:return False
  if any(abs(x-spot['x'])<w+50 and abs(y-spot['y'])<h+40 for spot in mine.get('parking_spots',[])):return False
 for node in r.get('nodes',[]):
  if restoring:break
  if node.get('site')=='mine' or node.get('stock',1)<=0 or node.get('hp',1)<=0:continue
  radius=max(20,min(60,node.get('size',35)))
  if abs(x-node['x'])<w+radius-.01 and abs(y-node['y'])<h+radius-.01:return False
 for obj in r.get('props',[]):
  if restoring:break
  if obj.get('kind') not in ['tree','rock','ruin','wood','abandoned_car','road_business'] or obj.get('hp',0)<=0 or obj.get('stock',1)<=0:continue
  radius=max(20,min(60,obj.get('size',35)))
  if abs(x-obj['x'])<w+radius-.01 and abs(y-obj['y'])<h+radius-.01:return False
 if not ignore_units and not restoring:
  for unit in r['entities']:
   if unit['id']==ignore or unit['hp']<=0 or unit.get('embarked') or unit['kind'] in FOOTPRINTS and not unit.get('packed'):continue
   uw,uh=grid_occupancy.dimensions(unit,FOOTPRINTS)
   left=math.floor((unit['x']-uw/2)/GRID_SIZE)*GRID_SIZE;right=math.ceil((unit['x']+uw/2-.001)/GRID_SIZE)*GRID_SIZE
   top=math.floor((unit['y']-uh/2)/GRID_SIZE)*GRID_SIZE;bottom=math.ceil((unit['y']+uh/2-.001)/GRID_SIZE)*GRID_SIZE
   if x-w<right-.01 and x+w>left+.01 and y-h<bottom-.01 and y+h>top+.01:return False
 if any(cliff_at(r,x+ox,y+oy) for ox,oy in [(0,0),(-w,-h),(w,-h),(-w,h),(w,h)]) or any(x-w<px<x+w and y-h<py<y+h for c in r.get('cliffs',CLIFFS) for px,py in c['points']):return False
 if x-w<10 or x+w>WORLD_W-10 or y-h<10 or y+h>WORLD_H-10:return False
 for other in r['entities']+r.get('props',[])+r.get('wrecks',[]):
  other_kind=other.get('building_kind') if other['kind'] in ['abandoned','wreck'] else other['kind']
  if other['id']==ignore or other['hp']<=0 or other_kind not in FOOTPRINTS or other.get('packed'):continue
  ow,oh=FOOTPRINTS[other_kind]
  if abs(math.sin(other.get('facing',other.get('angle',0) if other_kind in ['wall','gate'] else 0)))>.7:ow,oh=oh,ow
  gap=0
  if abs(x-other['x'])<w+ow+gap-.01 and abs(y-other['y'])<h+oh+gap-.01:return False
 return True


def snap_wall(r,p,x,y,angle,ignore=None):
 candidates=[];vertical=abs(math.sin(angle))>.7
 for wall in r['entities']:
  if wall['id']==ignore or wall['kind'] not in ['wall','gate'] or wall['hp']<=0 or not ally(r,p['id'],wall['owner']):continue
  if (abs(math.sin(wall.get('angle',0)))>.7)!=vertical:continue
  step=WALL_SPAN
  for side in [-1,1]:
   px=wall['x'] if vertical else wall['x']+side*step;py=wall['y']+side*step if vertical else wall['y'];distance=math.hypot(x-px,y-py)
   if distance<26:candidates.append((distance,px,py))
 return min(candidates)[1:] if candidates else (x,y)
def connected_gates(r,gate):
 index=r.get('_barrier_index')
 if index is None:index=barrier_index.BarrierIndex(r['entities']);r['_barrier_index']=index
 found=[gate];seen={gate['id']};i=0
 while i<len(found):
  current=found[i];i+=1;vertical=abs(math.sin(current.get('angle',0)))>.7
  for other in index.nearby(current['x']-65,current['y']-65,current['x']+65,current['y']+65):
   if other['id'] in seen or other['kind']!='gate' or other['owner']!=gate['owner'] or other['hp']<=0 or (abs(math.sin(other.get('angle',0)))>.7)!=vertical:continue
   dx=abs(other['x']-current['x']);dy=abs(other['y']-current['y'])
   if (abs(dy-WALL_SPAN)<2 and dx<2) if vertical else (abs(dx-WALL_SPAN)<2 and dy<2):seen.add(other['id']);found.append(other)
 return found

def barrier_hit(r,e,nx,ny):
 index=r.get('_barrier_index')
 if index is None:index=barrier_index.BarrierIndex(r['entities']);r['_barrier_index']=index
 for wall in index.nearby(e['x'],e['y'],nx,ny):
  if wall['kind'] not in ['wall','gate'] or wall['hp']<=0:continue
  if wall['kind']=='gate' and (wall.get('gate_mode','auto')=='open' or wall.get('gate_mode','auto')=='auto' and ally(r,e['owner'],wall['owner'])):continue
  w,h=FOOTPRINTS[wall['kind']]
  if abs(math.sin(wall.get('angle',0)))>.7:w,h=h,w
  if wall['id'] in index.corners:w=h=30
  radius=4 if e['kind'] in ['infantry','grenadier','marksman','medic','engineer','hacker'] else 9;w+=radius;h+=radius
  lo,hi=0,1
  for start,delta,center,extent in [(e['x'],nx-e['x'],wall['x'],w),(e['y'],ny-e['y'],wall['y'],h)]:
   if abs(delta)<1e-8:
    if abs(start-center)>extent:lo=2;break
   else:
    a,b=(center-extent-start)/delta,(center+extent-start)/delta;lo=max(lo,min(a,b));hi=min(hi,max(a,b))
  if lo<=hi and hi>=0 and lo<=1:return wall
 return None

HISTORICAL_COSTS={
 'warehouse':dict(wood=120,stone=60),'barracks':dict(wood=100,stone=80),'academy':dict(wood=140,stone=120),
 'wall':dict(stone=15,wood=5),'gate':dict(stone=35,wood=35),'core':dict(wood=500,stone=400,iron=150),
 'harvester':dict(food=60,wood=40),'infantry':dict(food=40,wood=20),'marksman':dict(food=50,wood=45,gold=10),
 'engineer':dict(food=60,wood=35,iron=20),'medic':dict(food=70,gold=30),'knight':dict(food=100,iron=60,gold=40),
 'dock':dict(wood=180,stone=100),'transport':dict(wood=140,iron=30),'gunboat':dict(wood=200,iron=100,gold=40),
 'turret':dict(stone=100,wood=80,iron=40),'power':dict(iron=240,stone=140),'factory':dict(iron=320,stone=200,wood=120),
 'solar':dict(iron=200,riftglass=80),'airfield':dict(iron=400,stone=250,wood=120),
 'jeep':dict(iron=100,gold=20),'scout':dict(iron=90,gold=20),'tank':dict(iron=220,gold=50),
 'walker':dict(iron=200,riftglass=60),'lancer':dict(iron=240,riftglass=80),'grenadier':dict(food=60,iron=45,gold=15),
 'fighter':dict(iron=260,gold=80),'bomber':dict(iron=360,riftglass=120),'hacker':dict(food=70,iron=50,riftglass=90)}
def material_costs(k,p=None):
 if p and p.get('historical_shared'):return era_rules.equipment_costs(k,p['historical']['era'],HISTORICAL_COSTS)
 metal,glass,wood=MATERIAL_COSTS[k];return {'metal':metal+math.ceil((600 if k=='core' else STATS[k][3])/10),'riftglass':glass,'wood':wood}
def commander_costs(p,costs):
 if not p.get('historical_shared'):return dict(costs)
 names={'metal':'iron','riftglass':'riftglass' if p['historical']['era']=='future' else 'gold'}
 result={}
 for resource,cost in costs.items():
  if cost:key=names.get(resource,resource);result[key]=result.get(key,0)+cost
 return result
def pay_costs(p,costs):
 costs=commander_costs(p,costs);bank=p['historical']['resources'] if p.get('historical_shared') else p
 for resource,cost in costs.items():assert bank.get(resource,0)>=cost,'Not enough '+resource+' — assign a harvester'
 for resource,cost in costs.items():bank[resource]-=cost
 if p.get('historical_shared'):sync_historical_bank(p,to_history=False)
def pay_materials(p,k):pay_costs(p,material_costs(k,p))
UNIT_COMBAT_DAMAGE_FACTOR=.6
def damage_target(r,target,amount,source=None):
 # Longer unit engagements; structures and bridge demolition retain their damage.
 amount*=UNIT_COMBAT_DAMAGE_FACTOR if target['kind'] in STATS and target['kind'] not in FOOTPRINTS else 1
 target['hp']-=amount;target['last_hit_at']=r['elapsed'];target['last_hit_damage']=amount
 if source:target['hit_angle']=math.atan2(target['y']-source['y'],target['x']-source['x'])
 return amount
def effective_attack_range(p,e):
 if e.get('packed') or under_construction(e):return 0
 ran=e.get('attack_range',STATS[e['kind']][2])
 return ran*1.25 if e['kind']=='turret' and 'targeting' in p.get('tech',[]) else ran

def target_extent(e):
 # Combat scenery (fires, craters and effects) has coordinates but no unit kind.
 kind=e.get('kind')
 return e.get('span',480)/2 if kind=='bridge' else max(FOOTPRINTS[kind]) if kind in FOOTPRINTS else 0
def acquisition_range(p,e):
 ran=effective_attack_range(p,e)
 return 0 if not ran else ran if e['kind'] in FOOTPRINTS else max(ran+100,340 if e['kind'] in ['knight','tank','walker','jeep','scout','lancer','gunboat'] else 300)
def sight_range(p,e):return max(280,acquisition_range(p,e)+30)
def can_engage(e,t):
 return t['hp']>0 and not t.get('embarked') and (t['kind'] not in ['fighter','bomber'] or e['kind'] in ['fighter','lancer','turret']) and not (e['kind']=='bomber' and t['kind'] in ['fighter','bomber'])
def combat_priority(e,t):
 return dist(e,t)-target_extent(t)+(260 if t['kind']=='core' else 180 if t['kind'] in FOOTPRINTS else 0 if STATS.get(t['kind'],(0,0,0,0))[2] else 90)
ENGINEER_REPAIR_REACH=90
def engineer_repair_coverage(p):return 4*effective_attack_range(p,dict(kind='turret'))
def engineer_summary(r,p):
 engineers=[e for e in r['entities'] if e['kind']=='engineer' and e['owner']==p['id'] and e['hp']>0 and not e.get('embarked')]
 available=[e['id'] for e in engineers if not any(e.get(k) for k in ['moving','goal','repairing','rebuilding','reclaim_target','board_target','hack_target']) and (not e.get('repair_target') or e.get('repair_notice','').startswith('Need '))]
 return dict(total=len(engineers),available=len(available),available_ids=available)
def assign_auto_repair(r,p,e):
 if any(e.get(k) for k in ['goal','repair_target','reclaim_target','board_target','hack_target']):return
 if r['elapsed']<e.get('_repair_scan',0):return
 e['_repair_scan']=r['elapsed']+.5
 origin=e.setdefault('_repair_origin',dict(x=e['x'],y=e['y']))
 candidates=[b for b in r['entities'] if b['kind'] in FOOTPRINTS and ally(r,p['id'],b['owner']) and 0<b['hp']<b['maxhp'] and not b.get('packed') and not under_construction(b) and dist(origin,b)<=engineer_repair_coverage(p)]
 if candidates:
  b=min(candidates,key=lambda b:(b['hp']/b['maxhp'],dist(e,b)));e.update(repair_target=b['id'],auto_repair=True)
def spawn_future_riftglass(r):
 if r.get('_map_geometry')!='continental' or r.get('_future_riftglass') or not any(p.get('historical',{}).get('era')=='future' for p in r['players']):return
 r['_future_riftglass']=True
 for i,y in enumerate([3000,6600]):r['nodes'].append(dict(id='future-reserve-'+str(i),kind='riftglass',x=7200,y=y,hp=500,maxhp=500,stock=40000,max_stock=40000,owner=None,finite=True,region='future'))

def upgrade_buildings_for_era(r,p):
 if not p.get('historical_shared'):return
 era=p['historical']['era']
 for e in r['entities']:
  if e['owner']!=p['id'] or e['hp']<=0 or e['kind'] not in FOOTPRINTS:continue
  old=e.get('era_created',era);e.setdefault('original_era',old)
  if era_rules.index_for(old)>=era_rules.index_for(era):continue
  e['era_created']=era;e['upgraded_at']=r['elapsed']
  if e['kind']=='turret':
   if era_rules.index_for(era)<era_rules.index_for('industrial'):e['historical_role']='ballista_tower'
   else:e.pop('historical_role',None)

def update_worker_activity(r):
 for e in r['entities']:
  if e['kind']!='harvester':continue
  status='aboard' if e.get('embarked') else 'storage_full' if e.get('storage_blocked') else 'gathering' if e.get('harvesting') else 'travelling' if e.get('moving') or e.get('goal') or e.get('board_target') else 'idle'
  e['worker_status']=status
  if status in ['idle','storage_full']:
   if e.get('idle_since') is None:e['idle_since']=r['elapsed']
  else:e['idle_since']=None

def worker_summary(r,p):
 workers=[e for e in r['entities'] if e['owner']==p['id'] and e['kind']=='harvester' and e['hp']>0 and not e.get('embarked')]
 idle=[e['id'] for e in workers if e.get('worker_status')=='storage_full' or e.get('worker_status')=='idle' and e.get('idle_since') is not None and r.get('elapsed',0)-e['idle_since']>=1.5]
 return dict(total=len(workers),idle=len(idle),idle_ids=idle)

def effect(r,kind,x,y,**extra):
 r['effects'].append(dict(id=secrets.token_hex(5),kind=kind,x=x,y=y,born=r['elapsed'],**extra))
def terrain_height(r,x,y):
 height=9*math.sin(x*.0024)*math.cos(y*.0018)+3*math.sin((x+y)*.011)+1.4*math.sin(x*.055)*math.cos(y*.047)
 for hill in r.get('hills',HILLS):
  d=math.hypot(x-hill['x'],y-hill['y'])/hill['radius']
  if d<1:height+=hill['height']*(1-d*d)**.8
 for crater in r.get('craters',[]):
  d=math.hypot(x-crater['x'],y-crater['y']);radius=max(1,crater['size'])
  if d<radius:height-=min(18,crater.get('depth',0))*(1-(d/radius)**2)
 return height
def terrain_contact(r,e):
 angle=e.get('angle',0);x=e['x'];y=e['y'];forward=(math.cos(angle)*18,math.sin(angle)*18);side=(-math.sin(angle)*13,math.cos(angle)*13);center=terrain_height(r,x,y)
 front=terrain_height(r,x+forward[0],y+forward[1]);rear=terrain_height(r,x-forward[0],y-forward[1]);left=terrain_height(r,x+side[0],y+side[1]);right=terrain_height(r,x-side[0],y-side[1])
 bridge=any(b['kind']=='bridge' and b['hp']>0 and bridge_contains(b,x,y,2) for b in r.get('props',[]))
 if bridge:front=rear=left=right=center
 slope=(front-rear)/36;rough=abs(front+rear-2*center)+abs(left+right-2*center)
 weather=r.get('weather',{});mud=weather.get('mud',.4 if weather.get('kind')=='rain' else 0);snow=weather.get('snow',0)
 wetness=max(.6,min(1.2,.95-center*.006+.15*math.sin(x*.003)*math.cos(y*.004)));mud=min(1,mud*wetness);snow=min(1,snow*max(.85,min(1.25,.95+center*.003)))
 if road_lane(x,y,r=r):mud*=.6;snow*=.8
 if bridge:mud=0;snow*=.65
 surface='bridge' if bridge else 'water' if water_at(x,y,r=r) else 'snow' if snow>.08 else 'mud' if mud>.12 else 'dirt'
 contact=dict(height=round(center,3),pitch=round(max(-.13,min(.13,slope)),4),roll=round(max(-.1,min(.1,(left-right)/26)),4),rough=round(min(6,rough),3),surface=surface,mud=round(mud,4),snow=round(snow,4));contact['speed_factor']=round(weather_mobility(e,contact),4);return contact

def deform(r,x,y,size,depth=4):
 marks=r.setdefault('craters',[]);near=next((m for m in marks if math.hypot(m['x']-x,m['y']-y)<max(15,size*.4)),None)
 if near:near.update(size=min(110,max(near['size'],size)+3),depth=min(18,near.get('depth',0)+depth*.4))
 else:marks.append(dict(x=x,y=y,size=size,depth=depth))
 r['craters']=marks[-100:]
def ignite(r,x,y,radius=28):
 fires=r.setdefault('fires',[])
 if any(math.hypot(f['x']-x,f['y']-y)<25 for f in fires):return
 if len(fires)<24:fires.append(dict(id=secrets.token_hex(4),x=x,y=y,radius=radius,born=r['elapsed'],expires=r['elapsed']+14,spread=r['elapsed']+3))
def dist(a,b):return math.hypot(a['x']-b['x'],a['y']-b['y'])
def entity(r,p,k,x,y,*,recruitment_era=None):
 h,s,ran,c=STATS[k];h=upgraded_hp(p,k,h); e=dict(id=secrets.token_hex(5),owner=p['id'],design=p.get('design',p['faction'].lower()),kind=k,x=x,y=y,hp=h,maxhp=h,goal=None,cool=0,packed=False,cargo=0,angle=0);
 if k in ['harvester','tank','walker','jeep','scout','lancer','transport','gunboat','fighter','bomber']:e['hull_angle']=0
 if p.get('historical_shared'):
  e['era_created']=recruitment_era or p['historical']['era']
  if era_rules.index_for(e['era_created'])<era_rules.index_for('industrial'):
   if k=='infantry':e.update(historical_role='spearman',attack_range=58)
   if k=='marksman':e.update(historical_role='archer',attack_range=230)
   if k=='harvester':e['historical_role']='gatherer'
   if k=='engineer':e['historical_role']='artisan'
   if k=='medic':e['historical_role']='healer'
   if k=='transport':e['historical_role']='sailing_transport'
   if k=='gunboat':e['historical_role']='ballista_ship'
   if k=='turret':e['historical_role']='ballista_tower'
 if p.get('historical_shared') and e.get('era_created')=='industrial' and k in ['tank','walker']:e['historical_role']='industrial_armor'
 if p.get('historical_shared') and e.get('era_created')=='future' and k=='gunboat':e['historical_role']='advanced_gunboat'
 if k=='knight':e.update(historical_role='knight',attack_range=70)
 if k=='harvester':e['cargo_capacity']=harvester_capacity(p)
 if k=='warehouse':e['storage_level']=warehouse_level(p)
 if k=='medic':e['heal_range']=MEDIC_RANGE
 if k=='transport':e.update(passengers=0,capacity=TRANSPORT_CAPACITY)
 if k in FOOTPRINTS and e.get('era_created'):e['original_era']=e['era_created']
 if k not in FOOTPRINTS:
  spot=make_occupancy(r).nearest(e,x,y,rings=40)
  assert spot,'No clear grid space for this unit'
  e['x'],e['y']=spot
 e['grid_cols'],e['grid_rows']=[round(v/GRID_SIZE) for v in grid_occupancy.dimensions(e,FOOTPRINTS)]
 r['entities'].append(e);r.pop('_occupancy',None);r.pop('_barrier_index',None);return e
def player(r,pid):return next((p for p in r['players'] if p['id']==pid),None)
def ally(r,a,b):
 if a is None or b is None:return False
 return a==b or (player(r,a).get('bot') and player(r,b).get('bot')) or (r['mode']=='teams' and player(r,a)['team']==player(r,b)['team'])
class CombatIndex:
 """Tick-local broad phase; nearby combat work stays local as armies grow."""
 def __init__(self,entities,cell=320):
  self.cell=cell;self.cells={}
  for e in entities:
   if e['hp']>0 and not e.get('embarked'):self.cells.setdefault((math.floor(e['x']/cell),math.floor(e['y']/cell)),[]).append(e)
 def nearby(self,e,radius):
  c=self.cell
  for x in range(math.floor((e['x']-radius)/c),math.floor((e['x']+radius)/c)+1):
   for y in range(math.floor((e['y']-radius)/c),math.floor((e['y']+radius)/c)+1):
    yield from self.cells.get((x,y),())

def scenery():
 rng=random.Random(secrets.randbits(32));props=[]
 def add(kind,x,y,hp,size):props.append(dict(id='prop-'+secrets.token_hex(5),kind=kind,x=x,y=y,hp=hp,maxhp=hp,owner=None,size=size))
 for _ in range(1800):
  x=rng.randrange(80,WORLD_W-80);y=rng.randrange(80,WORLD_H-80)
  if abs(x-WORLD_W/2)>280 and math.sin(x*.006)+math.cos(y*.008)+math.sin((x+y)*.004)>.3 and all(math.hypot(x-bx,y-by)>180 for bx,by in [(260,260),(WORLD_W-260,WORLD_H-260),(WORLD_W-260,260),(260,WORLD_H-260)]):add('tree',x,y,60,rng.randrange(18,36))
 for _ in range(85):add('rock',rng.randrange(80,WORLD_W-80),rng.randrange(80,WORLD_H-80),180,rng.randrange(10,24))
 # Ruins are clustered at two sites; no abandoned city grid across the world.
 # Bombed-out districts and salvageable facilities, scattered per match.
 facilities=['barracks','power','factory','academy','solar','turret','airfield']
 for cx,cy,name in [(4600,3600,'CINDER CROSSING'),(10000,6100,'OLD MERIDIAN')]:
  cx+=rng.randrange(-60,61);cy+=rng.randrange(-60,61)
  for i,(ox,oy) in enumerate([(-100,0),(100,0)]):
   add('abandoned',cx+ox,cy+oy,600,65);props[-1].update(building_kind=facilities[rng.randrange(len(facilities))],district=name)
  for i in range(3):add('ruin',cx+rng.randrange(-130,131),cy+rng.randrange(-130,131),220,20)
 for i in range(2):
  for attempt in range(100):
   x=rng.randrange(650,WORLD_W-650);y=rng.randrange(350,WORLD_H-350)
   if not water_at(x,y) and not cliff_at({},x,y) and not road_lane(x,y,140) and abs(x-WORLD_W/2)>400 and all(math.hypot(x-o['x'],y-o['y'])>180 for o in props if o['kind']=='abandoned'):
    add('abandoned',x,y,600,65);props[-1].update(building_kind=rng.choice(facilities),district='FRONTIER OUTPOST');break
 # Avoid trees growing through abandoned buildings and ruined city blocks.
 sites=[o for o in props if o['kind']=='abandoned'];props=[o for o in props if o['kind']!='tree' or all(dist(o,b)>95 for b in sites)]
 for y in [2400,4800,7400]:
  index=min(range(len(RIVER_SAMPLES)),key=lambda i:abs(RIVER_SAMPLES[i][1]-y));x,by=RIVER_SAMPLES[index];prev=RIVER_SAMPLES[max(0,index-1)];nextp=RIVER_SAMPLES[min(len(RIVER_SAMPLES)-1,index+1)];angle=math.atan2(-(nextp[0]-prev[0]),nextp[1]-prev[1]);span=640
  while span<1100 and any(water_at(x+side*math.cos(angle)*span/2,by+side*math.sin(angle)*span/2) for side in [-1,1]):span+=40
  add('bridge',x,by,650,200);props[-1].update(angle=angle,span=span,deck_width=88)
 for obj in [o for o in props if o['kind']=='abandoned' and route_lane({'props':props},o['x'],o['y'],100)]:
  for _ in range(300):
   x=rng.randrange(650,WORLD_W-650);y=rng.randrange(350,WORLD_H-350)
   if not water_at(x,y) and not cliff_at({},x,y) and not route_lane({'props':props},x,y,140) and all(math.hypot(x-o['x'],y-o['y'])>250 for o in props if o['kind']=='abandoned'):
    obj.update(x=x,y=y);break
 props=[o for o in props if o['kind']=='bridge' or (not water_at(o['x'],o['y']) and not cliff_at({},o['x'],o['y']) and not route_lane({'props':props},o['x'],o['y'],max(100,o.get('size',0))) and (o['kind'] not in ['tree','rock'] or all(math.hypot(o['x']-x,o['y']-y)>=650 for x,y in START_BASES)))]
 # Small randomized roadside sites sit outside the travel lanes and bridge approaches.
 placed=[]
 for kind,count,offset in [('road_business',3,300),('abandoned_car',9,220)]:
  for i in range(count):
   for attempt in range(300):
    route=rng.choice(ROAD_ROUTES);a,b=rng.choice(list(zip(route,route[1:])));dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy);t=rng.uniform(.16,.84);side=rng.choice([-1,1]);nx,ny=-dy/length,dx/length;x=a[0]+dx*t+nx*offset*side;y=a[1]+dy*t+ny*offset*side
    if not (400<x<WORLD_W-400 and 400<y<WORLD_H-400) or water_at(x,y) or cliff_at({},x,y) or road_lane(x,y,120) or bridge_lane({'props':props},x,y,150) or any(math.hypot(x-bx,y-by)<750 for bx,by in START_BASES) or any(math.hypot(x-q['x'],y-q['y'])<180 for q in placed):continue
    if any(math.hypot(x-q['x'],y-q['y'])<170 for q in props if q['kind']=='abandoned'):continue
    if kind=='road_business' and (water_at(x-nx*side*100,y-ny*side*100) or cliff_at({},x-nx*side*100,y-ny*side*100)):continue
    add(kind,x,y,150 if kind=='abandoned_car' else 450,35 if kind=='abandoned_car' else 90);site=props[-1];site.update(variant=rng.randrange(2),angle=math.atan2(dy,dx));placed.append(site)
    if kind=='road_business':site['parking']={'x':x-nx*side*100,'y':y-ny*side*100,'angle':site['angle']}
    break
 props=[o for o in props if o in placed or o['kind'] not in ['tree','rock','ruin'] or all(math.hypot(o['x']-q['x'],o['y']-q['y'])>max(95,q['size']*1.5) for q in placed)]
 props=[o for o in props if o in placed or o['kind'] not in ['tree','rock','ruin'] or not roadside_lane({'props':props},o['x'],o['y'],35)]
 for prop in props:
  if prop['kind'] in ['tree','rock','ruin']:prop.update(resource='wood' if prop['kind']=='tree' else 'metal',stock=DEPOSIT_STOCK)
 return props

def update_weather(r,dt=0):
 elapsed=r.get('elapsed',0);setting=r.get('weather_mode','dynamic');types=['clear','rain','snow','dust'];index=max(0,int(elapsed//150))
 if setting=='dynamic':
  sequence=r.setdefault('_weather_sequence',[]);rng=r.get('_weather_rng')
  if rng is None:rng=random.Random(secrets.randbits(64));r['_weather_rng']=rng
  while len(sequence)<=index:sequence.append(rng.choice([kind for kind in types if not sequence or kind!=sequence[-1]]))
  kind=sequence[index]
 else:kind=setting
 hour=(r.get('start_hour',6)+elapsed/30)%24;sun=math.sin((hour-6)/24*math.tau);daylight=max(.08,min(1,.18+sun*1.1));phase='sunrise' if 5<=hour<8 else 'day' if 8<=hour<17 else 'sunset' if 17<=hour<20 else 'night'
 previous=r.get('weather',{});old_snow=previous.get('snow',0);mud=previous.get('mud',0)
 melt_rate=.0025 if kind=='rain' else .0014 if daylight>.55 else .00055
 snow=max(0,min(1,old_snow+dt*(.004 if kind=='snow' else -melt_rate)));melt=max(0,old_snow-snow)
 dry_rate=.0025 if kind=='dust' else .0015 if daylight>.55 else .00055
 mud=max(0,min(1,mud+dt*(.005 if kind=='rain' else -.00025 if kind=='snow' else -dry_rate)+melt*1.4))
 r['weather']=dict(kind=kind,hour=hour,phase=phase,daylight=daylight,snow=snow,mud=mud,wind=math.sin(elapsed*.006)*.8+.4,next_change=max(0,150-elapsed%150) if setting=='dynamic' else None)

def weather_mobility(e,contact):
 if e.get('kind') in ['fighter','bomber'] or contact['surface']=='water':return 1
 mud=contact.get('mud',0);snow=contact.get('snow',0)
 if contact['surface']=='bridge':return max(.85,1-snow*.18)
 design=e.get('design','bastion');kind=e.get('kind','jeep')
 if kind=='scout' and design in ['vesper','nightfall']:mud_drag,snow_drag=.08,.16
 elif kind=='walker':mud_drag,snow_drag=.18,.3
 elif kind in ['tank','lancer'] or (kind=='harvester' and design!='vesper') or kind=='scout':mud_drag,snow_drag=.22,.32
 elif kind in ['infantry','grenadier','marksman','medic','engineer','hacker']:mud_drag,snow_drag=.2,.35
 else:mud_drag,snow_drag=.45,.5
 return max(.35,1-mud*mud_drag-snow*snow_drag)

def scatter_resources(r):
 # Stratified distribution gives each broad region material sites, with natural jitter.
 rng=random.Random(secrets.randbits(32));types=['metal','wood','riftglass']
 for row in range(6):
  for col in range(8):
   kind=types[(row*8+col)%3]
   for _ in range(80):
    x=(col+.25+rng.random()*.5)*WORLD_W/8;y=(row+.25+rng.random()*.5)*WORLD_H/6
    if water_at(x,y,r=r) or cliff_at(r,x,y) or route_lane(r,x,y,120) or any(math.hypot(x-bx,y-by)<650 for bx,by in START_BASES):continue
    if any(o['kind'] in ['abandoned','bridge'] and math.hypot(x-o['x'],y-o['y'])<220 for o in r.get('props',[])):continue
    if any(math.hypot(x-n['x'],y-n['y'])<400 for n in r['nodes']):continue
    r['nodes'].append(dict(x=x,y=y,stock=deposit_stock(kind),kind=kind));break
HISTORICAL_ALIASES={'wood':'wood','iron':'metal','riftglass':'riftglass'}
def sync_historical_bank(p,to_history=True):
 if not p.get('historical_shared'):return
 bank=p['historical']['resources']
 for historical,legacy in HISTORICAL_ALIASES.items():
  if to_history:bank[historical]=p[legacy]
  else:p[legacy]=bank[historical]

def historical_gather_choice(p):
 h=p['historical'];bank=h['resources'];next_age=era_rules.next_era(h)
 if p.get('historical_shared'):
  for resource in ['wood','iron']:
   if bank[resource]<80:return resource
 for resource,amount in (next_age.costs.items() if next_age else []):
  if bank[resource]<amount:return resource
 for resource,minimum in [('food',160),('wood',220),('stone',160),('iron',300)]:
  if bank[resource]<minimum:return resource
 return 'riftglass' if h['era']=='future' and bank['riftglass']<80 else 'iron' if p.get('historical_shared') else 'stone'

def initialize_commander(r,p,slot):
 x,y=([(WORLD_W/2+900,260),(WORLD_W/2+900,WORLD_H-260)][slot%2] if p.get('bot') else [(260,260),(WORLD_W-260,WORLD_H-260),(WORLD_W-260,260),(260,WORLD_H-260)][slot%4])
 if r.get('_map_geometry')=='continental':
  occupied={q.get('map_slot') for q in r['players'] if q is not p and 'map_slot' in q};map_slot=next(i for i in range(8) if i not in occupied);p['map_slot']=map_slot;x,y=historic_map.starting_positions()[map_slot]
 p.update(spawn_slot=slot,tech=[],research=None,research_notice='',gathered={'metal':0,'wood':0,'riftglass':0},metal=190,riftglass=60,wood=80,alive=True,autopilot=bool(p.get('bot')),auto_idle=False,last_input=r.get('elapsed',0),advice='Establishing power and production. Gathering metal, Riftglass, and wood.',ai_next=r.get('elapsed',0))
 if r.get('_experimental_history'):p['historical']=era_rules.new_commander(p['faction'])
 if r.get('_map_geometry')=='continental':
  p.update(historical_shared=True,wood=200,riftglass=0);sync_historical_bank(p)
 entity(r,p,'core',*snap_building('core',x,y))
 if r.get('_map_geometry')=='continental':
  entity(r,p,'harvester',x+130,y+30)
  for j in range(3):entity(r,p,'infantry',x-32+j*32,y+105)
 else:
  entity(r,p,'harvester',x-150,y+30)
  for j in range(3):entity(r,p,'infantry',x-32+j*32,y+70)
def add_historical_deposits(r):
 """Lay out experimental finite deposits; existing map geometry remains unchanged."""
 def choose(cx,cy,seed,radii,base_slot=None):
  for radius in radii:
   for i in range(72):
    angle=(i*math.tau/72)+(seed*2.399963);x=cx+math.cos(angle)*radius;y=cy+math.sin(angle)*radius
    if not (180<x<WORLD_W-180 and 180<y<WORLD_H-180):continue
    if water_at(x,y,r=r) or cliff_at(r,x,y) or route_lane(r,x,y,120):continue
    if base_slot is not None and min(range(len(START_BASES)),key=lambda j:math.hypot(x-START_BASES[j][0],y-START_BASES[j][1]))!=base_slot:continue
    if any(math.hypot(x-n['x'],y-n['y'])<150 for n in r['nodes']):continue
    if any(o['kind'] in ['abandoned','road_business','abandoned_car'] and math.hypot(x-o['x'],y-o['y'])<180 for o in r.get('props',[])):continue
    return x,y
  raise ValueError('Unable to place an experimental historical deposit')
 def add(kind,cx,cy,seed,radii,stock,base_slot=None):
  x,y=choose(cx,cy,seed,radii,base_slot);r['nodes'].append(dict(id='historic-'+secrets.token_hex(6),kind=kind,x=x,y=y,hp=500,maxhp=500,stock=stock,max_stock=stock,owner=None,finite=True,region='starter' if base_slot is not None else 'contested',base_slot=base_slot))
  r['props']=[o for o in r.get('props',[]) if o['kind'] not in ['tree','rock','ruin'] or math.hypot(x-o['x'],y-o['y'])>120]
 for slot,(x,y) in enumerate(START_BASES):
  for i,kind in enumerate(['food','wood','stone','gold','iron']):
   add(kind,x,y,slot*5+i,[750,850,950,1050,1150,1250],5000 if kind=='food' else 10000,slot)
 for i,kind in enumerate(['gold','iron','stone','gold','iron','stone']):
  add(kind,WORLD_W/2,WORLD_H/2,i,[1000,1300,1600,1900,2200,2500],100000)

def initialize_continental_map(r):
 assert r.get('_experimental_history'),'Continental map requires historical mode'
 for p in r['players']:p.pop('map_slot',None)
 cliffs=[dict(id='ridge-'+str(i),points=list(points)) for i,points in enumerate(historic_map.MOUNTAIN_POLYGONS)]
 nodes=[]
 for i,source in enumerate(historic_map.resource_layout()):
  node=dict(source);node.update(id='continental-'+str(i),hp=500,maxhp=500,max_stock=source['stock'],owner=None,base_slot=source.get('slot'));nodes.append(node)
 r.update(phase='battle',elapsed=0,winner=None,cliffs=cliffs,hills=[],entities=[],effects=[],wrecks=[],craters=[],fires=[],projectiles=[],nodes=nodes,props=[],road_routes=historic_map.road_layout(),pending_deposits=[])
 r['props'].append(dict(id='continental-eastern-bridge',kind='bridge',x=11200,y=4800,hp=650,maxhp=650,owner=None,size=200,angle=math.pi/2,span=1100,deck_width=100))
 r['road_routes'].extend([[(11200,3000),(11200,4250)],[(11200,5350),(11200,6400)]])
 r.pop('_nav_static',None);r.pop('_shore_cache',None)
 r['map_geometry']=dict(kind='continental',coast=historic_map.COAST,sea=dict(x=7200,y=4800,rx=2300,ry=1200),channel=dict(left=7200,top=4370,bottom=5230),islands=[dict(x=i.x,y=i.y,rx=i.rx,ry=i.ry) for i in historic_map.ISLANDS])

def spawn_future_abandoned_sites(r):
 if r.get('_future_sites_spawned') or r.get('_map_geometry')!='continental':return
 if not any(p.get('historical',{}).get('era')=='future' for p in r['players']):return
 rng=random.Random(6809);sites=[]
 for kind,count,size,hp in [('abandoned_car',9,35,150),('road_business',3,90,450),('abandoned',3,65,600)]:
  for _ in range(count):
   for attempt in range(1500):
    x=rng.randrange(900,WORLD_W-900);y=rng.randrange(900,WORLD_H-900)
    if kind=='road_business' and r.get('road_routes'):
     route=rng.choice(r['road_routes']);i=rng.randrange(len(route)-1);a,b=route[i],route[i+1];dx,dy=b[0]-a[0],b[1]-a[1];length=max(1,math.hypot(dx,dy));t=rng.uniform(.15,.85);ax,ay=a[0]+dx*t,a[1]+dy*t;offset=rng.choice([-1,1])*rng.randint(210,280);x,y=ax-dy/length*offset,ay+dx/length*offset
     if any(water_at(x+(ax-x)*step/24,y+(ay-y)*step/24,r=r) or cliff_at(r,x+(ax-x)*step/24,y+(ay-y)*step/24) for step in range(25)):continue
    if water_at(x,y,r=r) or cliff_at(r,x,y) or route_lane(r,x,y,size+80):continue
    if any(math.hypot(x-o['x'],y-o['y'])<size+180 for o in r['entities']+r['nodes']+r['props']+sites):continue
    if kind=='road_business':
     px,py=x+dx/length*190,y+dy/length*190
     if road_lane(px,py,110,r=r) or any(math.hypot(px-o['x'],py-o['y'])<180+o.get('size',0) for o in r['entities']+r['nodes']+r['props']+sites):continue
     if any(water_at(px+ox,py+oy,r=r) or cliff_at(r,px+ox,py+oy) for ox,oy in [(0,0),(-100,-50),(100,50)]):continue
    site=dict(id='future-site-'+secrets.token_hex(5),kind=kind,x=x,y=y,hp=hp,maxhp=hp,owner=None,size=size,variant=rng.randrange(2),angle=0)
    if kind=='road_business':site.update(variant=_%2,parking=dict(x=px,y=py,angle=math.atan2(dy,dx)),road_access=dict(x=ax,y=ay))
    if kind=='abandoned':site.update(building_kind=rng.choice(['barracks','factory','academy']),district='FORGOTTEN OUTPOST')
    sites.append(site);break
 r['props'].extend(sites);r['_future_sites_spawned']=True;r.pop('_nav_static',None)

def player_capacity(r):return 8 if r.get('_map_geometry')=='continental' else 4

def make_late_join_space(r):
 if r.get('_map_geometry')!='continental' or len(r['players'])<8:return
 bot=next((p for p in r['players'] if p.get('bot')),None)
 assert bot,'Match full'
 removed={e['id'] for e in r['entities'] if e['owner']==bot['id']}
 r['entities']=[e for e in r['entities'] if e['owner']!=bot['id']]
 r['projectiles']=[shot for shot in r.get('projectiles',[]) if shot.get('owner')!=bot['id'] and shot.get('target') not in removed]
 r['players'].remove(bot);r.get('_explored',{}).pop(bot['id'],None);r.pop('_nav_static',None)

def start(r,with_intro=False):
 r.pop('_future_sites_spawned',None);r['_explored']={};r['_next_exploration']=0;r['_weather_sequence']=[];r['_weather_rng']=random.Random(secrets.randbits(64))
 ps=r['players'];assert ps,'Add a commander first'
 if len(ps)==1:r['ai_enabled']=True
 if r['mode']=='teams':
  assert all(sum(q['team']==team for q in ps)<=player_capacity(r)//2 for team in [1,2]),'Too many players on one team'
  assert r.get('ai_enabled') or len(set(p['team'] for p in ps))>=2,'Choose opposing teams or enable Frontier Forces'
 if r.get('ai_enabled'):
  for j in range(min(2,8-len(ps)) if r.get('_map_geometry')=='continental' else 2):ps.append(dict(id='garrison-'+str(j),name=['Ironwatch Legion','Nightfall Pact'][j],team=3,faction=['Ironwatch','Nightfall'][j],bot=True,design=['ironwatch','nightfall'][j],alive=True))
 if r.get('_map_geometry')=='continental':
  initialize_continental_map(r)
  for i,p in enumerate(ps):initialize_commander(r,p,i)
  update_weather(r)
  if with_intro:r.update(phase='intro',intro_remaining=INTRO_DURATION,intro_duration=INTRO_DURATION)
  return
 r.update(phase='battle',elapsed=0,winner=None,cliffs=[dict(id=c['id'],points=list(c['points'])) for c in CLIFFS],hills=[dict(h) for h in HILLS],entities=[],effects=[],wrecks=[],craters=[],fires=[],projectiles=[],nodes=[dict(x=x,y=y,stock=MINE_STOCK,kind='metal') for x,y in [(7200,4800),(5000,3000),(9400,6600),(9400,3000),(5000,6600)]])
 # Three separated starter sites leave a clear construction area around each spawn.
 for x,y in START_BASES:
  sx=-1 if x>WORLD_W-1000 else 1;sy=-1 if y>WORLD_H/2 else 1
  for kind,radius,degrees in [('metal',750,15),('wood',950,45),('riftglass',800,80)]:
   angle=math.radians(degrees)
   r['nodes'].append(dict(x=x+sx*math.cos(angle)*radius,y=y+sy*math.sin(angle)*radius,stock=deposit_stock(kind),kind=kind))
 for n in r['nodes']:
  for _ in range(5):
   if not water_at(n['x'],n['y'],r=r) and not cliff_at(r,n['x'],n['y']):break
   n['x']+=350 if n['x']>=WORLD_W/2 else -350
 r['props']=scenery()
 # Fixed starter and central deposits obey the same road and bridge clearance as random sites.
 for n in r['nodes']:
  if not route_lane(r,n['x'],n['y'],120):continue
  base=min(START_BASES,key=lambda b:math.hypot(n['x']-b[0],n['y']-b[1]));near=math.hypot(n['x']-base[0],n['y']-base[1])<1200
  for _ in range(1000):
   angle=random.random()*math.tau;radius=random.uniform(700,1100) if near else random.uniform(350,1100);cx,cy=base if near else (n['x'],n['y']);x=cx+math.cos(angle)*radius;y=cy+math.sin(angle)*radius
   if not (180<x<WORLD_W-180 and 180<y<WORLD_H-180) or water_at(x,y,r=r) or cliff_at(r,x,y) or route_lane(r,x,y,120):continue
   if any(math.hypot(x-bx,y-by)<650 for bx,by in START_BASES) or any(o is not n and math.hypot(x-o['x'],y-o['y'])<400 for o in r['nodes']):continue
   n.update(x=x,y=y);break
 scatter_resources(r)
 for i,node in enumerate(r['nodes']):
  node.update(id='deposit-'+str(i),hp=500,maxhp=500,owner=None,max_stock=deposit_stock(node['kind']));prepare_mine(r,node)
 if r.get('_experimental_history'):add_historical_deposits(r)
 for i,p in enumerate([q for q in ps if not q.get('bot')]):initialize_commander(r,p,i)
 for i,p in enumerate([q for q in ps if q.get('bot')]):initialize_commander(r,p,i)
 update_weather(r)
 if with_intro:r.update(phase='intro',intro_remaining=INTRO_DURATION,intro_duration=INTRO_DURATION)
def replenish_deposits(r):
 pending=r.setdefault('pending_deposits',[])
 for node in material_sources(r):
  if node.get('stock',1)<=0 and node['hp']>0 and node['kind']!='wreck' and not node.get('finite'):pending.append(dict(kind=material_kind(node),oldx=node['x'],oldy=node['y']))
 r['props']=[prop for prop in r.get('props',[]) if prop.get('stock',1)>0 or prop['hp']<=0]
 r['wrecks']=[w for w in r.get('wrecks',[]) if w['stock']>0 and w['hp']>0 and not w.get('restored')]
 r['nodes']=[node for node in r['nodes'] if node.get('stock',1)>0 or node['hp']<=0]
 remaining=[]
 for job in pending:
  for _ in range(300):
   x=random.uniform(180,WORLD_W-180);y=random.uniform(180,WORLD_H-180)
   if water_at(x,y,r=r) or cliff_at(r,x,y) or route_lane(r,x,y,120) or math.hypot(x-job['oldx'],y-job['oldy'])<600 or any(math.hypot(x-bx,y-by)<650 for bx,by in START_BASES):continue
   if any(math.hypot(x-o['x'],y-o['y'])<400 for o in r['nodes']):continue
   if any(o['hp']>0 and o['kind'] in FOOTPRINTS and math.hypot(x-o['x'],y-o['y'])<220 for o in r['entities']):continue
   if any(math.hypot(x-f['x'],y-f['y'])<f['radius']+80 for f in r.get('fires',[])):continue
   if any(o['kind'] in ['abandoned','bridge'] and math.hypot(x-o['x'],y-o['y'])<240 for o in r.get('props',[])):continue
   kind=job['kind'];r['nodes'].append(dict(id='deposit-'+secrets.token_hex(8),kind=kind,x=x,y=y,hp=500,maxhp=500,stock=deposit_stock(kind),max_stock=deposit_stock(kind),owner=None));prepare_mine(r,r['nodes'][-1]);break
  else:remaining.append(job)
 r['pending_deposits']=remaining
def production_seconds(kind):
 return 6 if kind=='infantry' else 9 if kind in ['medic','engineer','grenadier','marksman','hacker'] else 18 if kind in ['fighter','bomber'] else 12
def nearest_water(x,y,maximum=250,r=None):
 if water_at(x,y,r=r):return (x,y)
 for radius in range(20,maximum+1,20):
  for i in range(24):
   angle=i*math.tau/24;xx=x+math.cos(angle)*radius;yy=y+math.sin(angle)*radius
   if 20<xx<WORLD_W-20 and 20<yy<WORLD_H-20 and water_at(xx,yy,r=r):return (xx,yy)
 return None

def shore_positions(r,ship,maximum=180):
 cache=r.setdefault('_shore_cache',{});key=(ship['id'],round(ship['x']/20),round(ship['y']/20),int(r.get('elapsed',0)*2),maximum)
 if key in cache:return cache[key]
 if len(cache)>64:cache.clear()
 points=[]
 for radius in range(55,maximum+1,20):
  for i in range(24):
   angle=i*math.tau/24;x=ship['x']+math.cos(angle)*radius;y=ship['y']+math.sin(angle)*radius
   if 20<x<WORLD_W-20 and 20<y<WORLD_H-20 and not water_at(x,y,r=r) and not cliff_at(r,x,y) and not any(e['hp']>0 and e['kind'] in FOOTPRINTS and abs(x-e['x'])<FOOTPRINTS[e['kind']][0]+10 and abs(y-e['y'])<FOOTPRINTS[e['kind']][1]+10 for e in r['entities']):points.append(dict(x=x,y=y))
 cache[key]=points;return points

def tick_production(r,p,dt):
 for factory in list(r['entities']):
  queue=factory.get('production',[])
  if factory['owner']!=p['id'] or factory['hp']<=0 or not queue:continue
  budget=dt
  while queue and budget>0:
   job=queue[0];job['paused']='Under construction' if under_construction(factory) else 'Building packed' if factory.get('packed') else 'Insufficient power' if p.get('power',20)<0 and job['kind']!='harvester' else None
   if job['paused']:break
   amount=min(budget,job['seconds']-job['progress']);job['progress']+=amount;budget-=amount
   if job['progress']+1e-8<job['seconds']:break
   spawn=nearest_water(factory['x'],factory['y'],r=r) if job['kind'] in NAVAL else (factory['x']+random.randrange(-25,26),factory['y']+70)
   if not spawn:job['paused']='No water available at dock';break
   try:entity(r,p,job['kind'],*spawn,recruitment_era=job.get('era_ordered'))
   except AssertionError:job['paused']='Exit occupied — waiting for clear grid space';break
   queue.pop(0)
def command(r,p,d,automatic=False):
 sync_historical_bank(p)
 try:return _command(r,p,d,automatic)
 finally:
  sync_historical_bank(p,to_history=d.get('action')!='advance_era')
  if d.get('action') in ['move','formation','attack','gather','engineer_repair','hack','reclaim']:
   ids=set(d.get('ids',[]))
   for e in r.get('entities',[]):
    if e['owner']==p['id'] and e['id'] in ids:e.pop('_nav_job',None);e.pop('_traffic_job',None)
  if d.get('action') in ['build','wall_line','gate_line','rotate_building','relocate_building','demolish']:r.pop('_barrier_index',None)

def _command(r,p,d,automatic=False):
 a=d['action']
 if a=='start':
  assert p==r['players'][0] and r['phase']=='lobby','Host only';start(r,with_intro=True);return
 if a=='config':
  assert r['phase']=='lobby','Match already started'
  if 'mode' in d:
   assert p==r['players'][0] and d['mode'] in ['ffa','teams'],'Host only';r['mode']=d['mode']
  if 'map_preset' in d:
   assert p==r['players'][0],'Host only';assert d['map_preset'] in ['frontier','continental'],'Unknown map'
   assert d['map_preset']!='frontier' or len([q for q in r['players'] if not q.get('bot')])<=4,'Pinewatch supports four human players; keep Continental for larger matches'
   r['map_preset']=d['map_preset'];r['_experimental_history']=d['map_preset']=='continental';r['_map_geometry']='continental' if d['map_preset']=='continental' else 'frontier'
  if 'weather_mode' in d:
   assert p==r['players'][0],'Host only';assert d['weather_mode'] in ['dynamic','clear','rain','snow','dust'],'Choose a weather mode';r['weather_mode']=d['weather_mode']
  if 'start_hour' in d:
   assert p==r['players'][0],'Host only';assert d['start_hour'] in [0,6,12,18],'Choose a starting time';r['start_hour']=d['start_hour']
  if 'difficulty' in d:
   assert p==r['players'][0],'Host only';assert d['difficulty'] in DIFFICULTIES,'Choose Easy, Normal, Hard or Brutal';r['difficulty']=d['difficulty']
  if 'ai_enabled' in d:
   assert p==r['players'][0],'Host only';r['ai_enabled']=bool(d['ai_enabled'])
  if 'faction' in d:
   assert d['faction'] in ['Bastion','Vesper','Ironwatch','Nightfall'];p['faction']=d['faction']
  if 'team' in d:
   assert d['team'] in [1,2];assert sum(q['id']!=p['id'] and q['team']==d['team'] for q in r['players'] if not q.get('bot'))<2,'That team is full';p['team']=d['team']
  return
 assert r['phase']=='battle' and p['alive'],'Match is not active'
 if a=='autopilot':
  assert not d.get('enabled'),'Human autopilot has been removed'
  p['auto_idle']=False;p['autopilot']=False;return
 if not automatic and not p.get('bot'):
  p['last_input']=r['elapsed'];p['autopilot']=False
 if a=='activity':return
 if a=='advance_era':
  assert r.get('_experimental_history') and p.get('historical'),'Historical era mode is unavailable'
  assert research_facility(r,p,'core'),'A completed command center is required'
  try:era_rules.begin_advance(p['historical'])
  except era_rules.EraError as error:raise AssertionError(str(error)) from error
  return
 if a=='research':
  key=d.get('tech');assert key in TECHS,'Unknown technology'
  assert key not in p.get('tech',[]),'Technology already completed'
  assert not p.get('research'),'A research project is already running'
  reason=research_reason(r,p,key);assert reason is None,reason
  pay_costs(p,tech_for(p,key)['costs'])
  p['research']=dict(key=key,progress=0,paused=None);p['research_notice']='Research started: '+TECHS[key]['name'];return
 es=[e for e in r['entities'] if e['owner']==p['id']]; ids=d.get('ids',[])
 if a in ['rotate_building','relocate_building']:
  target=next((e for e in es if e['id']==d.get('building') and e['kind'] in FOOTPRINTS and e['hp']>0),None);assert target,'Select an owned building';assert not under_construction(target),'Wait for construction to finish'
  angle=((target.get('facing',target.get('angle',0) if target['kind'] in ['wall','gate'] else 0)+math.pi/2)%(math.tau)) if a=='rotate_building' else float(d.get('angle',target.get('facing',0)))
  x=target['x'] if a=='rotate_building' else float(d['x']);y=target['y'] if a=='rotate_building' else float(d['y']);assert all(math.isfinite(v) for v in [x,y,angle]),'Invalid placement'
  x,y=snap_building(target['kind'],x,y,angle)
  if target['kind'] in ['wall','gate']:x,y=snap_wall(r,p,x,y,angle,target['id'])
  assert clear_footprint(r,target['kind'],x,y,target['id'],angle=angle),'Building would overlap another structure or map edge'
  assert water_building(r,p,target['kind'],x,y),'Water requires a nearby dock; docks need shoreline'
  assert not any(math.hypot(x-f['x'],y-f['y'])<f['radius']+25 for f in r.get('fires',[])),'Ground is burning'
  assert not any(math.hypot(x-c['x'],y-c['y'])<c['size']*.65 and c.get('depth',0)>8 for c in r.get('craters',[])),'Crater is too deep'
  target.update(x=x,y=y,facing=angle,goal=None,packed=False)
  if target['kind'] in ['wall','gate']:target['angle']=angle
  target['grid_cols'],target['grid_rows']=[round(v/GRID_SIZE) for v in grid_occupancy.dimensions(target,FOOTPRINTS)]
  return
 if a=='gate_mode':
  gate=next((e for e in es if e['id']==d.get('building') and e['kind']=='gate'),None);assert gate,'Select your gate';assert d.get('mode') in ['auto','open','closed'];
  for section in connected_gates(r,gate):section['gate_mode']=d['mode']
  return
 if a in ['wall_line','gate_line']:
  kind='gate' if a=='gate_line' else 'wall'
  assert unlocked(p,kind),unlock_reason(p,kind)
  x=float(d['x']);y=float(d['y']);endx=float(d['endx']);endy=float(d['endy']);assert all(math.isfinite(v) for v in [x,y,endx,endy]);vertical=abs(endy-y)>abs(endx-x);length=abs(endy-y) if vertical else abs(endx-x);count=min(128,max(1,int(length/WALL_SPAN)+1));direction=1 if (endy-y if vertical else endx-x)>=0 else -1;angle=math.pi/2 if vertical else 0
  x,y=snap_building(kind,x,y,angle)
  existing=next((e for e in r['entities'] if e['owner']==p['id'] and e['kind']==kind and e['hp']>0 and math.hypot(e['x']-x,e['y']-y)<24),None)
  if existing:x,y=existing['x'],existing['y']
  else:x,y=snap_wall(r,p,x,y,angle)
  pending=[]
  for i in range(count):
   wx=x if vertical else x+i*WALL_SPAN*direction;wy=y+i*WALL_SPAN*direction if vertical else y
   if any(e['owner']==p['id'] and e['kind']==kind and e['hp']>0 and math.hypot(e['x']-wx,e['y']-wy)<2 for e in r['entities']):continue
   temp={**r,'entities':r['entities']+pending}
   assert water_building(temp,p,kind,wx,wy),'Water construction requires a nearby dock'
   assert clear_footprint(temp,kind,wx,wy,angle=angle),'Wall line overlaps a structure, cliff or map boundary'
   assert not any(math.hypot(wx-f['x'],wy-f['y'])<f['radius']+25 for f in r.get('fires',[])),'Ground is burning'
   assert not any(math.hypot(wx-m['x'],wy-m['y'])<m['size']*.65 and m.get('depth',0)>8 for m in r.get('craters',[])),'Crater is too deep to build here'
   pending.append(dict(id='pending-'+str(i),owner=p['id'],kind=kind,x=wx,y=wy,hp=STATS[kind][0],angle=angle,facing=angle))
  assert pending,'This wall is already built; drag farther to extend it'
  costs={resource:cost*len(pending) for resource,cost in material_costs(kind,p).items()}
  pay_costs(p,costs)
  for wall in pending:created=entity(r,p,kind,wall['x'],wall['y']);created.update(angle=angle,facing=angle,gate_mode='auto');begin_construction(created)
  return
 if a=='build':
  k=d['kind'];assert unlocked(p,k) or (k=='core' and not any(e['owner']==p['id'] and e['kind']=='core' and e['hp']>0 for e in r['entities'])),unlock_reason(p,k);assert k in ['warehouse','power','factory','turret','core','solar','airfield','barracks','academy','wall','gate','dock'];reason=building_limit_reason(r,p,k);assert reason is None,reason;x=float(d['x']);y=float(d['y']);assert math.isfinite(x) and math.isfinite(y) and 40<x<WORLD_W-40 and 40<y<WORLD_H-40
  assert not any(dist(dict(x=x,y=y),f)<f['radius']+25 for f in r.get('fires',[])),'Ground is burning — choose another site'
  assert not any(dist(dict(x=x,y=y),m)<m['size']*.65 and m.get('depth',0)>8 for m in r.get('craters',[])),'Crater is too deep to build here'
  angle=float(d.get('angle',0));assert math.isfinite(angle);angle=(round(angle/(math.pi/2))%4)*(math.pi/2)
  x,y=snap_building(k,x,y,angle)
  if k in ['wall','gate']:x,y=snap_wall(r,p,x,y,angle)
  assert water_building(r,p,k,x,y),'Water construction requires a nearby dock; place docks on the shoreline'
  assert clear_footprint(r,k,x,y,angle=angle),'Building footprint overlaps another structure or the map edge — leave clearance'
  pay_materials(p,k);created=entity(r,p,k,x,y);begin_construction(created)
  created['facing']=angle
  if k in ['wall','gate']:created['angle']=angle;created['gate_mode']='auto'
 if a=='train':
  k=d['kind'];assert unlocked(p,k),unlock_reason(p,k);assert k in ['knight','harvester','tank','walker','scout','infantry','lancer','fighter','bomber','grenadier','marksman','medic','jeep','engineer','hacker','transport','gunboat'];assert (k!='tank' or p['faction']!='Vesper') and (k!='walker' or p['faction']=='Vesper')
  fs=[e for e in es if e['kind']==('dock' if k in NAVAL else 'core' if k=='harvester' else 'airfield' if k in ['fighter','bomber'] else 'barracks' if k in ['knight','infantry','medic','engineer','grenadier','marksman','hacker'] else 'factory') and not e['packed'] and not under_construction(e)];assert fs,'Build the required producer: barracks for all soldiers/specialists, factory for vehicles, airfield for aircraft'
  if d.get('producer'):
   fs=[e for e in fs if e['id']==d['producer']];assert fs,'Select an owned, deployed building that produces this unit'
  assert k=='harvester' or p.get('power',0)>=0,'Build more power plants first'
  assert sum(e['kind'] not in FOOTPRINTS for e in es)+sum(len(e.get('production',[])) for e in es)<60,'Unit limit reached'
  producer=min(fs,key=lambda e:len(e.get('production',[])));assert len(producer.get('production',[]))<5,'Production queue full (5 units)'
  pay_materials(p,k);producer.setdefault('production',[]).append(dict(kind=k,seconds=production_seconds(k),progress=0,paused=None,**(dict(era_ordered=p['historical']['era']) if p.get('historical_shared') else {})))
 if a=='board':
  ship=next((e for e in es if e['id']==d.get('transport') and e['kind']=='transport' and e['hp']>0),None);assert ship,'Select your troop transport'
  assert shore_positions(r,ship,180),'Move the transport close to shore first'
  troops=[e for e in es if e['id'] in ids and e['kind'] in TRANSPORTABLE and e['hp']>0 and not e.get('embarked')];assert troops,'Select your infantry or specialists first'
  already=sum(e.get('embarked')==ship['id'] or e.get('board_target')==ship['id'] for e in es);available=max(0,TRANSPORT_CAPACITY-already);assert available>0,'Transport is full'
  for troop in troops[:available]:troop.update(board_target=ship['id'],goal=None,attack=None,repair_target=None,reclaim_target=None,hack_target=None)
  return
 if a=='unload':
  ship=next((e for e in es if e['id']==d.get('transport') and e['kind']=='transport' and e['hp']>0),None);assert ship,'Select your troop transport'
  passengers=[e for e in es if e.get('embarked')==ship['id'] and e['hp']>0];assert passengers,'Transport has no troops aboard'
  points=shore_positions(r,ship);assert points,'Move the transport close to shore to unload'
  occupancy=make_occupancy(r);placed=0
  for troop in passengers:
   spot=None
   for point in points:
    candidate=occupancy.nearest(troop,point['x'],point['y'],rings=5)
    if candidate and math.hypot(candidate[0]-ship['x'],candidate[1]-ship['y'])<240:spot=candidate;break
   if not spot:break
   troop.update(x=spot[0],y=spot[1],embarked=None,board_target=None,goal=None);occupancy.add(troop);placed+=1
  assert placed,'No room on shore to unload troops'
  ship['passengers']=sum(e.get('embarked')==ship['id'] and e['hp']>0 for e in es)
  return
 if a=='hack':
  assert unlocked(p,'hacker'),'Complete Storm Technology to unlock hackers'
  target=next((e for e in r['entities'] if e['id']==d.get('target') and e['hp']>0),None)
  assert target and not target.get('embarked') and target['kind'] not in FOOTPRINTS and not ally(r,p['id'],target['owner']),'Select an enemy mobile unit; buildings cannot be hacked'
  assert any(dist(target,f)<280 for f in r['entities'] if ally(r,p['id'],f['owner']) and f['hp']>0),'Target is outside shared vision'
  hackers=[e for e in es if e['id'] in ids and e['kind']=='hacker' and e['hp']>0];assert hackers,'Select one of your hackers first'
  assert sum(e['kind'] not in FOOTPRINTS for e in es)<60,'Unit limit reached'
  existing=target.get('hack');assert not existing or existing['owner']==p['id'] or not any(e['id']==existing['hacker'] and e['hp']>0 and e.get('hack_target')==target['id'] for e in r['entities']),'Another army is already hacking this unit'
  hacker=min(hackers,key=lambda e:dist(e,target));target['hack']=dict(owner=p['id'],hacker=hacker['id'],progress=0,seconds=9 if 'electronic_warfare' in p.get('tech',[]) else 12,paused='Closing uplink range');hacker['hack_target']=target['id'];hacker['goal']=[target['x'],target['y']];hacker['attack']=None
 if a=='reclaim':
  assert unlocked(p,'engineer'),unlock_reason(p,'engineer')
  target=next((o for o in r.get('props',[])+r.get('wrecks',[]) if o['id']==d.get('target') and ((o['kind'] in ['abandoned','wreck'] and o['hp']>0) or (o['kind']=='bridge' and o['hp']<o['maxhp']))),None);assert target,'Choose an abandoned facility or damaged bridge'
  kind=target.get('building_kind','bridge');assert kind=='bridge' or unlocked(p,kind) or (kind=='core' and not any(e['owner']==p['id'] and e['kind']=='core' and e['hp']>0 for e in r['entities'])),unlock_reason(p,kind)
  if kind!='bridge':
   reason=building_limit_reason(r,p,kind,target['id']);assert reason is None,reason
  engineers=[e for e in es if e['id'] in ids and e['kind']=='engineer' and e['hp']>0];assert engineers,'Select one of your engineers first'
  assert any(dist(target,f)<sight_range(p,f)+target_extent(target) for f in r['entities'] if ally(r,p['id'],f['owner']) and f['hp']>0),'Explore the site before reclaiming it'
  assert kind=='bridge' or clear_footprint(r,kind,target['x'],target['y'],target['id'],ignore_units=True),'Restoration site is blocked by a building'
  previous=target.get('rebuild');same=previous and previous['owner']==p['id']
  if previous and not same:assert not any(e['id']==previous['engineer'] and e['hp']>0 and e.get('reclaim_target')==target['id'] for e in r['entities']),'Another army is already rebuilding this site'
  if not same:
   costs=dict(metal=25,wood=20,riftglass=0) if kind=='bridge' else {resource:math.ceil(cost*.5) for resource,cost in material_costs(kind,p).items()}
   pay_costs(p,costs)
  engineer=min(engineers,key=lambda e:dist(e,target))
  for e in es:
   if e.get('reclaim_target')==target['id']:e['reclaim_target']=None
  target['rebuild']=dict(owner=p['id'],engineer=engineer['id'],progress=previous['progress'] if same else 0,seconds=30,paused='Engineer travelling')
  engineer['repair_target']=None;engineer['reclaim_target']=target['id']
  if kind=='bridge':
   a=target.get('angle',0);side=-1 if (engineer['x']-target['x'])*math.cos(a)+(engineer['y']-target['y'])*math.sin(a)<0 else 1;reach=target.get('span',480)/2+35;engineer['goal']=[target['x']+side*math.cos(a)*reach,target['y']+side*math.sin(a)*reach]
  else:engineer['goal']=[target['x']+65,target['y']+45]
  engineer['attack']=None
 if a=='engineer_repair':
  target=next((e for e in es if e['id']==d.get('building') and e['kind'] in FOOTPRINTS and e['hp']>0),None);assert target,'Select an owned active building'
  assert target['hp']<target['maxhp'],'Building is already at full health'
  engineers=[e for e in es if e['id'] in ids and e['kind']=='engineer' and e['hp']>0];assert engineers,'Select your engineers first'
  for engineer in engineers:engineer.update(repair_target=target['id'],reclaim_target=None,attack=None,goal=None,repair_notice='Travelling to repair')
 if a=='repair':
  target=next((e for e in es if e['id']==d.get('building') and e['kind'] in FOOTPRINTS),None)
  assert target and target['hp']>0,'Select one of your active buildings'
  damage=max(0,target['maxhp']-target['hp']);assert damage>0,'Building is already at full health'
  cost=math.ceil(damage/20);assert p['metal']>=cost,'Not enough metal to repair'
  p['metal']-=cost;target['hp']=target['maxhp']
 if a=='gather':
  resource=d.get('resource');historic=r.get('_experimental_history') and p.get('historical');allowed=['auto','food','wood','stone','gold','iron','riftglass'] if historic else ['auto','metal','riftglass','wood'];assert resource in allowed,'Unknown gathering resource';assert not (historic and resource=='riftglass' and p['historical']['era']!='future'),'Riftglass requires the Future Age'
  target=next((n for n in material_sources(r) if n['id']==d.get('node') and n['hp']>0 and n['stock']>0 and material_kind(n)==resource),None)
  if d.get('node'):assert target,'That deposit is depleted or unavailable'
  for e in es:
   if e['id'] in ids and e['kind']=='harvester':e.update(gather=resource,resource_target=target['id'] if target else None,goal=None,load_type=resource if resource!='auto' else e.get('load_type','metal'),returning=False,storage_blocked=False,harvesting=False);e.pop('_route',None);e.pop('_route_key',None);e.pop('_mine_node',None)
 if a=='pack':
  for e in es:
   if e['id'] in ids and e['kind'] in ['factory','power']:
    if e['packed']:assert clear_footprint(r,e['kind'],e['x'],e['y'],e['id']),'Cannot deploy: building footprint is occupied'
    e['packed']=not e['packed'];e['goal']=None
 if a=='demolish':
  for e in es:
   if e['id'] in ids:e['hp']=0
 if a=='attack':
  target=next((o for o in r['entities']+r['nodes']+r.get('props',[]) if o['id']==d.get('target') and o['hp']>0),None);assert target and not target.get('embarked') and not ally(r,p['id'],target.get('owner')),'Choose an enemy or scenery object'
  assert any(dist(target,f)<sight_range(p,f)+target_extent(target) for f in r['entities'] if ally(r,p['id'],f['owner'])),'Target is outside shared vision'
  if target['kind'] in ['fighter','bomber'] and any(e['id'] in ids and e.get('historical_role') in ['spearman','archer','knight'] for e in es):
   assert any(e['id'] in ids and STATS[e['kind']][2] and e.get('historical_role') not in ['spearman','archer','knight'] for e in es),'Spearmen and archers cannot attack aircraft'
  for e in es:
   if e['id'] in ids and STATS[e['kind']][2] and not (e.get('historical_role') in ['spearman','archer','knight'] and target['kind'] in ['fighter','bomber']):e['attack']=target['id'];e['goal']=None;e['attack_order']='ai' if automatic else 'player';e.pop('_defend_origin',None)
 if a=='pace':
  for e in es:
   if e['id'] in ids and e['kind'] in ['infantry','grenadier','marksman','medic','engineer','hacker']:e['running']=bool(d.get('running',True))
 if a in ['move','formation']:
  movers=[e for e in es if e['id'] in ids and e['hp']>0 and not e.get('embarked') and (STATS[e['kind']][1] or e['packed'])]
  if not movers:return
  kind=d.get('formation',p.get('formation','box'));assert kind in grid_occupancy.FORMATIONS,'Unknown formation'
  if a=='formation' and 'x' not in d:x=sum(e['x'] for e in movers)/len(movers);y=sum(e['y'] for e in movers)/len(movers)
  else:x=float(d['x']);y=float(d['y'])
  angle=float(d.get('angle',p.get('formation_angle',0)));assert all(math.isfinite(v) for v in [x,y,angle]),'Invalid formation location'
  assert 0<=x<=WORLD_W and 0<=y<=WORLD_H,'Choose a location inside the map'
  assert not any(e['kind'] in NAVAL for e in movers) or water_at(x,y,r=r),'Ships must move on water'
  assert not cliff_at(r,x,y) or all(e['kind'] in ['fighter','bomber'] for e in movers),'Cliff terrain is impassable; choose clear ground'
  slots=grid_occupancy.formation_slots(make_occupancy(r),movers,x,y,kind,angle)
  p['formation']=kind;p['formation_angle']=angle;group=secrets.token_hex(5)
  for e,slot in slots:
   e.pop('_repair_origin',None);e.pop('_defend_origin',None);e.pop('_route',None);e.pop('_route_key',None)
   e['_formation_group']=group;e['_formation_depth']=round(math.hypot(slot[0]-x,slot[1]-y)/GRID_SIZE)
   e.update(auto_repair=False,move_order=True,repair_target=None,repairing=False,hack_target=None,reclaim_target=None,board_target=None,attack=None,goal=list(slot),formation=kind,formation_slot=list(slot),waiting_for_space=False)
 if not automatic and a in ['build','train','move','formation','pack','gather','pace','attack','demolish','repair','engineer_repair','reclaim','hack']:
  p['autopilot']=False;p['advice']='Manual command active.'
def commander_ai(r,p):
 if not p.get('bot'):return
 own=[e for e in r['entities'] if e['owner']==p['id'] and e['hp']>0]
 base=next((e for e in own if e['kind']=='core'),next((e for e in own if e['kind'] in FOOTPRINTS),None))
 if not base:return
 friends=[e for e in r['entities'] if ally(r,p['id'],e['owner']) and e['hp']>0]
 threats=[e for e in r['entities'] if not ally(r,p['id'],e['owner']) and any(dist(e,f)<300 and (f['kind'] in FOOTPRINTS or STATS[f['kind']][2] or f['kind']=='harvester') for f in friends)]
 active=lambda kind:[e for e in own if e['kind']==kind and not e['packed']]
 if p.get('power',20)<20:plan='solar' if active('power') else 'power'
 elif not active('power') and not active('solar'):plan='power'
 elif not active('barracks'):plan='barracks'
 elif any(p.get(k,0)>=storage_capacity(r,p)*.85 for k in ['metal','wood','riftglass']):plan='warehouse'
 elif not active('factory'):plan='factory'
 elif len(active('harvester'))<2:plan='harvester'
 elif len(active('turret'))<2:plan='turret'
 elif len(active('infantry'))<6:plan='infantry'
 elif not active('academy'):plan='academy'
 elif len(active('medic'))<1:plan='medic'
 elif len(active('grenadier'))<2:plan='grenadier'
 elif len(active('marksman'))<1:plan='marksman'
 elif len(active('lancer'))<1:plan='lancer'
 elif not active('airfield'):plan='airfield'
 elif len(active('fighter'))<2:plan='fighter'
 elif len(active('bomber'))<1:plan='bomber'
 else:plan='tank' if p['faction']!='Vesper' else 'walker'
 p['advice']=('Enemy approaching an allied base: reinforce its defenses.' if threats else 'Recommended next: '+plan+'. Gather wood for construction, metal for armor, and Riftglass for advanced weapons.')
 if not p.get('bot'):
  p['autopilot']=bool(p.get('auto_idle',True) and r['elapsed']-p.get('last_input',0)>=30)
 if not p.get('autopilot'):return
 def issue(action,**data):
  try:command(r,p,dict(action=action,**data),automatic=True);return True
  except (AssertionError,KeyError):return False
 if p.get('historical_shared') and not p['historical'].get('era_job'):
  issue('advance_era')
 if p.get('historical_shared') and plan and era_rules.kind_era_reason(p['historical'],plan):
  plan='barracks' if not active('barracks') else 'harvester' if len(active('harvester'))<2 else 'academy' if not active('academy') else 'infantry' if len(active('infantry'))<8 else 'knight' if era_rules.index_for(p['historical']['era'])>=era_rules.index_for('medieval') and len(active('knight'))<2 else 'marksman' if era_rules.index_for(p['historical']['era'])>=era_rules.index_for('ancient') and len(active('marksman'))<2 else None
 if plan and not unlocked(p,plan):
  required='engineering_basics' if plan=='engineer' and p.get('historical_shared') else UNLOCKS[plan]
  def next_tech(key):
   for prerequisite in tech_for(p,key)['requires']:
    if prerequisite not in p.get('tech',[]):return next_tech(prerequisite)
   return key
  needed=next_tech(required);facility=tech_for(p,needed)['facility']
  if not active('academy'):plan='academy'
  elif not active(facility):plan=facility
  else:
   plan=None
   if not p.get('research'):
    reason=research_reason(r,p,needed)
    if reason:p['advice']='Research '+TECHS[needed]['name']+': '+reason
    else:issue('research',tech=needed);p['advice']='Researching '+TECHS[needed]['name']
 if plan in ['warehouse','power','factory','turret','solar','airfield','barracks','academy']:
  for radius in [85,140,195]:
   built=False
   for i in range(12):
    angle=i*math.tau/12;x=base['x']+math.cos(angle)*radius;y=base['y']+math.sin(angle)*radius
    if issue('build',kind=plan,x=x,y=y):built=True;break
   if built:break
 elif plan:issue('train',kind=plan)
 # Repair nearby friendly structures using this commander's own credits.
 for e in friends:
  if e['kind'] in ['core','power','factory','turret','solar','airfield','barracks','academy'] and e['hp']<e['maxhp'] and dist(e,base)<350 and p['metal']>=1:
   e['hp']=min(e['maxhp'],e['hp']+24);p['metal']-=1;break
 army=[e for e in own if e['kind'] in ['knight','infantry','tank','walker','scout','lancer','fighter','bomber','grenadier','marksman','medic','jeep']]
 if threats:
  target=min(threats,key=lambda e:dist(base,e));p['advice']='Autopilot: reinforcing '+player(r,min(friends,key=lambda f:dist(f,target))['owner'])['name']+' against nearby enemies.'
  for i,e in enumerate(army):
   if STATS[e['kind']][2]:issue('attack',ids=[e['id']],target=target['id'])
 elif p.get('bot'):
  tuning=DIFFICULTIES[r.get('difficulty','normal')]
  if r['elapsed']>=max(tuning['raid_after'],p.get('next_raid',0)) and len(army)>=4:
   # Clear surviving structures throughout the enemy territory, including expansions.
   targets=[e for e in r['entities'] if e['hp']>0 and not ally(r,p['id'],e['owner']) and not e.get('embarked')]
   live_ids={e['id'] for e in r['entities'] if e['hp']>0}
   ready=[e for e in army if STATS[e['kind']][2] and e.get('attack') not in live_ids]
   if targets and ready:
    lead=min(ready,key=lambda e:min(dist(e,t) for t in targets));target=min(targets,key=lambda t:combat_priority(lead,t))
    travelling=[]
    for e in sorted(ready,key=lambda e:dist(e,target))[:tuning['raid_size']]:
     if not issue('attack',ids=[e['id']],target=target['id']):travelling.append(e['id'])
    if travelling:issue('move',ids=travelling,x=target['x'],y=target['y'],formation='box')
    p['next_raid']=r['elapsed']+tuning['raid_interval']
 elif len(army)>=6:
  visible=[e for e in r['entities'] if not ally(r,p['id'],e['owner']) and any(dist(e,f)<280 for f in friends)]
  target=min(visible,key=lambda e:dist(base,e),default=None)
  if not target:
   nodes=[n for n in r['nodes'] if dist(base,n)>400];target=nodes[int(r['elapsed']//25)%len(nodes)] if nodes else base
  for i,e in enumerate(army):
   if not e['goal']:issue('move',ids=[e['id']],x=target['x']+(i%3-1)*20,y=target['y']+(i//3)*20)
 # Relocate threatened mobile buildings away from the active storm band.
 for e in own:
  if e['kind'] in ['power','factory'] and abs(e['x']-r.get('storm',-400))<120:
   if not e['packed']:issue('pack',ids=[e['id']])
   issue('move',ids=[e['id']],x=e['x']+(200 if e['x']>r['storm'] else -200),y=e['y'])
  elif e['packed'] and not e['goal']:issue('pack',ids=[e['id']])
def tick(r,dt):
 if r['phase']=='intro':
  r['intro_remaining']=max(0,r['intro_remaining']-dt)
  if r['intro_remaining']<=0.000001:r['phase']='battle'
  return
 if r['phase']!='battle':return
 if r['elapsed']>=r.get('_next_exploration',0):
  for commander in r['players']:explored_cells(r,commander)
  r['_next_exploration']=r['elapsed']+.5
 r['elapsed']+=dt
 for e in r['entities']:
  if e['kind']=='hacker':e['hacking']=False
  if e['hp']>0 and under_construction(e):e['construction']['progress']=min(e['construction']['seconds'],e['construction']['progress']+dt)
 update_weather(r,dt);r['effects']=[fx for fx in r['effects'] if r['elapsed']-fx['born']<fx.get('duration',1.5)];storm=int(r['elapsed']//45)%3; sx=[-400,WORLD_W/2,WORLD_W*.653][storm] if r['weather']['kind']=='dust' else -400;r['storm']=sx
 if r.get('laststorm')!=int(r['elapsed']//45):
  r['laststorm']=int(r['elapsed']//45)
  if storm:
   for n in r['nodes']:
    if abs(n['x']-sx)<120 and not n.get('finite'):n['stock']=min(deposit_stock(n['kind']),n['stock']+4000)
 for p in r['players']:
  if r.get('_experimental_history') and p.get('historical') and p['alive']:
   era_rules.advance_time(p['historical'],dt,paused=not research_facility(r,p,'core'))
   upgrade_buildings_for_era(r,p)
   spawn_future_riftglass(r);spawn_future_abandoned_sites(r)
  if not p.get('bot'):
   p['auto_idle']=False;p['autopilot']=False
  if p['alive'] and r['elapsed']>=p.get('ai_next',0):
   p['ai_next']=r['elapsed']+(DIFFICULTIES[r.get('difficulty','normal')]['decision'] if p.get('bot') else 60);commander_ai(r,p)
  es=[e for e in r['entities'] if e['owner']==p['id'] and not e['packed'] and not under_construction(e)];p['power']=20+sum(40 for e in es if e['kind']=='power')+sum(25 for e in es if e['kind']=='solar')-sum(20 for e in es if e['kind']=='factory')-sum(10 for e in es if e['kind']=='turret')-sum(30 for e in es if e['kind']=='airfield')-sum(5 for e in es if e['kind']=='barracks')-sum(10 for e in es if e['kind']=='academy')
  if p.get('historical_shared') and era_rules.index_for(p['historical']['era'])<era_rules.index_for('industrial'):p['power']=20
  tick_research(r,p,dt);tick_production(r,p,dt)
 # Fires damage the environment and can spread into nearby trees or timber.
 r['fires']=[f for f in r.get('fires',[]) if f['expires']>r['elapsed']]
 for fire in list(r['fires']):
  for obj in r['entities']+r['nodes']+r.get('props',[]):
   if obj['hp']>0 and not obj.get('embarked') and obj['kind'] not in ['fighter','bomber'] and dist(fire,obj)<fire['radius']:
    obj['hp']-=dt*(12 if obj['kind'] in ['tree','wood'] else 5)
  if r['elapsed']>=fire['spread']:
   fire['spread']=r['elapsed']+3;deform(r,fire['x'],fire['y'],fire['radius']*.8,depth=.5)
   fuel=next((obj for obj in r.get('props',[])+r['nodes'] if obj['kind'] in ['tree','wood'] and obj['hp']>0 and fire['radius']<dist(fire,obj)<fire['radius']+55 and not any(dist(obj,f)<25 for f in r['fires'])),None)
   if fuel:ignite(r,fuel['x'],fuel['y'],24)
 # Shells and missiles travel before applying impact damage.
 pending=[]
 for shot in r.get('projectiles',[]):
  target=next((e for e in r['entities']+r['nodes']+r.get('props',[]) if e['id']==shot['target'] and e['hp']>0),None)
  if target and shot['kind']=='missile':shot['tx']=target['x'];shot['ty']=target['y']
  dx=shot['tx']-shot['x'];dy=shot['ty']-shot['y'];distance=math.hypot(dx,dy)
  if distance<=shot['speed']*dt:
   if shot['kind']=='arrow':
    if target and not target.get('embarked') and not ally(r,shot['owner'],target.get('owner')):
     target_radius=20+(max(FOOTPRINTS[target['kind']]) if target['kind'] in FOOTPRINTS else 0)
     if math.hypot(target['x']-shot['tx'],target['y']-shot['ty'])<target_radius:
      damage_target(r,target,shot['damage'],dict(x=shot['sx'],y=shot['sy']));effect(r,'arrow_hit',shot['tx'],shot['ty'],tx=shot['tx'],ty=shot['ty'],size=5,duration=.35)
    continue
   effect(r,'explosion',shot['tx'],shot['ty'],size=46 if shot['kind']=='missile' else 24)
   deform(r,shot['tx'],shot['ty'],shot['radius']*.8,depth=5 if shot['kind'] in ['missile','shell'] else 2)
   if shot['kind'] in ['missile','shell']:ignite(r,shot['tx'],shot['ty'],min(34,shot['radius']))
   for enemy in r['entities']+r['nodes']+r.get('props',[]):
    if not enemy.get('embarked') and not ally(r,shot['owner'],enemy['owner']) and math.hypot(enemy['x']-shot['tx'],enemy['y']-shot['ty'])<shot['radius']:
     damage_target(r,enemy,shot['damage'],dict(x=shot['sx'],y=shot['sy']))
  else:
   shot['x']+=dx/distance*shot['speed']*dt;shot['y']+=dy/distance*shot['speed']*dt;pending.append(shot)
 r['projectiles']=pending
 r['_nav_topology']=hash(tuple((e['id'],e['x'],e['y'],e.get('angle',0),e.get('facing',0),e.get('gate_mode'),e['hp']>0) for e in r['entities'] if e['kind'] in FOOTPRINTS)+tuple((b['id'],b['hp']>0) for b in r.get('props',[]) if b['kind']=='bridge'))
 occupancy=make_occupancy(r);r['_occupancy']=occupancy
 # Recover old saves, disembarks or a newly restored structure without a push cascade.
 for unit in r['entities']:
  if unit['hp']<=0 or unit.get('embarked') or unit['kind'] in FOOTPRINTS and not unit.get('packed'):continue
  if next(occupancy.blockers(unit,unit['x'],unit['y']),None):
   spot=occupancy.nearest(unit,unit['x'],unit['y'],rings=30)
   if spot:unit['x'],unit['y']=spot;occupancy.add(unit)
 combat_index=CombatIndex(r['entities']);combat_padding=max((STATS[e['kind']][1] for e in r['entities']),default=0)*dt
 hostile_owners={p['id']:{q['id'] for q in r['players'] if not ally(r,p['id'],q['id'])} for p in r['players']}
 objects_by_id={o['id']:o for o in r['entities']+r['nodes']+r.get('props',[])}
 r['_barrier_index']=barrier_index.BarrierIndex(r['entities'])
 gate_groups={}
 for gate in r['entities']:
  if gate['kind']=='gate' and gate['hp']>0 and gate['id'] not in gate_groups:
   group=connected_gates(r,gate)
   for section in group:gate_groups[section['id']]=group
 gate_open={}
 for gate in r['entities']:
  if gate['kind']!='gate' or gate['id'] in gate_open:continue
  group=gate_groups.get(gate['id'],[gate]);mode=gate.get('gate_mode','auto')
  opened=mode=='open' or mode=='auto' and any(u['kind'] not in FOOTPRINTS and ally(r,gate['owner'],u['owner']) and dist(section,u)<65 for section in group for u in combat_index.nearby(section,65))
  for section in group:gate_open[section['id']]=opened
 r['_navigation_deadline']=time.perf_counter()+.012
 for e in r['entities']:
  if e['hp']<=0:continue
  if under_construction(e):continue
  if e.get('embarked'):
   ship=next((v for v in r['entities'] if v['id']==e['embarked'] and v['hp']>0),None)
   if ship:e['x']=ship['x'];e['y']=ship['y']
   else:e['hp']=0
   continue
  if e['kind']=='gate':e['open']=gate_open.get(e['id'],False)
  p=player(r,e['owner']);speed=45 if e['packed'] else STATS[e['kind']][1];e['moving']=False;e['harvesting']=False
  if speed and e['kind'] not in ['fighter','bomber']:
   e['terrain']=terrain_contact(r,e);speed*=max(.6,1-abs(e['terrain']['pitch'])*1.4-e['terrain']['rough']*.025)
   speed*=e['terrain']['speed_factor']
  if e['kind'] in ['fighter','bomber'] and 'aviation_engines' in p.get('tech',[]):speed*=1.2
  if e['kind'] in ['infantry','grenadier','marksman','medic'] and 'basic_drills' in p.get('tech',[]):speed*=1.05
  if e['kind'] in ['infantry','grenadier','marksman','medic'] and 'infantry_drills' in p.get('tech',[]):speed*=1.15
  if e['kind']=='knight' and 'cavalry_training' in p.get('tech',[]):speed*=1.15
  if e['kind'] in ['transport','gunboat'] and 'naval_engines' in p.get('tech',[]):speed*=1.2
  if e['kind']=='tank' and water_at(e['x'],e['y'],r=r):speed*=.55
  if e['kind'] in ['infantry','grenadier','marksman','medic'] and e.get('running',True):speed*=1.35
  if e['kind'] not in ['fighter','bomber'] and any(dist(e,m)<m['size'] and m.get('depth',0)>1 for m in r.get('craters',[])):speed*=.65
  e['cool']-=dt
  if e['kind']=='harvester' and not e['goal']:
   e['cargo_capacity']=harvester_capacity(p);capacity=e['cargo_capacity']
   cores=[b for b in r['entities'] if b['owner']==e['owner'] and b['kind'] in ['core','warehouse'] and b['hp']>0 and not b.get('packed') and not under_construction(b)]
   loads=e.setdefault('cargo_loads',{});total=sum(loads.values())
   if abs(total-e['cargo'])>.01:loads.clear();loads[e.get('load_type','metal')]=e['cargo']
   if e['cargo']==0:
    choice=e.get('gather','auto')
    e['load_type']=(historical_gather_choice(p) if r.get('_experimental_history') and p.get('historical') else ('wood' if p['wood']<30 else 'riftglass' if p['riftglass']<20 else 'metal')) if choice=='auto' else choice
   resource=e.get('load_type','metal');available=[n for n in material_sources(r) if n['hp']>0 and n['stock']>0 and not n.get('rebuild') and material_kind(n)==resource]
   returning=e['cargo']>=capacity or (e.get('storage_blocked',False) and e['cargo']>0) or (not available and e['cargo']>0);e['returning']=returning;targets=cores if returning else available
   if targets:
    t=next((n for n in targets if not returning and n.get('id')==e.get('resource_target')),None) or min(targets,key=lambda t:dist(e,unload_anchor(t,e)) if returning else dist(e,t))
    anchor=storage_grid_anchor(r,t,e) if returning else mining_anchor(r,t,e) if not returning and t.get('site')=='mine' else t
    if not returning and t.get('site')=='mine':
     slot=footprint_destination(r,e,[anchor['x'],anchor['y']]);anchor=dict(x=slot[0],y=slot[1])
    if returning:e['_mine_node']=None;e['unload_target']=t['id'];e['unload_kind']=t['kind']
    work_reach=18 if t.get('site')=='mine' and not returning else 35 if returning else max(grid_occupancy.dimensions(e,FOOTPRINTS))/2+35
    if dist(e,anchor)>work_reach:dest=[anchor['x'],anchor['y']]
    else:
     dest=None
     if returning:
      for carried,quantity in list(loads.items()):
       bank=p['historical']['resources'] if r.get('_experimental_history') and p.get('historical') and carried in era_rules.RESOURCES else p;delivered=min(quantity,max(0,storage_capacity(r,p)-bank.get(carried,0)));amount=delivered;bank[carried]=bank.get(carried,0)+amount;sync_historical_bank(p,to_history=False) if bank is p.get('historical',{}).get('resources') else None;p.setdefault('gathered',{})[carried]=p.get('gathered',{}).get(carried,0)+amount;loads[carried]=max(0,quantity-delivered)
      e['cargo']=sum(loads.values());e['storage_blocked']=e['cargo']>0
      if e['cargo']==0:e['unload_target']=None;e['returning']=False
     else:
      amt=min(t['stock'],capacity-e['cargo'],(16 if resource=='riftglass' else 20)*dt*(1.25 if 'extraction' in p.get('tech',[]) else 1)*(1.1 if 'stone_tools' in p.get('tech',[]) else 1)*(DIFFICULTIES[r.get('difficulty','normal')]['harvest'] if p.get('bot') else 1));t['stock']-=amt;e['cargo']+=amt;loads[resource]=loads.get(resource,0)+amt;e['harvesting']=amt>0
   else:dest=None
  else:dest=e['goal']
  if e.get('board_target'):
   ship=next((v for v in r['entities'] if v['id']==e['board_target'] and v['kind']=='transport' and v['owner']==e['owner'] and v['hp']>0),None)
   if not ship:e['board_target']=None;dest=None
   elif dist(e,ship)<=180 and ship.get('passengers',0)<TRANSPORT_CAPACITY:
    e.update(embarked=ship['id'],board_target=None,goal=None,attack=None,moving=False);ship['passengers']=sum(t.get('embarked')==ship['id'] and t['hp']>0 for t in r['entities']);continue
   else:
    points=shore_positions(r,ship,180);spot=min(points,key=lambda pt:dist(e,pt),default=None);dest=[spot['x'],spot['y']] if spot else None
  if e['kind']=='engineer':
   e['repairing']=False;e['rebuilding']=False
   assign_auto_repair(r,p,e)
   if e.get('repair_target'):
    building=next((b for b in r['entities'] if b['id']==e['repair_target'] and ally(r,b['owner'],e['owner']) and b['hp']>0 and b['kind'] in FOOTPRINTS),None)
    if not building or building['hp']>=building['maxhp']:e.update(repair_target=None,goal=None,repair_notice='Repair complete' if building else 'Repair target lost');dest=None
    elif dist(e,building)>ENGINEER_REPAIR_REACH+target_extent(building):dest=[building['x'],building['y']];e['repair_notice']='Travelling to repair'
    else:
     e['angle']=math.atan2(building['y']-e['y'],building['x']-e['x']);e['repair_point']=dict(x=building['x'],y=building['y']);dest=None;rate=18 if 'field_engineering' in p.get('tech',[]) else 12;amount=min(building['maxhp']-building['hp'],dt*rate,max(0,p['metal'])/.02,max(0,p['wood'])/.01)
     building['hp']+=amount;p['metal']-=amount*.02;p['wood']-=amount*.01;e['repairing']=amount>0;e['repair_notice']='Repairing building' if amount>0 else 'Need metal and wood to repair'
     sync_historical_bank(p)
     if amount>0 and r['elapsed']>=e.get('_repair_fx',0):effect(r,'heal',e['x'],e['y'],tx=building['x'],ty=building['y'],size=8);e['_repair_fx']=r['elapsed']+1
  if e['kind']=='hacker' and e.get('hack_target'):
   victim=next((v for v in r['entities'] if v['id']==e['hack_target'] and v['hp']>0 and not ally(r,e['owner'],v['owner'])),None)
   if victim:dest=[victim['x'],victim['y']] if dist(e,victim)>120 else None
   else:e['hack_target']=None
  if e['kind']=='medic':e['heal_range']=MEDIC_RANGE;e['healing_target']=None if e.get('heal_until',0)<r['elapsed'] else e.get('healing_target')
  if e['kind']=='medic' and e['cool']<=0:
   patients=[f for f in r['entities'] if ally(r,e['owner'],f['owner']) and f['kind'] in ['knight','infantry','grenadier','marksman','medic','engineer','hacker'] and not f.get('embarked') and 0<f['hp']<f['maxhp'] and dist(e,f)<=MEDIC_RANGE]
   if patients:
    if not dest:
     patient=min(patients,key=lambda f:f['hp']/f['maxhp']);e['angle']=math.atan2(patient['y']-e['y'],patient['x']-e['x'])
    patient=min(patients,key=lambda f:f['hp']/f['maxhp']);patient['hp']=min(patient['maxhp'],patient['hp']+(18 if 'combat_medicine' in p.get('tech',[]) else 12));e['cool']=2;e['healing_target']=patient['id'];e['heal_until']=r['elapsed']+1.2;e['heal_point']=dict(x=patient['x'],y=patient['y']);effect(r,'heal',e['x'],e['y'],tx=patient['x'],ty=patient['y'],size=8)
  ran=effective_attack_range(p,e)
  awareness=acquisition_range(p,e)
  enemies=(b for b in combat_index.nearby(e,awareness+combat_padding+80) if b['owner'] in hostile_owners[e['owner']] and can_engage(e,b) and dist(e,b)<=awareness+target_extent(b)) if ran else ()
  origin=e.get('_defend_origin')
  target=min((b for b in enemies if not origin or dist(origin,b)<awareness+target_extent(b)),key=lambda t:combat_priority(e,t),default=None)
  forced=objects_by_id.get(e.get('attack'))
  if forced and (forced['hp']<=0 or ally(r,e['owner'],forced.get('owner'))):forced=None;e['attack']=None
  if forced and can_engage(e,forced) and (e.get('attack_order')!='ai' or not target):target=forced
  reach=ran+target_extent(target) if target else ran
  if target and ran:
   e['combat_target_id']=target['id']
   chasing=bool(forced or (not e.get('goal') and STATS[e['kind']][1]))
   if chasing:
    if not forced:e.setdefault('_defend_origin',dict(x=e['x'],y=e['y']))
    dest=None if dist(e,target)<reach*.9 else [target['x'],target['y']]
  else:
   e['combat_target_id']=None
   if origin and not e.get('goal'):
    if dist(e,origin)>15:dest=[origin['x'],origin['y']]
    else:e.pop('_defend_origin',None)
  e['engaged']=bool(ran and target and dist(e,target)<reach)
  if e['engaged']:e['turret_angle']=math.atan2(target['y']-e['y'],target['x']-e['x']);e['angle']=e['turret_angle']
  if e['kind']=='turret' and not e['engaged']:e['turret_angle']=r['elapsed']*.35
  if ran and target and dist(e,target)<reach and e['cool']<=0 and (e['kind']!='turret' or p['power']>=0):
   e['turret_angle']=math.atan2(target['y']-e['y'],target['x']-e['x']);e['angle']=e['turret_angle']
   kind='pulse' if e.get('historical_role')=='advanced_gunboat' else 'shell' if e.get('historical_role')=='industrial_armor' else 'arrow' if e.get('historical_role') in ['archer','ballista_ship','ballista_tower'] else 'melee' if e.get('historical_role') in ['spearman','knight'] else 'grenade' if e['kind']=='grenadier' else 'missile' if e['kind'] in ['lancer','fighter'] else 'shell' if e['kind'] in ['tank','bomber'] else 'pulse' if e['kind']=='walker' else 'tracer'
   e['cool']=1.8 if kind=='arrow' else 3 if kind=='grenade' else 3.5 if kind=='missile' else 2.2 if kind=='shell' else 2.5 if e['kind']=='marksman' else 1.2
   if e['kind'] in ['tank','walker','lancer'] and 'stabilizers' in p.get('tech',[]):e['cool']*=.8
   e.update(attack_started=r['elapsed'],attack_cycle=e['cool'],attack_style=kind,combat_target=dict(x=target['x'],y=target['y']))
   if kind not in ['melee','arrow'] and not (kind=='grenade' and e.get('era_created')=='industrial'):effect(r,'muzzle',e['x'],e['y'],tx=target['x'],ty=target['y'],weapon=kind,size=12,source_id=e['id'])
   if kind=='melee':
    damage_target(r,target,weapon_damage(p,e,26 if e['kind']=='knight' else 14),e);effect(r,'melee',e['x'],e['y'],tx=target['x'],ty=target['y'],size=7,duration=.4)
   elif kind=='arrow':
    r['projectiles'].append(dict(id=secrets.token_hex(5),owner=e['owner'],kind=kind,target=target['id'],sx=e['x'],sy=e['y'],total=dist(e,target),x=e['x'],y=e['y'],tx=target['x'],ty=target['y'],speed=300,damage=weapon_damage(p,e,18)))
   elif kind in ['missile','shell','grenade']:
    r['projectiles'].append(dict(id=secrets.token_hex(5),owner=e['owner'],kind=kind,target=target['id'],sx=e['x'],sy=e['y'],total=dist(e,target),x=e['x'],y=e['y'],tx=target['x'],ty=target['y'],speed=130 if kind=='grenade' else 170 if kind=='missile' else 350,radius=45 if kind=='grenade' else 52 if kind=='missile' else 26,damage=weapon_damage(p,e,36 if kind=='grenade' else 34 if e['kind']=='fighter' else 75 if e['kind']=='bomber' else 62 if kind=='missile' else 48)))
   else:
    damage_target(r,target,weapon_damage(p,e,32 if e['kind']=='marksman' else 11 if e['kind']=='infantry' else 23),e);effect(r,kind,e['x'],e['y'],tx=target['x'],ty=target['y'],size=7)
  if e.get('goal') and e.get('_formation_group') and not e.get('attack'):
   waiting=any(u.get('_formation_group')==e['_formation_group'] and u.get('_formation_depth',0)<e.get('_formation_depth',0) and u.get('goal') and u['hp']>0 for u in r['entities'])
   e['formation_waiting']=waiting
   if waiting:dest=None
  else:e['formation_waiting']=False
  if dest and speed:
   dest=footprint_destination(r,e,dest)
   destination=navigation_destination(r,e,dest)
   route=e.get('_traffic_route',[])
   if e.get('_traffic_goal')!=tuple(dest):route=[]
   while route and math.hypot(e['x']-route[0][0],e['y']-route[0][1])<1:route.pop(0)
   if e.get('_blocked_steps',0)>=2 and r['elapsed']>=e.get('_traffic_retry',0) and time.perf_counter()<r.get('_navigation_deadline',float('inf')):
    route=occupancy.detour(e,dest);e['_traffic_retry']=r['elapsed']+(0 if e.get('_traffic_job') else 1);e['_traffic_goal']=tuple(dest)
   e['_traffic_route']=route
   if route:destination=route[0]
   dx,dy=destination[0]-e['x'],destination[1]-e['y'];n=math.hypot(dx,dy)
   if n<.01:e['goal']=None;e['move_order']=False
   else:
    nx=e['x']+dx/n*min(n,speed*dt);ny=e['y']+dy/n*min(n,speed*dt)
    blocked=e['kind'] not in ['tank','fighter','bomber'] and e['kind']!='engineer' and any(prop['kind']=='bridge' and prop['hp']<=0 and bridge_contains(prop,nx,ny,3) for prop in r.get('props',[]))
    barrier=barrier_hit(r,e,nx,ny) if e['kind'] not in ['fighter','bomber'] else None
    if barrier and not ally(r,e['owner'],barrier['owner']) and STATS[e['kind']][2]:e['attack']=barrier['id']
    if not blocked:
     oldx,oldy=e['x'],e['y'];moved=occupancy.move(e,nx,ny)
     direct=moved
     if not moved:
      # Yield around traffic using bounded local steering; every trial is checked.
      for offset in [.55,-.55,1.1,-1.1,math.pi/2,-math.pi/2]:
       heading=math.atan2(dy,dx)+offset;step=min(n,speed*dt);px=oldx+math.cos(heading)*step;py=oldy+math.sin(heading)*step
       if occupancy.move(e,px,py):moved=True;break
     e['waiting_for_space']=not moved;e['_blocked_steps']=0 if direct else e.get('_blocked_steps',0)+1
     if not moved:e['_blocked_steps']=e.get('_blocked_steps',0)+1
     if moved:
      e['travel']=e.get('travel',0)+math.hypot(e['x']-oldx,e['y']-oldy);e['moving']=True;e['angle']=math.atan2(e['y']-oldy,e['x']-oldx);e['hull_angle']=e['angle']
     if e['kind'] not in ['fighter','bomber']:e['terrain']=terrain_contact(r,e)
  if abs(e['x']-sx)<90:e['hp']-=2*dt


 # A continuous close-range electronic takeover; moving away or losing the hacker pauses it.
 for target in r['entities']:
  job=target.get('hack')
  if not job or target['hp']<=0:continue
  hacker=next((e for e in r['entities'] if e['id']==job['hacker'] and e['owner']==job['owner'] and e['hp']>0 and e.get('hack_target')==target['id']),None)
  owner=player(r,job['owner'])
  if not owner or not owner['alive'] or ally(r,job['owner'],target['owner']):target.pop('hack',None);continue
  job['paused']='Uplink interrupted' if not hacker else 'Out of uplink range' if dist(hacker,target)>150 else None
  if job['paused']:continue
  if sum(e['owner']==owner['id'] and e['kind'] not in FOOTPRINTS and e['hp']>0 for e in r['entities'])>=60:job['paused']='Unit limit reached';continue
  hacker['hacking']=True;hacker['hack_point']=dict(x=target['x'],y=target['y']);hacker['angle']=math.atan2(target['y']-hacker['y'],target['x']-hacker['x'])
  job['progress']=min(job['seconds'],job['progress']+dt)
  if job['progress']>=job['seconds']:
   target.update(captured_from=target['owner'],owner=owner['id'],goal=None,attack=None,reclaim_target=None,hack_target=None);target.pop('hack',None);hacker['hack_target']=None;hacker['goal']=None;owner['research_notice']='Enemy '+target['kind']+' captured — now under your control'

 # Engineers physically reach a site and work; interrupted jobs can be resumed.
 for site in r.get('props',[])+r.get('wrecks',[]):
  job=site.get('rebuild')
  if (site['hp']<=0 and site['kind']!='bridge') or not job:continue
  owner=player(r,job['owner']);engineer=next((e for e in r['entities'] if e['id']==job['engineer'] and e['owner']==job['owner'] and e['hp']>0 and e.get('reclaim_target')==site['id']),None)
  job['paused']='Engineer unavailable' if not engineer else 'Engineer travelling' if dist(engineer,site)>(site.get('span',480)/2+65 if site['kind']=='bridge' else 100) else 'Building limit reached' if site['kind']!='bridge' and building_limit_reason(r,owner,site['building_kind'],site['id']) else 'Site blocked' if site['kind']!='bridge' and not clear_footprint(r,site['building_kind'],site['x'],site['y'],site['id'],ignore_units=True) else None
  if not owner or not owner['alive'] or job['paused']:continue
  engineer['goal']=None;engineer['rebuilding']=True;engineer['repair_point']=dict(x=site['x'],y=site['y']);engineer['angle']=math.atan2(site['y']-engineer['y'],site['x']-engineer['x']);job['progress']=min(job['seconds'],job['progress']+dt*(1.5 if 'field_engineering' in owner.get('tech',[]) else 1))
  if job['progress']>=job['seconds']:
   if site['kind']=='bridge':site['hp']=site['maxhp'];site.pop('wrecked',None);site.pop('rebuild',None);owner['research_notice']='Bridge restored — crossing reopened'
   else:
    if not clear_footprint(r,site['building_kind'],site['x'],site['y'],site['id']):job['paused']='Clear troops from the construction footprint';continue
    entity(r,owner,site['building_kind'],site['x'],site['y']);site['restored']=True;owner['research_notice']='Restored '+site['building_kind']+' — facility captured for your army'
   engineer['reclaim_target']=None
 r['props']=[site for site in r.get('props',[]) if not site.get('restored')]

 # Collision is resolved before movement; no post-step pushes into neighbours.
 for passenger in r['entities']:
  if passenger.get('embarked') and not any(v['id']==passenger['embarked'] and v['hp']>0 for v in r['entities']):passenger['hp']=0
 for destroyed in [e for e in r['entities']+r['nodes']+r.get('props',[]) if e['hp']<=0 and not e.get('wrecked')]:
  if destroyed['kind']=='bridge':destroyed['wrecked']=True
  if destroyed['kind'] in FOOTPRINTS:
   r.setdefault('wrecks',[]).append(dict(id='wreck-'+destroyed['id'],kind='wreck',building_kind=destroyed['kind'],former_owner=destroyed['owner'],owner=None,x=destroyed['x'],y=destroyed['y'],design=destroyed.get('design','bastion'),facing=destroyed.get('facing',0),era_created=destroyed.get('era_created'),resource=('wood' if destroyed.get('era_created')=='stone' else 'iron' if destroyed.get('era_created') else 'metal'),stock=max(10,MATERIAL_COSTS[destroyed['kind']][0]*5),hp=1,maxhp=1,born=r['elapsed']))
  soldier=destroyed['kind'] in ['infantry','grenadier','marksman','medic','engineer','hacker'];structure=destroyed['kind'] in FOOTPRINTS;size=18 if soldier else 72 if structure else 40
  effect(r,'explosion',destroyed['x'],destroyed['y'],size=size,source=destroyed['kind'],design=destroyed.get('design','bastion'),era_created=destroyed.get('era_created'),facing=destroyed.get('facing',0),duration=1.6 if soldier else 3.2)
  if not soldier:
   deform(r,destroyed['x'],destroyed['y'],size*.65,depth=6 if structure else 3)
   if structure or destroyed['kind'] in ['tank','jeep','harvester','fighter','bomber','transport','gunboat','abandoned_car','road_business']:ignite(r,destroyed['x'],destroyed['y'],32 if structure else 20)
 r['craters']=r.get('craters',[])[-100:]
 replenish_deposits(r)
 r['nodes']=[n for n in r['nodes'] if n['hp']>0];r['props']=[prop for prop in r.get('props',[]) if prop['hp']>0 or prop['kind']=='bridge']
 r['entities']=[e for e in r['entities'] if e['hp']>0]
 r.pop('_occupancy',None);r.pop('_barrier_index',None);r.pop('_navigation_deadline',None)
 update_worker_activity(r)
 for p in r['players']:
  if not p.get('bot'):
   p['auto_idle']=False;p['autopilot']=False
  if p['alive'] and not any(e['owner']==p['id'] and e['kind'] in FOOTPRINTS for e in r['entities']):p['alive']=False
 r['entities']=[e for e in r['entities'] if player(r,e['owner'])['alive']]
 alive=[p for p in r['players'] if p['alive']];sides=set(('garrisons' if p.get('bot') else p['team'] if r['mode']=='teams' else p['id']) for p in alive)
 if len(sides)<=1:r['phase']='finished';r['winner']=('Frontier Forces' if alive[0].get('bot') else 'Team '+str(alive[0]['team']) if r['mode']=='teams' else alive[0]['name']) if alive else 'Draw'
EXPLORATION_CELL=100
def explored_cells(r,p):
 cells=r.setdefault('_explored',{}).setdefault(p['id'],set());cols=math.ceil(WORLD_W/EXPLORATION_CELL)
 for e in r['entities']:
  if e['hp']<=0 or not ally(r,p['id'],e['owner']):continue
  cx=int(e['x']//EXPLORATION_CELL);cy=int(e['y']//EXPLORATION_CELL);radius=sight_range(player(r,e['owner']),e);cells_radius=math.ceil(radius/EXPLORATION_CELL)
  for iy in range(max(0,cy-cells_radius),min(math.ceil(WORLD_H/EXPLORATION_CELL),cy+cells_radius+1)):
   for ix in range(max(0,cx-cells_radius),min(cols,cx+cells_radius+1)):
    if math.hypot((ix+.5)*EXPLORATION_CELL-e['x'],(iy+.5)*EXPLORATION_CELL-e['y'])<=radius:cells.add(iy*cols+ix)
 return sorted(cells)
def view(r,p):
 explored=explored_cells(r,p) if r['phase']!='lobby' else []
 v={k:x for k,x in r.items() if k!='players' and not k.startswith('_')};v['player_capacity']=player_capacity(r);v['explored_cells']=explored;v['exploration_cell']=EXPLORATION_CELL;v['grid_size']=GRID_SIZE;v['world_width']=WORLD_W;v['world_height']=WORLD_H;v['era_catalog']=[dict(key=e.key,title=e.title,costs=dict(e.costs),seconds=e.seconds,unlocks=e.unlocks) for e in era_rules.ERAS] if r.get('_experimental_history') else [];v['tech_catalog']={key:tech_for(p,key) for key in TECHS};v['cost_catalog']={kind:commander_costs(p,material_costs(kind,p)) for kind in MATERIAL_COSTS};v['lock_reasons']={kind:unlock_reason(p,kind) for kind in STATS};v['unlocks']=UNLOCKS;v['workers']=worker_summary(r,p);v['engineers']=engineer_summary(r,p);v['unlocks']={**UNLOCKS,**({'engineer':'engineering_basics'} if p.get('historical_shared') else {})};v['kind_eras']=dict(era_rules.KIND_ERAS) if p.get('historical_shared') else {};v['research_reasons']={key:research_reason(r,p,key) for key in TECHS} if r['phase']!='lobby' else {}; v['players']=[{**{k:x for k,x in q.items() if k not in ['token','account_user']},'storage_capacity':storage_capacity(r,q)} for q in r['players']]
 if r['phase']!='lobby':
  if r.get('_map_geometry')=='continental' and p.get('historical',{}).get('era')!='future':v['nodes']=[n for n in r['nodes'] if n['kind']!='riftglass']
  friends=[e for e in r['entities'] if ally(r,p['id'],e['owner'])];friend_index=CombatIndex(friends)
  vision=max((sight_range(player(r,f['owner']),f) for f in friends),default=280)
  def visible(o):return any(dist(o,f)<sight_range(player(r,f['owner']),f)+target_extent(o) for f in friend_index.nearby(o,vision+target_extent(o)))
  v['entities']=[{**{k:value for k,value in e.items() if not k.startswith('_')},'effective_attack_range':effective_attack_range(player(r,e['owner']),e),'acquisition_range':acquisition_range(player(r,e['owner']),e),**(dict(repair_coverage=engineer_repair_coverage(player(r,e['owner'])),repair_reach=ENGINEER_REPAIR_REACH) if e['kind']=='engineer' else {})} for e in r['entities'] if ally(r,p['id'],e['owner']) or visible(e)]
  v['fires']=[fire for fire in r.get('fires',[]) if visible(fire)]
  v['craters']=[mark for mark in r.get('craters',[]) if visible(mark)]
  v['effects']=[fx for fx in r.get('effects',[]) if visible(fx)]
  v['projectiles']=[shot for shot in r.get('projectiles',[]) if ally(r,p['id'],shot['owner']) or visible(shot)]
 return v
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def end_headers(self):
  self.send_header('Cache-Control','no-store, no-cache, must-revalidate');self.send_header('Pragma','no-cache');super().end_headers()
 @contextmanager
 def game_lock(self):
  try:
   with LOCK:
    self._defer_reply=True;self._pending_reply=None
    yield
  finally:
   self._defer_reply=False
   reply=getattr(self,'_pending_reply',None);self._pending_reply=None
   if reply:self.send_bytes(*reply)
 def send_bytes(self,b,code):
  try:
   self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(b)
  except (BrokenPipeError,ConnectionResetError):pass
 def send(self,obj,code=200):
  b=json.dumps(obj).encode()
  if getattr(self,'_defer_reply',False):self._pending_reply=(b,code)
  else:self.send_bytes(b,code)
 def send_video(self,path):
  size=path.stat().st_size;start=0;end=size-1;partial=False;header=self.headers.get('Range')
  if header:
   match=re.fullmatch(r'bytes=(\d*)-(\d*)',header.strip())
   if not match or not any(match.groups()):self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.end_headers();return
   first,last=match.groups()
   if first:start=int(first);end=min(size-1,int(last)) if last else size-1
   else:start=max(0,size-int(last))
   if start>=size or start>end:self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.end_headers();return
   partial=True
  self.send_response(206 if partial else 200);self.send_header('Content-Type','video/mp4');self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(end-start+1))
  if partial:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
  self.end_headers()
  try:
   with path.open('rb') as stream:
    stream.seek(start);remaining=end-start+1
    while remaining:
     block=stream.read(min(65536,remaining))
     if not block:break
     self.wfile.write(block);remaining-=len(block)
  except (BrokenPipeError,ConnectionResetError):pass
 def do_GET(self):
  request_path=urlparse(self.path).path
  if request_path=='/lobby-cinema.css':
   b=Path(__file__).with_name('lobby-cinema.css').read_bytes();self.send_response(200);self.send_header('Content-Type','text/css; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  historical_files={'era-barriers-painted-v78.png':'image/png','resources-painted-v78.png':'image/png','era-roads-painted-v78.png':'image/png','vehicle-industrial-hull.png':'image/png','vehicle-future-hull.png':'image/png','vehicle-industrial-turrets.png':'image/png','vehicle-future-turrets.png':'image/png','vehicle-industrial-jeep-steer.png':'image/png','vehicle-future-jeep-steer.png':'image/png','future-marksman-attack-directions.png':'image/png','industrial-infantry-attack-directions.png':'image/png','industrial-marksman-attack-directions.png':'image/png','industrial-grenadier-attack-directions.png':'image/png','future-infantry-attack-directions.png':'image/png','future-grenadier-attack-directions.png':'image/png','artisan-repair-directions.png':'image/png','industrial-engineer-repair-directions.png':'image/png','engineer-repair-directions.png':'image/png','era-bridges.png':'image/png','industrial-wrecks-a-directions.png':'image/png','industrial-wrecks-b-directions.png':'image/png','early-defense-wrecks-directions.png':'image/png','future-transport-directions.png':'image/png','future-gunboat-directions.png':'image/png','medieval-dock-directions.png':'image/png','industrial-infantry-directions.png':'image/png','industrial-marksman-directions.png':'image/png','industrial-grenadier-directions.png':'image/png','industrial-medic-directions.png':'image/png','industrial-engineer-directions.png':'image/png','industrial-harvester-directions.png':'image/png','industrial-jeep-directions.png':'image/png','industrial-scout-directions.png':'image/png','industrial-lancer-directions.png':'image/png','industrial-fighter-directions.png':'image/png','industrial-transport-directions.png':'image/png','industrial-gunboat-directions.png':'image/png','industrial-core-directions.png':'image/png','industrial-barracks-directions.png':'image/png','industrial-academy-directions.png':'image/png','industrial-warehouse-directions.png':'image/png','industrial-factory-directions.png':'image/png','industrial-power-directions.png':'image/png','industrial-airfield-directions.png':'image/png','industrial-dock-directions.png':'image/png','industrial-turret-directions.png':'image/png','industrial-armor-directions.png':'image/png','historical-masonry-wrecks-directions.png':'image/png','knight-directions.png':'image/png','historical-tower-directions.png':'image/png','sailing-transport-directions.png':'image/png','ballista-ship-directions.png':'image/png','artisan-directions.png':'image/png','healer-directions.png':'image/png','ancient-academy-directions.png':'image/png','medieval-academy-directions.png':'image/png','ancient-warehouse-directions.png':'image/png','medieval-warehouse-directions.png':'image/png','ancient-barracks-directions.png':'image/png','medieval-core-v2-directions.png':'image/png','medieval-barracks-directions.png':'image/png','ancient-core-v2-directions.png':'image/png','ancient-core-directions.png':'image/png','medieval-core-directions.png':'image/png','index.html':'text/html; charset=utf-8','README.md':'text/plain; charset=utf-8','academy-era-study.png':'image/png','barracks-era-study.png':'image/png','warehouse-era-study.png':'image/png','ancient-headquarters-study.png':'image/png','medieval-headquarters-study.png':'image/png','spearman-directions.png':'image/png','gatherer-directions.png':'image/png','archer-directions.png':'image/png','stone-core-directions.png':'image/png','stone-barracks-directions.png':'image/png','stone-wrecks-directions.png':'image/png','stone-warehouse-directions.png':'image/png','stone-academy-directions.png':'image/png','stone-services-wrecks-directions.png':'image/png','ancient-dock-directions.png':'image/png'}
  historical_files.update({role+'-attack-directions.png':'image/png' for role in ['spearman','archer','knight']})
  historical_name=request_path.removeprefix('/historical-designs/')
  if request_path.startswith('/historical-designs/') and historical_name in historical_files:
   path=Path(__file__).parent/'historical-designs'/historical_name
   if not path.is_file():self.send({'error':'Design file missing'},404);return
   b=path.read_bytes();self.send_response(200);self.send_header('Content-Type',historical_files[historical_name]);self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  if request_path=='/troop-combat-atlases.js':
   b=Path(__file__).with_name('troop-combat-atlases.js').read_bytes();self.send_response(200);self.send_header('Content-Type','text/javascript; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  if request_path in ['/responsive-runtime.js','/wall-artwork.js','/world-artwork.js','/lobby-cinema.js','/formations.js','/vehicle-motion.js','/vehicle-art-atlases.js']:
   b=Path(__file__).with_name(request_path[1:]).read_bytes();self.send_response(200);self.send_header('Content-Type','text/javascript; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  if request_path=='/troop-motion.js':
   b=Path(__file__).with_name('troop-motion.js').read_bytes();self.send_response(200);self.send_header('Content-Type','text/javascript; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  if request_path=='/historical-units.js':
   b=Path(__file__).with_name('historical-units.js').read_bytes();self.send_response(200);self.send_header('Content-Type','text/javascript; charset=utf-8');self.end_headers();self.wfile.write(b);return
  if request_path=='/historical-ui.js':
   b=Path(__file__).with_name('historical-ui.js').read_bytes();self.send_response(200);self.send_header('Content-Type','text/javascript; charset=utf-8');self.end_headers();self.wfile.write(b);return
  if urlparse(self.path).path=='/language.js':
   data=Path(__file__).with_name('language.js').read_bytes();self.send_response(200);self.send_header('Content-Type','text/javascript; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
  if re.fullmatch(r'/intro-(bastion|vesper|ironwatch|nightfall)\.mp4',urlparse(self.path).path):
   path=Path(__file__).with_name(urlparse(self.path).path[1:])
   if not path.exists():self.send({'error':'Introduction video is missing'},404);return
   self.send_video(path);return
  audio_path=urlparse(self.path).path
  if audio_path in ['/soundtrack-neon-foundry.wav','/soundtrack-pixel-rebellion.wav','/soundtrack-rift-drive.wav','/soundtrack-lobby.wav','/soundtrack-battle.wav','/soundtrack-frontier-dawn.wav','/soundtrack-after-the-dust.wav','/soundtrack-stone-and-steel.wav','/soundtrack-stormfront.wav','/soundtrack-iron-roads.wav','/soundtrack-last-citadel.wav']:
   b=Path(__file__).with_name(audio_path[1:]).read_bytes();self.send_response(200);self.send_header('Content-Type','audio/wav');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b);return
  if re.fullmatch(r'/directional-(warehouse|core|barracks|power|factory|academy|turret|solar|airfield|dock|wall|gate|harvester|tank|walker|jeep|scout|lancer|fighter|bomber|infantry|grenadier|marksman|medic|engineer|hacker)\.png',urlparse(self.path).path) or urlparse(self.path).path in ['/wall-vertical-sprites.png','/ships-sprites.png','/wreck-industrial-sprites.png','/wreck-infrastructure-sprites.png','/wreck-defenses-sprites.png','/combat-fx-sprites.png','/roadside-sprites.png','/cliffs-painted-sprites.png','/mine-sprites.png','/bridge-painted-sprites.png','/harvester-parts-sprites.png','/turret-complete-sprites.png','/lobby-wallpaper.png','/bastion-soldier.png','/bastion-atlas.png','/vesper-atlas.png','/ironwatch-atlas.png','/nightfall-atlas.png','/terrain-ground.png','/engineer-atlas.png','/hacker-atlas.png','/bastion-sprites.png','/vesper-sprites.png','/ironwatch-sprites.png','/nightfall-sprites.png','/engineer-sprites.png','/hacker-sprites.png','/barrier-sprites.png','/resources-approved-sprites.png','/harvester-empty-sprites.png','/turret-base-sprites.png']:
   b=Path(__file__).with_name(urlparse(self.path).path[1:]).read_bytes();self.send_response(200);self.send_header('Content-Type','image/png');self.end_headers();self.wfile.write(b);return
  if self.path=='/' or self.path.startswith('/?'):
   b=Path(__file__).with_name('index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(b);return
  try:
   q=parse_qs(urlparse(self.path).query)
   with self.game_lock():
    if urlparse(self.path).path=='/directory':
     account(self.headers.get('Authorization','').removeprefix('Bearer '));query=q.get('search',[''])[0].casefold()[:20]
     matches=[]
     for r in ROOMS.values():
      if r['phase'] not in ['lobby','intro','battle'] or not r['players']:continue
      if query and not any(query in p['name'].casefold() for p in r['players']):continue
      humans=[p for p in r['players'] if not p.get('bot')];matches.append(dict(room=r['code'],host=humans[0]['name'],players=[p['name'] for p in humans],mode=r['mode'],phase=r['phase'],full=len(humans)>=player_capacity(r),capacity=player_capacity(r)))
     self.send({'matches':matches});return
    room_code=q.get('room',[''])[0];token=q.get('token',[''])[0]
    r=ROOMS.get(room_code)
    p=next((p for p in r['players'] if token and p.get('token')==token),None) if r else None
    if p is None:self.send({'error':'Room or session not found','code':'invalid_session'},404);return
    if urlparse(self.path).path=='/share':self.send({**ONLINE_STATUS,'room':r['code']});return
    self.send(view(r,p))
  except Exception:
   # An internal state error must not invalidate a healthy client session.
   import traceback
   traceback.print_exc()
   self.send({'error':'Unable to update match. Please retry.','code':'state_unavailable'},500)
 def do_POST(self):
  try:
   assert int(self.headers.get('Content-Length',0))<16384
   d=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
   with self.game_lock():
    a=d['action']
    if a=='guest':
     self.send(guest(d.get('username','')));return
    if a=='logout':
     SESSIONS.pop(d.get('account'),None);self.send({'ok':True});return
    if a in ['create','join']:
     u=account(d.get('account'));chosen_faction=d.get('faction','Bastion');assert chosen_faction in ['Bastion','Vesper','Ironwatch','Nightfall'],'Choose an available faction'
     # Rejoin an existing seat instead of allocating a duplicate commander.
     for old in ROOMS.values():
      seat=next((p for p in old['players'] if p.get('account_user')==u['username']),None)
      if seat and old['phase'] in ['lobby','intro','battle']:
       if a=='join' and d.get('room')!=old['code']:raise AssertionError('Leave your current operation first')
       self.send(dict(room=old['code'],token=seat['token'],id=seat['id']));return
     if a=='create':
      code=secrets.token_hex(12);ROOMS[code]=dict(code=code,mode='ffa',phase='lobby',players=[],entities=[],nodes=[],elapsed=0,storm=-400,ai_enabled=True,difficulty='normal',weather_mode='dynamic',start_hour=6,map_preset='continental',_map_geometry='continental',_experimental_history=True);r=ROOMS[code]
     else:r=ROOMS[d['room']]
     humans=[q for q in r['players'] if not q.get('bot')];assert r['phase'] in ['lobby','intro','battle'] and len(humans)<player_capacity(r),'Match full or finished'
     if r['phase'] in ['intro','battle']:make_late_join_space(r)
     p=dict(id=secrets.token_hex(5),token=secrets.token_hex(20),name=u['display'],account_user=u['username'],team=min([1,2],key=lambda team:sum(q['team']==team for q in humans)),faction=chosen_faction,alive=True);r['players'].append(p)
     if r['phase'] in ['intro','battle']:
      occupied={q.get('spawn_slot') for q in humans};slot=next(i for i in range(player_capacity(r)) if i not in occupied);initialize_commander(r,p,slot)
     self.send(dict(room=r['code'],token=p['token'],id=p['id']));return
    r=ROOMS[d['room']];p=next(p for p in r['players'] if p.get('token')==d['token'])
    if a=='leave':
     assert r['phase'] not in ['intro','battle'],'Finish the match before leaving'
     r['players'].remove(p)
     if not r['players']:del ROOMS[r['code']]
     self.send({'ok':True});return
    command(r,p,d);self.send({'ok':True})
  except Exception as ex:self.send({'error':str(ex) or 'Invalid command'},400)

def loop():
 while True:
  time.sleep(.1)
  with LOCK:
   for r in ROOMS.values():tick(r,.1)
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=int(os.environ.get('PORT','3018')));parser.add_argument('--open-browser',action='store_true');parser.add_argument('--online',action='store_true');args,_=parser.parse_known_args()
 httpd=ThreadingHTTPServer(('0.0.0.0',args.port),Handler)
 url=f'http://localhost:{args.port}/?build=78'
 print(f'RIFTFALL v0.78: {url} — other devices use this computer LAN IP',flush=True)
 if args.open_browser:
  import webbrowser
  threading.Timer(.5,lambda:webbrowser.open(url)).start()
 tunnel=None
 if args.online:
  from online_tunnel import OnlineTunnel
  tunnel=OnlineTunnel(args.port,online_status);tunnel.start()
 threading.Thread(target=loop,daemon=True).start()
 try:httpd.serve_forever()
 except KeyboardInterrupt:pass
 finally:
  if tunnel:tunnel.stop()
  httpd.server_close()
