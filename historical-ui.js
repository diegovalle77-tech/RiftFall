/* Era-aware terrain, progression controls and runtime artwork previews. */
let historicalTerrainKey='frontier',historicalPanelKey='';
function continentalWaterAt(map,x,y){
 if(x<0||y<0||x>WORLD_W||y>WORLD_H)return true;
 if(map.islands.some(i=>((x-i.x)/i.rx)**2+((y-i.y)/i.ry)**2<=1))return false;
 const c=map.coast,s=map.sea,ch=map.channel;
 return x<c||x>WORLD_W-c||y<c||y>WORLD_H-c||((x-s.x)/s.rx)**2+((y-s.y)/s.ry)**2<1||x>=ch.left&&y>ch.top&&y<ch.bottom;
}
function paintContinentalTerrain(g,map){
 const c=map.coast/4,w=WORLD_W/4,h=WORLD_H/4,s=map.sea,ch=map.channel;
 g.save();g.fillStyle='#355f65';g.fillRect(0,0,w,c);g.fillRect(0,h-c,w,c);g.fillRect(0,0,c,h);g.fillRect(w-c,0,c,h);
 g.strokeStyle='#c4b17c';g.lineWidth=9;g.strokeRect(c+4.5,c+4.5,w-2*c-9,h-2*c-9);
 g.fillStyle='#355f65';g.fillRect(ch.left/4,ch.top/4,w-ch.left/4,(ch.bottom-ch.top)/4);
 g.beginPath();g.ellipse(s.x/4,s.y/4,s.rx/4,s.ry/4,0,0,Math.PI*2);g.fill();g.strokeStyle='#b8a679';g.lineWidth=7;g.stroke();
 // Restore the channel over the eastern lake shore; no false land barrier.
 g.fillRect((s.x+s.rx-130)/4,ch.top/4,(WORLD_W-s.x-s.rx+130)/4,(ch.bottom-ch.top)/4);
 for(const i of map.islands){g.fillStyle='#718055';g.strokeStyle='#c8b783';g.lineWidth=8;g.beginPath();g.ellipse(i.x/4,i.y/4,i.rx/4,i.ry/4,0,0,Math.PI*2);g.fill();g.stroke();g.fillStyle='#abb37a66';for(let n=0;n<50;n++){const a=n*2.399,r=Math.sqrt((n+.5)/50)*.85;g.fillRect((i.x+Math.cos(a)*i.rx*r)/4,(i.y+Math.sin(a)*i.ry*r)/4,1.6,1)}}
 g.restore();
}
function animateContinentalWater(now,view){
 const step=140;ctx.save();ctx.strokeStyle='#c0e1d449';ctx.lineWidth=1;
 for(let y=Math.floor(camera.y/step)*step;y<camera.y+view.h;y+=step)for(let x=Math.floor(camera.x/step)*step;x<camera.x+view.w;x+=step){const px=x+Math.sin(y*.019)*30,py=y+Math.sin(now*.0007+x*.01)*5;if(!waterAt(px,py)||!waterAt(px+25,py))continue;ctx.beginPath();ctx.moveTo(px,py);ctx.quadraticCurveTo(px+12,py+4,px+25,py);ctx.stroke()}ctx.restore();
}
const resourceArt2D=new Map();
function resourceDepositArt(kind,depleted=false,mine=false){
 const painted=paintedResourceFrame(kind,depleted);if(painted)return painted;
 const key=kind+':'+depleted+':'+mine;if(resourceArt2D.has(key))return resourceArt2D.get(key);
 const art=document.createElement('canvas');art.width=180;art.height=140;const g=art.getContext('2d');g.translate(90,95);
 const ore={stone:['#777b6d','#b3b4a0','#d2cfb5'],gold:['#716344','#bb9147','#edcd72'],iron:['#5d6761','#8c9e97','#b3c4b7'],metal:['#5d6761','#8c9e97','#b3c4b7'],riftglass:['#68567d','#9b7db7','#d5b3e4']}[kind],flora=['wood','food'].includes(kind);
 function poly(points,fill,stroke){g.fillStyle=fill;g.beginPath();points.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.closePath();g.fill();if(stroke){g.strokeStyle=stroke;g.lineWidth=1.4;g.stroke()}}
 // Irregular soil edges and stippled brushwork sit directly on the map plane.
 poly([[-77,-19],[-68,-52],[-42,-69],[-9,-76],[22,-70],[53,-54],[74,-29],[70,-4],[43,21],[9,30],[-29,23],[-58,8]],flora?'#53613c66':'#82704c88');
 for(let i=0;i<85;i++){const a=i*2.399,r=12+Math.sqrt(i/85)*62,x=Math.cos(a)*r,y=-23+Math.sin(a)*r*.64;g.fillStyle=['#ac985f55','#544c3766','#9b9b6344'][i%3];g.fillRect(x,y,1+i%3,1+i%2)}
 const count=depleted?5:13;
 for(let i=0;i<count;i++){const a=i*2.399,r=9+Math.sqrt(i)*13,x=Math.cos(a)*r,y=-28+Math.sin(a)*r*.62,sz=10+(i*7)%13;
  if(flora){
   if(kind==='wood'){g.save();g.translate(x,y);g.rotate(a);g.strokeStyle='#433e2c';g.lineWidth=9;g.beginPath();g.moveTo(-12,1);g.lineTo(14,1);g.stroke();g.strokeStyle='#a28851';g.lineWidth=5;g.stroke();g.strokeStyle='#d0b77a';g.lineWidth=1;g.beginPath();g.moveTo(-10,-1);g.lineTo(12,-1);g.stroke();g.restore()}
   for(let j=0;j<5;j++){const px=x+Math.cos(j*1.257)*sz*.5,py=y+Math.sin(j*1.257)*sz*.5;g.fillStyle=['#334b30','#4b6439','#69814a'][j%3];g.beginPath();g.arc(px,py,sz*.67,0,Math.PI*2);g.fill();g.strokeStyle='#86925455';g.lineWidth=1;g.beginPath();g.arc(px-2,py-2,sz*.45,3.3,5.7);g.stroke()}
   if(kind==='food')for(let j=0;j<5;j++){g.fillStyle=j%2?'#cb6b52':'#923e3b';g.beginPath();g.arc(x+Math.cos(j*2.1)*sz*.65,y+Math.sin(j*2.1)*sz*.65,2.6,0,Math.PI*2);g.fill()}
  }else{
   poly([[x-sz,y-3],[x-sz*.7,y-sz*.65],[x+sz*.35,y-sz*.8],[x+sz,y-2],[x+sz*.5,y+sz*.6],[x-sz*.6,y+sz*.5]],ore[i%2], '#444c3c');
   // Mineral veins and broken surface contours, without extruded sides or cast shadows.
   g.strokeStyle=ore[2];g.lineWidth=kind==='gold'?2.5:1.3;g.beginPath();g.moveTo(x-sz*.65,y+sz*.25);g.lineTo(x-sz*.2,y-sz*.2);g.lineTo(x+sz*.15,y);g.lineTo(x+sz*.55,y-sz*.45);g.stroke();g.strokeStyle=ore[0];g.lineWidth=1;g.beginPath();g.moveTo(x+sz*.2,y+sz*.45);g.lineTo(x+sz*.1,y+sz*.1);g.lineTo(x+sz*.5,y-sz*.1);g.stroke();
   if(kind==='gold'||kind==='riftglass'){g.fillStyle=ore[2];for(let j=0;j<3;j++)g.fillRect(x-5+j*5,y-6+(j%2)*5,2.5,2)}
  }
 }
 if(mine&&!flora){poly([[-20,-42],[20,-42],[23,-12],[-22,-12]],'#293b32','#9a895d');g.strokeStyle='#b39b68';g.lineWidth=4;g.strokeRect(-24,-46,48,37);g.strokeStyle='#5b655c';g.lineWidth=2;for(const x of [-12,12]){g.beginPath();g.moveTo(x,-8);g.lineTo(x,28);g.stroke()}for(let y=-3;y<28;y+=8){g.strokeStyle='#8c7954';g.lineWidth=3;g.beginPath();g.moveTo(-16,y);g.lineTo(16,y);g.stroke()}}
 resourceArt2D.set(key,art);return art;
}
function drawHistoricalResource(n,time){
 const kind=n.kind||'metal',capacity=n.max_stock||(['iron','metal'].includes(kind)?250000:40000),depleted=n.stock<capacity*.18,mine=n.site==='mine',art=resourceDepositArt(kind,depleted,mine);ctx.save();ctx.translate(n.x,n.y);ctx.drawImage(art,-90,-95,180,140);

 if(mine&&(n.parking_spots||[]).some(spot=>(state.entities||[]).some(e=>e.kind==='harvester'&&e.harvesting&&Math.hypot(e.x-spot.x,e.y-spot.y)<30))){ctx.strokeStyle='#c7b78a';ctx.lineWidth=1.5;for(let i=0;i<3;i++){const t=(time*2+i*.33)%1;ctx.beginPath();ctx.moveTo(-10+t*20,-22);ctx.lineTo(-10+t*20,-27);ctx.stroke()}}
 if(inspectedMapId===n.id){ctx.strokeStyle='#c6f3dc';ctx.lineWidth=1.5;ctx.strokeRect(-86,-88,172,130);ctx.fillStyle='#10222af2';ctx.fillRect(-95,49,190,23);ctx.fillStyle='#e4f2e9';ctx.font='11px system-ui';ctx.textAlign='center';ctx.fillText(Math.max(0,Math.floor(n.stock)).toLocaleString()+' '+(kind==='metal'?'iron':kind)+' remaining',0,65)}ctx.restore();
}

function visibleGatherResources(){const h=me()?.historical;return h?['auto','food','wood','stone','gold','iron',...(h.era==='future'?['riftglass']:[])]:['auto','metal','riftglass','wood']}
function syncHistoricalMatch(){
 const continental=state?.map_geometry?.kind==='continental',key=continental?state.code+':continental:'+currentRoadEra():'frontier';
 if(key!==historicalTerrainKey){historicalTerrainKey=key;terrainBuild();riverDetailTexture=null;groundWeatherTextures=null;focused=false}
 if($('mapPreset')){$('mapPreset').value=state.map_preset||'frontier';$('mapPreset').disabled=state.players[0]?.id!==session.id;$('historicalLobbyNote').hidden=state.map_preset!=='continental'}
 if(state.phase==='lobby'||state.phase==='intro')return;
 updateHistoricalPanel();
 const tools=$('gatherTools'),historical=!!me().historical;
 if(tools.dataset.historical!==String(historical)+':'+(me().historical?.era||'')){tools.dataset.historical=String(historical)+':'+(me().historical?.era||'');tools.replaceChildren();const title=document.createElement('small');title.textContent=historical?'Gather:':'Gather:';tools.append(title);for(const resource of visibleGatherResources()){const b=document.createElement('button');b.textContent=resource[0].toUpperCase()+resource.slice(1);b.onclick=()=>gather(resource);tools.append(b)}}
}
function updateHistoricalPanel(){
 const panel=$('eraPanel'),p=me(),h=p?.historical,b=selectedBuilding();panel.hidden=!h||!b||!['core','academy','barracks','warehouse','dock'].includes(b.kind);if(panel.hidden){historicalPanelKey='';return}
 const key=JSON.stringify([b.id,b.kind,p.faction,h,Math.ceil(b.hp),b.facing||0,buildingUnderConstruction(b)]);if(key===historicalPanelKey)return;historicalPanelKey=key;panel.replaceChildren();
 const eras=state.era_catalog||[],index=eras.findIndex(e=>e.key===h.era),era=eras[index],next=eras[index+1];const title=document.createElement('h3');title.textContent=era?.title||h.era;panel.append(title);
 const bank=document.createElement('p');bank.textContent='Supplies · '+Object.entries(h.resources).filter(([k])=>k!=='riftglass'||h.era==='future').map(([k,v])=>Math.floor(v).toLocaleString()+' '+k).join(' · ');panel.append(bank);
 if(isIndustrialBuilding(b)||historicalCoreEra(b)||isHistoricalAncientDock(b)||isHistoricalStoneBuilding(b)||['academy','barracks','warehouse'].includes(b.kind)){const picture=document.createElement('div');picture.className='historicalArtPreview';const row=['Bastion','Vesper','Ironwatch','Nightfall'].indexOf(p.faction);if(isIndustrialBuilding(b)){picture.style.backgroundImage='url(/historical-designs/industrial-'+b.kind+'-directions.png)';picture.style.backgroundSize='400% 400%';picture.style.backgroundPosition=(directionIndex(b)*100/3)+'% '+(row*100/3)+'%';picture.setAttribute('aria-label',p.faction+' Industrial '+b.kind+' as currently positioned')}else if(historicalAcademyEra(b)){picture.style.backgroundImage='url(/historical-designs/'+historicalAcademyEra(b)+'-academy-directions.png)';picture.style.backgroundSize='400% 400%';picture.style.backgroundPosition=(directionIndex(b)*100/3)+'% '+(row*100/3)+'%';picture.setAttribute('aria-label',p.faction+' '+historicalAcademyEra(b)+' academy as currently positioned')}else if(historicalWarehouseEra(b)){picture.style.backgroundImage='url(/historical-designs/'+historicalWarehouseEra(b)+'-warehouse-directions.png)';picture.style.backgroundSize='400% 400%';picture.style.backgroundPosition=(directionIndex(b)*100/3)+'% '+(row*100/3)+'%';picture.setAttribute('aria-label',p.faction+' '+historicalWarehouseEra(b)+' warehouse as currently positioned')}else if(isAncientBarracks(b)||isMedievalBarracks(b)){picture.style.backgroundImage='url(/historical-designs/'+b.era_created+'-barracks-directions.png)';picture.style.backgroundSize='400% 400%';picture.style.backgroundPosition=(directionIndex(b)*100/3)+'% '+(row*100/3)+'%';picture.setAttribute('aria-label',p.faction+' Medieval barracks as currently positioned')}else if(historicalCoreEra(b)){picture.style.backgroundImage='url(/historical-designs/'+historicalCoreEra(b)+'-core'+'-v2'+'-directions.png)';picture.style.backgroundSize='400% 400%';picture.style.backgroundPosition=(directionIndex(b)*100/3)+'% '+(historicalCoreRow(historicalCoreEra(b),p.faction.toLowerCase())*100/3)+'%';picture.setAttribute('aria-label',p.faction+' '+historicalCoreEra(b)+' headquarters as currently positioned')}else if(isHistoricalAncientDock(b)){picture.style.backgroundImage='url(/historical-designs/'+historicalDockEra(b)+'-dock-directions.png)';picture.style.backgroundSize='400% 400%';picture.style.backgroundPosition=(directionIndex(b)*100/3)+'% '+(row*100/3)+'%';picture.setAttribute('aria-label',p.faction+' Ancient Age dock as currently positioned')}else if(isHistoricalStoneBuilding(b)){picture.style.backgroundImage='url(/historical-designs/stone-'+b.kind+'-directions.png)';picture.style.backgroundSize='400% 400%';picture.style.backgroundPosition=(directionIndex(b)*100/3)+'% '+(row*100/3)+'%';picture.setAttribute('aria-label',p.faction+' Stone Age '+b.kind+' as currently positioned')}else{picture.style.backgroundImage='url(/directional-'+b.kind+'.png)';picture.style.backgroundSize='400% 400%';picture.style.backgroundPosition=(directionIndex(b)*100/3)+'% '+(row*100/3)+'%';picture.setAttribute('aria-label',p.faction+' Future '+b.kind+' as currently positioned')}picture.setAttribute('role','img');panel.append(picture)}
 if(['core','academy'].includes(b.kind)&&!buildingUnderConstruction(b)){if(h.era_job){const job=h.era_job,progress=document.createElement('progress');progress.max=job.seconds;progress.value=job.progress;const label=document.createElement('p');label.textContent='Advancing · '+Math.ceil(job.seconds-job.progress)+'s remaining · requires a completed command center';panel.append(label,progress)}else if(next){const costs=document.createElement('p');costs.textContent=Object.entries(next.costs).map(([r,n])=>n+' '+r).join(' · ')+' · '+next.seconds+'s';const button=document.createElement('button');button.textContent='Advance to '+next.title;button.disabled=Object.entries(next.costs).some(([r,n])=>h.resources[r]<n)||!state.entities.some(e=>e.owner===p.id&&e.kind==='core'&&e.hp>0&&!buildingUnderConstruction(e));button.onclick=()=>act('advance_era');panel.append(costs,button)}else{const done=document.createElement('p');done.textContent='Future Age reached';panel.append(done)}}
 const note=document.createElement('small');note.textContent='Five eras: gather supplies, advance and research. Construction and recruitment costs change with each era. Early settlements use food, wood and stone; industrial equipment uses iron and future equipment uses Riftglass. Your buildings upgrade automatically as you advance. Troops and queued recruits keep the equipment from the era in which they were ordered.';const link=document.createElement('a');link.href='/historical-designs/index.html';link.target='_blank';link.rel='noopener';link.textContent='Compare every faction and era ↗';panel.append(note,link);
}
