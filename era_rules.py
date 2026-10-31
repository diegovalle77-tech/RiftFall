"""Historical era progression and authoritative building/unit research gates."""
from dataclasses import dataclass
from math import isfinite
from typing import Mapping
RESOURCES=('food','wood','stone','gold','iron','riftglass')
FACTIONS=('Bastion','Vesper','Ironwatch','Nightfall')
@dataclass(frozen=True)
class Era:
 key:str
 title:str
 costs:Mapping[str,int]
 seconds:float
 unlocks:tuple[str,...]
ERAS=(Era('stone','Stone Age',{},0,('gatherer','spearman','camp','storage','watchtower')),Era('ancient','Ancient Age',{'food':250,'wood':150,'stone':100},30,('archer','stone_wall','sailing_dock')),Era('medieval','Medieval Age',{'food':400,'wood':250,'stone':250,'gold':100,'iron':100},45,('knight','fortress','warship')),Era('industrial','Industrial / Modern Age',{'food':500,'wood':350,'stone':300,'gold':250,'iron':300},60,('rifleman','factory','tank')),Era('future','Future Age',{'food':500,'wood':300,'stone':350,'gold':400,'iron':450},75,('riftglass','reactor','advanced_units')))
class EraError(ValueError):pass
def new_commander(faction):
 if faction not in FACTIONS:raise EraError('Unknown faction')
 return {'faction':faction,'era':'stone','era_job':None,'resources':{'food':200,'wood':200,'stone':150,'gold':0,'iron':0,'riftglass':0}}
def index_for(key):
 for i,era in enumerate(ERAS):
  if era.key==key:return i
 raise EraError('Unknown era')
def next_era(p):
 i=index_for(p['era'])+1
 return ERAS[i] if i<len(ERAS) else None
def begin_advance(p):
 if p.get('era_job') is not None:raise EraError('An era advance is already in progress')
 era=next_era(p)
 if not era:raise EraError('Already in the final era')
 for resource,cost in era.costs.items():
  if p['resources'].get(resource,0)<cost:raise EraError('Not enough '+resource)
 for resource,cost in era.costs.items():p['resources'][resource]-=cost
 p['era_job']={'target':era.key,'progress':0.0,'seconds':era.seconds};return p['era_job']
def advance_time(p,seconds,*,paused=False):
 if not isfinite(seconds) or seconds<0:raise EraError('Invalid elapsed time')
 job=p.get('era_job')
 if not job or paused:return False
 if next_era(p) is None or next_era(p).key!=job['target']:raise EraError('Era job does not follow the current era')
 job['progress']=min(job['seconds'],job['progress']+seconds)
 if job['progress']<job['seconds']:return False
 p['era']=job['target'];p['era_job']=None;return True
def available_unlocks(p):return {item for era in ERAS[:index_for(p['era'])+1] for item in era.unlocks}

# Existing combat sprites remain placeholders; these rules control availability.
KIND_ERAS={'knight':'medieval',
 'core':'stone','warehouse':'stone','barracks':'stone','academy':'stone','wall':'stone','harvester':'stone','infantry':'stone',
 'dock':'ancient','transport':'ancient','gate':'ancient','turret':'ancient','engineer':'stone','medic':'ancient',
 'gunboat':'medieval','marksman':'ancient',
 'power':'industrial','factory':'industrial','tank':'industrial','walker':'industrial','jeep':'industrial','scout':'industrial','grenadier':'industrial','lancer':'industrial','airfield':'industrial','fighter':'industrial',
 'solar':'future','hacker':'future','bomber':'future'}
ERA_ONLY_KINDS={'dock','transport','gate','turret','gunboat'}
TECH_ERAS={'fieldcraft':'ancient','industry':'industrial','armor':'industrial','aviation':'industrial','stormtech':'future','base_expansion':'medieval','logistics':'ancient','extraction':'ancient','warehousing':'medieval','infantry_drills':'ancient','combat_medicine':'medieval','composite_armor':'industrial','stabilizers':'industrial','fortifications':'medieval','targeting':'medieval','field_engineering':'medieval','aviation_engines':'industrial','electronic_warfare':'future',**{'storage_'+str(level):'ancient' if level==2 else 'medieval' if level==3 else 'industrial' if level==4 else 'future' for level in range(2,6)}}
TECH_ERAS.update({'engineering_basics':'stone','stone_tools':'stone','basic_drills':'stone','infantry_weapons':'ancient','field_armor':'ancient','cavalry_training':'medieval','naval_hulls':'medieval','naval_engines':'industrial','vehicle_weapons':'industrial','air_munitions':'industrial'})
TECH_OVERRIDES={
 'base_expansion':{'requires':['fieldcraft']},'logistics':{'requires':['fieldcraft']},
 'extraction':{'requires':['fieldcraft'],'facility':'academy'},
 'storage_2':{'requires':['fieldcraft']},
 'fortifications':{'requires':['fieldcraft'],'facility':'academy'},
 'targeting':{'requires':['fieldcraft'],'facility':'academy'},
 'field_engineering':{'requires':['fieldcraft']}}

def era_requirement(commander,required):
 return None if index_for(commander['era'])>=index_for(required) else 'Reach '+ERAS[index_for(required)].title

def kind_era_reason(commander,kind):return era_requirement(commander,KIND_ERAS.get(kind,'future'))
def tech_era_reason(commander,key):return era_requirement(commander,TECH_ERAS.get(key,'future'))

# Costs follow the equipment available at the time an order is placed.
# Entries replace an earlier recipe; they are not additive surcharges.
ERA_COST_OVERRIDES={
 'stone':{
  'core':{'wood':300,'stone':200},'wall':{'wood':15,'stone':5},
  'engineer':{'food':60,'wood':35,'stone':20}},
 'ancient':{
  'core':{'wood':350,'stone':300},'warehouse':{'wood':140,'stone':100},
  'barracks':{'wood':120,'stone':120},'academy':{'wood':160,'stone':160,'gold':30},
  'wall':{'stone':20,'wood':5},'gate':{'stone':45,'wood':35},
  'turret':{'stone':100,'wood':100,'gold':20},
  'engineer':{'food':65,'wood':40,'stone':25},'transport':{'wood':160,'gold':25}},
 'medieval':{
  'core':{'wood':400,'stone':400,'iron':100},'warehouse':{'wood':160,'stone':140,'iron':30},
  'barracks':{'wood':140,'stone':160,'iron':30},'academy':{'wood':180,'stone':200,'gold':60},
  'wall':{'stone':30,'wood':5},'gate':{'stone':60,'wood':40,'iron':20},
  'turret':{'stone':140,'wood':120,'iron':50},'engineer':{'food':70,'wood':40,'iron':30},
  'marksman':{'food':65,'wood':50,'gold':20}},
 'industrial':{
  'core':{'stone':450,'iron':300,'gold':100},'warehouse':{'stone':180,'iron':140},
  'barracks':{'stone':180,'iron':120},'academy':{'stone':240,'iron':180,'gold':100},
  'wall':{'stone':35,'iron':15},'gate':{'stone':70,'iron':60},
  'turret':{'stone':120,'iron':180,'gold':30},'dock':{'wood':100,'stone':200,'iron':160},
  'harvester':{'food':60,'iron':120,'gold':20},'infantry':{'food':50,'iron':40},
  'marksman':{'food':65,'iron':60,'gold':25},'medic':{'food':80,'iron':25,'gold':35},
  'engineer':{'food':70,'iron':60,'gold':20},'transport':{'iron':180,'gold':40},
  'gunboat':{'iron':260,'gold':70}},
 'future':{
  'core':{'stone':450,'iron':400,'riftglass':160},'warehouse':{'stone':180,'iron':200,'riftglass':50},
  'barracks':{'stone':180,'iron':180,'riftglass':40},'academy':{'stone':240,'iron':260,'riftglass':100},
  'wall':{'stone':35,'iron':25,'riftglass':10},'gate':{'stone':70,'iron':90,'riftglass':30},
  'turret':{'stone':120,'iron':220,'riftglass':80},'dock':{'stone':200,'iron':220,'riftglass':60},
  'harvester':{'food':60,'iron':160,'riftglass':40},'infantry':{'food':50,'iron':55,'riftglass':15},
  'marksman':{'food':65,'iron':80,'riftglass':30},'medic':{'food':80,'iron':40,'riftglass':30},
  'engineer':{'food':70,'iron':80,'riftglass':30},'transport':{'iron':240,'riftglass':60},
  'gunboat':{'iron':320,'riftglass':100},'power':{'stone':140,'iron':300,'riftglass':80},
  'factory':{'stone':200,'iron':400,'riftglass':100},'airfield':{'stone':250,'iron':480,'riftglass':120},
  'tank':{'iron':280,'riftglass':70},'jeep':{'iron':140,'riftglass':30},
  'scout':{'iron':120,'riftglass':25},'grenadier':{'food':60,'iron':65,'riftglass':25},
  'fighter':{'iron':320,'riftglass':100}}}

def equipment_costs(kind,era,base_costs):
 costs=dict(base_costs[kind])
 for age in ERAS[:index_for(era)+1]:
  if kind in ERA_COST_OVERRIDES.get(age.key,{}):costs=dict(ERA_COST_OVERRIDES[age.key][kind])
 return costs
