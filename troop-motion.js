// Whole-unit atlas bounds prevent clipped legs, barrels and neighboring-row fragments.
const troopBaseAtlasLayouts={"infantry":{"width":1262,"height":1246,"cells":[[65,8,236,302],[374,24,235,291],[644,24,238,291],[955,33,244,282],[60,324,255,289],[384,323,247,295],[648,318,242,299],[956,323,247,297],[65,615,228,290],[374,617,244,285],[653,625,238,278],[961,625,243,277],[51,908,251,305],[365,908,251,306],[645,914,259,301],[954,908,290,307]]},"marksman":{"width":1402,"height":1122,"cells":[[24,9,330,271],[375,10,325,270],[723,14,315,273],[1078,8,315,275],[7,288,370,266],[372,289,342,268],[715,290,324,281],[1068,287,329,277],[18,558,356,270],[396,558,314,270],[721,562,326,265],[1078,562,320,268],[9,817,357,282],[381,818,325,287],[726,825,313,282],[1072,826,324,279]]},"grenadier":{"width":1312,"height":1199,"cells":[[52,12,281,290],[383,22,262,289],[722,21,259,293],[1011,20,273,292],[55,310,283,297],[386,318,265,289],[715,310,269,304],[1011,310,274,308],[56,600,281,299],[382,607,270,297],[728,610,251,299],[1011,607,272,303],[42,900,296,292],[386,908,271,286],[714,911,268,283],[1005,909,270,285]]},"medic":{"width":1254,"height":1254,"cells":[[63,17,210,293],[384,18,206,281],[702,13,197,292],[999,8,199,302],[65,317,214,305],[382,319,211,297],[704,322,196,302],[996,320,206,304],[64,628,212,307],[384,629,209,296],[696,632,207,301],[1001,631,207,306],[66,939,212,302],[391,942,202,287],[706,939,196,299],[1006,942,197,300]]},"walker":{"width":1254,"height":1254,"cells":[[11,17,302,273],[334,13,298,280],[649,26,303,270],[967,23,280,268],[26,320,288,264],[336,316,290,267],[655,329,302,257],[977,324,275,260],[8,574,313,297],[341,590,301,281],[657,600,301,276],[977,604,276,267],[9,881,305,309],[333,881,300,311],[651,905,307,298],[966,900,287,290]]},"tank":{"width":1263,"height":1246,"cells":[[28,47,304,261],[343,49,302,261],[670,44,286,264],[973,59,277,255],[22,334,315,276],[350,335,310,273],[677,345,285,260],[980,345,272,265],[24,628,315,283],[351,634,318,273],[693,641,278,262],[986,651,265,252],[21,928,317,277],[345,927,324,274],[685,928,287,270],[981,936,272,266]]},"jeep":{"width":1254,"height":1254,"cells":[[14,29,289,272],[336,31,293,270],[646,36,279,255],[958,39,283,254],[12,326,295,273],[338,326,293,273],[647,335,288,258],[959,337,282,259],[12,631,295,277],[335,632,296,277],[641,653,295,251],[953,645,292,259],[13,937,296,278],[335,937,296,279],[643,953,289,251],[949,946,297,262]]},"scout":{"width":1254,"height":1254,"cells":[[28,55,271,250],[350,81,276,231],[662,101,250,214],[950,77,275,236],[27,387,279,209],[351,379,272,214],[651,404,274,186],[956,405,272,190],[31,649,272,256],[358,659,272,247],[667,659,260,246],[959,670,268,239],[25,962,280,224],[334,962,290,222],[654,994,287,185],[976,980,261,207]]},"lancer":{"width":1236,"height":1273,"cells":[[20,29,284,270],[320,28,297,276],[629,20,286,280],[929,30,292,281],[14,320,293,284],[319,320,295,283],[626,321,287,278],[929,312,290,301],[19,619,293,289],[321,616,297,293],[630,618,290,278],[930,636,294,291],[14,919,292,308],[316,927,304,301],[627,930,295,294],[927,934,296,309]]},"fighter":{"width":1402,"height":1122,"cells":[[17,39,297,214],[377,43,307,203],[728,54,299,192],[1085,55,297,195],[16,312,312,204],[371,309,319,206],[719,303,306,229],[1078,307,313,220],[19,560,307,222],[370,563,312,220],[728,584,296,215],[1076,595,304,202],[16,835,319,232],[374,842,314,222],[725,857,321,226],[1092,866,300,220]]},"bomber":{"width":1402,"height":1122,"cells":[[13,31,304,240],[354,35,310,234],[707,46,332,205],[1076,38,316,216],[13,305,306,236],[358,305,306,238],[701,319,334,204],[1073,309,319,215],[13,569,307,239],[354,571,316,238],[702,588,336,205],[1075,587,317,210],[14,828,305,250],[349,830,320,253],[704,847,345,215],[1076,852,318,213]]}};
/* Riftfall v0.76: distance-driven 2D motion. No gameplay stats are changed here. */
const troopMotionProfiles=Object.freeze({
 spear:{stride:36,pace:60,step:.034,swing:.065,brace:.026,recoil:.04},
 bow:{stride:34,pace:56,step:.029,swing:.045,brace:.032,recoil:.025},
 cavalry:{stride:72,pace:90,step:.042,swing:.045,brace:.025,recoil:.035},
 rifle:{stride:38,pace:65,step:.032,swing:.054,brace:.03,recoil:.045},
 precision:{stride:34,pace:56,step:.025,swing:.035,brace:.045,recoil:.06},
 thrower:{stride:36,pace:60,step:.03,swing:.045,brace:.025,recoil:.035},
 healer:{stride:30,pace:60,step:.03,swing:.05,brace:.02,recoil:0},
 artisan:{stride:30,pace:58,step:.028,swing:.05,brace:.02,recoil:0},
 hacker:{stride:32,pace:60,step:.028,swing:.045,brace:.025,recoil:0},
 gatherer:{stride:32,pace:55,step:.025,swing:.04,brace:.02,recoil:0},
 walker:{stride:62,pace:68,step:.04,swing:.04,brace:.025,recoil:.042},
 armor:{stride:55,pace:55,step:.01,swing:.015,brace:.014,recoil:.055},
 vehicle:{stride:48,pace:90,step:.012,swing:.015,brace:.012,recoil:.032},
 launcher:{stride:52,pace:50,step:.009,swing:.012,brace:.02,recoil:.065},
 vessel:{stride:82,pace:60,step:.008,swing:.014,brace:.013,recoil:.035},
 aircraft:{stride:120,pace:140,step:.009,swing:.02,brace:.018,recoil:.035},
 collector:{stride:48,pace:60,step:.012,swing:.015,brace:.01,recoil:0}
});
function troopMotionRole(e){
 const role=e.historical_role;
 if(role==='spearman')return 'spear';if(role==='archer')return 'bow';if(e.kind==='knight')return 'cavalry';
 if(e.kind==='harvester')return role==='gatherer'?'gatherer':'collector';
 if(e.kind==='engineer')return 'artisan';if(e.kind==='medic')return 'healer';if(e.kind==='hacker')return 'hacker';
 if(e.kind==='infantry')return 'rifle';if(e.kind==='marksman')return 'precision';if(e.kind==='grenadier')return 'thrower';
 if(e.kind==='walker')return role==='industrial_armor'?'armor':'walker';if(e.kind==='tank')return 'armor';
 if(e.kind==='lancer')return 'launcher';if(['jeep','scout'].includes(e.kind))return 'vehicle';
 if(['transport','gunboat'].includes(e.kind))return 'vessel';if(['fighter','bomber'].includes(e.kind))return 'aircraft';return null;
}
function troopCombatPose(e,time){
 const now=(state?.elapsed||0)+Math.min(.5,Math.max(0,time-(pollTime||time*1000)/1000));
 const cycle=e.attack_cycle||(e.historical_role==='archer'?1.8:e.kind==='grenadier'?3:1.2);
 const age=e.attack_started==null?(e.engaged?Math.max(0,cycle-(e.cool??cycle)):100):Math.max(0,now-e.attack_started);
 const active=!!e.engaged||age<Math.min(.65,cycle),phase=Math.min(1,age/cycle),role=e.historical_role||e.kind;
 const recoil=active?Math.max(0,1-age/.24)**1.4:0;
 const thrust=active?Math.sin(Math.min(1,age/.72)*Math.PI):0;
 const draw=active&&role==='archer'?Math.max(0,Math.min(1,(age-.3)/Math.max(.3,cycle-.35))):0;
 const windup=active&&e.engaged?Math.max(0,(phase-.72)/.28):0;
 const hitAge=e.last_hit_at==null?100:Math.max(0,now-e.last_hit_at),hit=Math.max(0,1-hitAge/.42);
 return {active,age,phase,recoil,thrust,draw,windup,hit,hitAge,role,angle:e.turret_angle??e.angle??0};
}
function troopMotionPose(e,time){
 const role=troopMotionRole(e),profile=troopMotionProfiles[role];if(!profile)return null;
 const combat=combatPose(e,time),seed=String(e.id||e.kind).split('').reduce((a,c)=>a+c.charCodeAt(0),0)*.173;
 const distance=e.visualTravel??e.travel,travel=Number.isFinite(distance)?distance:time*profile.pace*(e.running===false?.62:1);
 const gait=travel/profile.stride*Math.PI*2+seed,work=!!(e.repairing||e.rebuilding||e.harvesting||e.healing_target||e.hacking);
 const walk=Math.max(0,Math.min(1,e.walk_blend??(e.moving?1:0)));
 const guard=walk<.2&&!work&&(e.engaged||e.combat_target_id||combat.hit>0);
 return {role,profile,combat,gait,seed,work,guard,walk,breath:Math.sin(time*2.1+seed),workStroke:Math.sin(time*(role==='healer'?4:role==='hacker'?9:6.5)+seed)};
}
function troopMotionVertex(u,v,e,time){
 const pose=e._motionPose||troopMotionPose(e,time);if(!pose)return {x:u,y:v};
 const {role,profile,combat,gait,seed,guard,walk,breath,workStroke}=pose;
 const side=u<.5?-1:1,upper=Math.max(0,1-v),leg=Math.max(0,(v-.57)/.43),knee=Math.sin(leg*Math.PI);
 const arm=Math.max(0,1-Math.abs(v-.39)/.3)*Math.max(0,(Math.abs(u-.5)-.12)/.38),chest=Math.sin(Math.max(0,Math.min(1,v))*Math.PI);
 const gaitStep=Math.sin(gait+side*Math.PI/2),dxAim=Math.cos(combat.angle),dyAim=Math.sin(combat.angle);
 let dx=0,dy=0;
 const person=['spear','bow','rifle','precision','thrower','healer','artisan','hacker','walker'].includes(role);
 if(person){
  if(walk>.001){dx+=(leg*gaitStep*profile.swing+knee*gaitStep*.023-arm*gaitStep*.035)*walk;dy-=Math.max(0,-gaitStep)*leg*profile.step*walk;dy+=arm*gaitStep*.032*walk;dx+=upper*Math.sin(gait*2)*.006*walk;dy-=chest*Math.abs(Math.sin(gait))*.007*walk}
  else{dx+=arm*breath*.006;dy-=chest*breath*.004}
  if(guard){dx+=dxAim*upper*profile.brace+side*arm*.014;dy+=chest*profile.brace*.48;dy-=arm*(role==='spear'?.04:.012);dx-=side*knee*profile.brace*.35}
  if(combat.active){
   if(role==='spear'){const jab=combat.thrust*.095-combat.windup*.025;dx+=dxAim*jab*(upper+arm*.6);dy+=dyAim*jab*upper*.55;dy+=chest*combat.thrust*.008}
   else if(role==='bow'){dx-=side*arm*combat.draw*.085;dx+=dxAim*(combat.recoil*.028-combat.draw*.02)*upper;dy-=arm*combat.draw*.025}
   else if(role==='thrower'){
    const throwing=e.era_created==='industrial',throwArc=Math.sin(Math.min(1,combat.age/.62)*Math.PI),push=throwing?throwArc*.12:-combat.recoil*profile.recoil;
    dx+=dxAim*push*(upper+arm*.35);dy-=arm*(throwing?throwArc*.1:combat.recoil*.025);dy+=chest*combat.windup*.018;
   }else{dx-=dxAim*combat.recoil*profile.recoil*(upper+arm*.8);dy-=dyAim*combat.recoil*profile.recoil*upper*.55;dy+=arm*combat.windup*.015}
  }
  if(role==='artisan'&&pose.work){dx+=arm*workStroke*.075+upper*Math.sin(time*3.25+seed)*.009;dy-=arm*Math.max(0,workStroke)*.07;dy+=chest*.01}
  if(role==='healer'&&e.healing_target){dx+=arm*(.035+workStroke*.025);dy-=arm*(.025+Math.max(0,workStroke)*.035);dy+=chest*.012}
  if(role==='hacker'&&e.hacking){dx+=arm*workStroke*.024;dy-=arm*(.025+Math.cos(time*7+seed)*.012);dy+=chest*.01}
 }else if(role==='cavalry'){
  const hoof=Math.max(0,(v-.57)/.43),beat=Math.sin(gait+u*10);
  if(walk>.001){dx+=hoof*beat*.06*walk;dy-=hoof*Math.max(0,beat)*.045*walk;dy-=chest*Math.abs(Math.sin(gait))*.012*walk;dx+=upper*Math.sin(gait)*.009*walk}else dy-=chest*breath*.004;
  if(combat.active){dx+=dxAim*(combat.thrust*.08-combat.windup*.025)*upper;dy+=chest*combat.thrust*.012}if(guard)dx+=dxAim*upper*.018;
 }else if(role==='gatherer'){
  const view=typeof historicalView==='function'?historicalView(e):0,body=Math.max(0,Math.min(1,([1,3].includes(view)?u-.38:.62-u)/.3));
  if(walk>.001){dx+=Math.sin(gait+side*Math.PI/2)*leg*.052*body*walk;dy-=Math.max(0,-Math.sin(gait+side*Math.PI/2))*leg*.025*body*walk;dy+=chest*Math.sin(gait)*.004*body*walk}
  if(e.harvesting){dx+=body*upper*workStroke*.04;dy-=body*chest*Math.max(0,workStroke)*.027}
 }else{
  if(e.moving){const ground=e.terrain||{},roll=Math.sin(gait+u*7);dy+=Math.max(0,(v-.5)*2)*roll*Math.min(.018,.004+(ground.rough||0)*.002);dy+=(u-.5)*(ground.pitch||0)*.28*chest}
  if(role==='vessel'){const sail=e.historical_role==='sailing_transport'||e.historical_role==='ballista_ship';dx+=Math.sin(time*1.9+seed)*upper*(sail?.013:.006);dy+=Math.sin(time*1.4+seed)*chest*.005}
  if(role==='aircraft'){dy+=Math.sin(time*1.8+seed)*(u-.5)*.024;dx+=Math.sin(time*1.1+seed)*upper*.008}
  if(combat.active){dx-=dxAim*combat.recoil*profile.recoil*upper;dy-=dyAim*combat.recoil*profile.recoil*upper*.6;if(role==='launcher')dy+=chest*combat.windup*.013}
  if(role==='collector'&&e.harvesting){const crane=Math.max(0,1-v/.58);dx+=Math.sin(time*2.1+u*2)*crane*.023;dy+=Math.cos(time*2.1+u*3)*crane*.019}
 }
 // A short upper-body hit reaction and recovery: planted feet never jump or slide.
 if(combat.hit>0){const impact=Math.sin(Math.min(1,combat.hitAge/.42)*Math.PI)*combat.hit;dx+=Math.cos(e.hit_angle||0)*impact*upper*(person?.055:.025);dy+=chest*impact*(person?.025:.009)}
 if(person&&e.terrain)dy+=(u-.5)*(e.terrain.roll||0)*.15*v*(1-v);
 return {x:u+Math.max(-.16,Math.min(.16,dx)),y:v+Math.max(-.12,Math.min(.12,dy))};
}
function drawTroopMotionDetails(e,bounds,y,time){
 const pose=e._motionPose||troopMotionPose(e,time);if(!pose)return;const {role,combat,gait}=pose,w=bounds.width,h=bounds.height,ground=bounds.bottom-e.y;
 if(e.moving&&['spear','bow','rifle','precision','thrower','healer','artisan','hacker','cavalry'].includes(role)){
  ctx.save();const surface=e.terrain?.surface;ctx.fillStyle=surface==='snow'?'#e3ebe477':surface==='mud'?'#69523e77':'#baa67c44';const step=(gait/(Math.PI*2)%1+1)%1;
  for(const side of [-1,1]){const p=(step+(side>0?.5:0))%1;if(p>.42)continue;ctx.globalAlpha=(1-p/.42)*.35;ctx.beginPath();ctx.ellipse(side*w*.15-Math.cos(e.angle||0)*p*10,ground+p*2,1+p*5,.6+p*2,0,0,Math.PI*2);ctx.fill()}ctx.restore();
 }
 if(role==='healer'&&e.healing_target){ctx.save();ctx.strokeStyle='#bce6ab';ctx.lineWidth=1.2;const side=Math.cos(e.angle||0)<0?-1:1,handX=side*w*.22,handY=y+h*.46,p=(time*1.3)%1;ctx.globalAlpha=(1-p)*.75;ctx.beginPath();ctx.arc(handX,handY,2+p*5,0,Math.PI*2);ctx.stroke();ctx.restore()}
 if(role==='hacker'&&e.hacking){ctx.save();ctx.fillStyle='#b9b3ed';for(let i=0;i<3;i++)if(Math.sin(time*9+i)>0)ctx.fillRect(-w*.18+i*3,y+h*.43,1.8,1.3);ctx.restore()}
 if(['rifle','precision'].includes(role)&&e.era_created==='industrial'&&combat.age<.35&&combat.active){const side=Math.cos(e.angle||0)<0?-1:1,p=combat.age/.35;ctx.save();ctx.translate(side*(w*.15+p*8),y+h*.45+p*p*8);ctx.rotate(p*7);ctx.fillStyle='#c6b378';ctx.fillRect(-1,-.5,2.5,1);ctx.restore()}
}
function troopMuzzlePoint(e){
 const bounds=spriteBounds(e),role=troopMotionRole(e),angle=e.turret_angle??e.angle??0;
 if(!['rifle','precision','thrower','spear','bow'].includes(role))return{x:e.x+Math.cos(angle)*16,y:e.y+Math.sin(angle)*16-12};
 const period=e.era_created==='industrial'?'industrial':'future',column=period==='industrial'?historicalView(e):directionIndex(e),side=[0,1].includes(column)?1:-1;
 return{x:e.x+side*bounds.width*.46,y:bounds.top+bounds.height*(role==='precision'?.28:period==='industrial'?.23:.35)};
}
function drawTroopMuzzle(fx,age){
 const e=fx.source_id&&state?.entities?.find(e=>e.id===fx.source_id);if(!e||!humanKinds.has(e.kind))return false;
 const point=troopMuzzlePoint(e),angle=Math.atan2(fx.ty-point.y,fx.tx-point.x),fade=Math.max(0,1-age/.25);ctx.save();ctx.translate(point.x,point.y);ctx.rotate(angle);ctx.globalAlpha=fade;
 const art=effectFrame(3,5);if(art)drawEffectSprite(art,4,3,13,8,fade);else{ctx.fillStyle=e.era_created==='industrial'?'#f7da9c':'#b4e8ec';ctx.beginPath();ctx.moveTo(0,-2);ctx.lineTo(9*fade,-4*fade);ctx.lineTo(5*fade,0);ctx.lineTo(10*fade,3*fade);ctx.lineTo(0,2);ctx.closePath();ctx.fill()}ctx.restore();return true;
}
