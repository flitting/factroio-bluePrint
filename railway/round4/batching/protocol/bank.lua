local vec={{0,-1},{1,0},{0,1},{-1,0}};local names={'N','E','S','W'}
local s,ports,active,records,samples,last_completion
local outside_counts={CONFIG.bank,CONFIG.bank,CONFIG.bank,CONFIG.bank}
local completed,total_completed,entered=0,0,0
local damage_events=0;local damaged_amount=0;local retired=0
local first_exit_signals={};local measurement_started=false
local measured_od={};local entry_supply_min={1e9,1e9,1e9,1e9};local no_upstream_ticks={0,0,0,0}
local function count_uncompleted() local n=0;for _,a in ipairs(active or {}) do if not a.r.complete_tick then n=n+1 end end;return n end
script.on_event(defines.events.on_entity_damaged,function(e) if e.entity.valid and (e.entity.type=="locomotive" or e.entity.type=="cargo-wagon") then damage_events=damage_events+1;damaged_amount=damaged_amount+(e.final_damage_amount or 0) end end)
local random_state=CONFIG.seed or 1
local function rand() random_state=(random_state*48271)%2147483647;return random_state/2147483647 end
local function place(name,p,d)
 local args={name=name,position=p,direction=d,force='player'}
 assert(s.can_place_entity(args),'illegal '..name..' '..p.x..','..p.y)
 return assert(s.create_entity(args))
end
local function signal(rail,dir)
 for _,rd in ipairs({defines.rail_direction.front,defines.rail_direction.back}) do
  local e=rail.get_rail_end(rd)
  if e.location.direction==dir then local loc=e.out_signal_location;return place('rail-signal',loc.position,loc.direction) end
 end
 error('signal direction '..dir)
end
script.on_init(function()
 s=game.create_surface('traffic',{width=CONFIG.surface_size or 24000,height=CONFIG.surface_size or 24000,autoplace_controls={}})
 s.generate_with_lab_tiles=true
 s.request_to_generate_chunks({0,0},CONFIG.core_chunk_radius or 5)
 for side=1,4 do for offset=160,math.max(CONFIG.length,CONFIG.outlet_length)+160,32 do s.request_to_generate_chunks({vec[side][1]*offset,vec[side][2]*offset},1) end end
 s.force_generate_chunk_requests();log('TRAFFIC_CHUNKS_READY');for _,e in pairs(s.find_entities()) do e.destroy() end
 game.forces.player.chart(s,{{-160,-160},{160,160}})
 log('TRAFFIC_TILES_READY');local inv=game.create_inventory(1);local stack=inv[1];stack.set_stack{name='blueprint'};assert(stack.import_stack(CONFIG.blueprint)==0)
 local ghosts=stack.build_blueprint{surface=s,force='player',position={0,0},build_mode=defines.build_mode.normal}
 for pass=1,20 do local n=0;for _,g in pairs(ghosts) do if g.valid then local _,e=g.revive{};if e then n=n+1 end end end;if n==0 then break end end
 for _,g in pairs(ghosts) do assert(not g.valid,'unbuilt blueprint ghost') end;inv.destroy()
 local rails=s.find_entities_filtered{name='straight-rail'};local xmin,xmax,ymin,ymax=1e9,-1e9,1e9,-1e9
 for _,r in pairs(rails) do local p=r.position;xmin=math.min(xmin,p.x);xmax=math.max(xmax,p.x);ymin=math.min(ymin,p.y);ymax=math.max(ymax,p.y) end
 local edge={{},{},{},{}};for _,r in pairs(rails) do local p=r.position;if p.y==ymin then edge[1][#edge[1]+1]=r end;if p.x==xmax then edge[2][#edge[2]+1]=r end;if p.y==ymax then edge[3][#edge[3]+1]=r end;if p.x==xmin then edge[4][#edge[4]+1]=r end end
 ports={}
 for side=1,4 do
  table.sort(edge[side],function(a,b) if side==1 or side==3 then return a.position.x<b.position.x else return a.position.y<b.position.y end end)
  assert(#edge[side]==2,'not two ports')
  ports[side]={};local inlet=(side==1 or side==2) and 1 or 2
  -- Extend terrain around actual port coordinates; topology may be asymmetric.
  for lane,r in ipairs(edge[side]) do
   local p=r.position;local limit=lane==inlet and CONFIG.length or CONFIG.outlet_length
   for offset=0,limit+64,32 do s.request_to_generate_chunks({x=p.x+vec[side][1]*offset,y=p.y+vec[side][2]*offset},1) end
  end
  s.force_generate_chunk_requests()
  for lane,r in ipairs(edge[side]) do
   local p={x=r.position.x,y=r.position.y};ports[side][lane]=p
   local limit=lane==inlet and CONFIG.length or CONFIG.outlet_length
   local dir=lane==inlet and ((side-1)*4+8)%16 or (side-1)*4
   for offset=2,limit,2 do local rail=place('straight-rail',{x=p.x+vec[side][1]*offset,y=p.y+vec[side][2]*offset},r.direction)
    if offset%CONFIG.spacing==0 and (lane==inlet or offset>=CONFIG.exit_clearance) then
     local sig=signal(rail,dir);if lane~=inlet and not first_exit_signals[side] then first_exit_signals[side]={offset=offset,position=sig.position} end
    end
   end
  end
  local p=ports[side][3-inlet];local dx,dy=vec[side][1],vec[side][2]
  local stop=place('train-stop',{x=p.x+dx*CONFIG.stop_offset-dy*2,y=p.y+dy*CONFIG.stop_offset+dx*2},(side-1)*4);stop.backer_name='OUT-'..names[side]
 end
 log('TRAFFIC_RAILS_READY');for i=1,7 do game.forces.player.technologies['braking-force-'..i].researched=true end
 active={};records={};samples={};last_completion=0
 for side=1,4 do
  local inlet=(side==1 or side==2) and 1 or 2;local p=ports[side][inlet];local dx,dy=vec[side][1],vec[side][2];local dir=((side-1)*4+8)%16
  for index=1,CONFIG.bank do
   local off=120+(index-1)*CONFIG.gap;local u=rand();local dest
   if u<CONFIG.near then dest=(side+2)%4+1 elseif u<CONFIG.near+CONFIG.straight then dest=(side+1)%4+1 else dest=side%4+1 end
   local loco=place('locomotive',{x=p.x+dx*off,y=p.y+dy*off},dir)
   for k=1,4 do local w=place('cargo-wagon',{x=p.x+dx*(off+7*k),y=p.y+dy*(off+7*k)},dir);if CONFIG.loaded then w.insert{name='iron-plate',count=4000} end end
   assert(#loco.train.carriages==5);loco.insert{name='nuclear-fuel',count=3}
   loco.train.schedule={current=1,records={{station='OUT-'..names[dest]}}};loco.train.manual_mode=false
   local r={id=#records+1,origin=side,destination=dest,arrival_tick=0,spawn_tick=0};records[#records+1]=r;active[#active+1]={loco=loco,r=r,train=loco.train,cars=loco.train.carriages}
  end
 end
log('TRAFFIC_BANK_READY')
end)
local function project(p,port,side) return (p.x-port.x)*vec[side][1]+(p.y-port.y)*vec[side][2] end
local function finish()
 local od={};for o=1,4 do for d=1,4 do if o~=d then od[names[o]..'-'..names[d]]={generated=0,entered=0,completed=0,measured_completed=0,max_wait_ticks=0} end end end
 local delays={}
 for _,r in ipairs(records) do local a=od[names[r.origin]..'-'..names[r.destination]];a.generated=a.generated+1;if r.entry_tick then a.entered=a.entered+1 end;if r.complete_tick then a.completed=a.completed+1;if r.complete_tick>=CONFIG.warmup and r.complete_tick<CONFIG.warmup+CONFIG.duration then a.measured_completed=a.measured_completed+1;delays[#delays+1]=(r.complete_tick-r.entry_tick)/60 end else a.max_wait_ticks=math.max(a.max_wait_ticks,game.tick) end end
 table.sort(delays);local sum=0;for _,d in ipairs(delays) do sum=sum+d end
 local snapshots={};for _,a in ipairs(active) do local t=a.loco.train;local rails={};for _,r in pairs(t.get_rails()) do rails[#rails+1]={id=r.unit_number,position=r.position,name=r.name} end;snapshots[#snapshots+1]={id=a.r.id,origin=a.r.origin,destination=a.r.destination,entered=a.r.entry_tick~=nil,state=t.state,speed=t.speed,has_path=t.has_path,position=a.loco.position,signal=t.signal and {name=t.signal.name,position=t.signal.position} or nil,rails=rails} end
 local result={id=CONFIG.id,scenario=CONFIG.scenario,seed=CONFIG.seed,engine=script.active_mods,config=CONFIG,completed=completed,total_completed=total_completed,entered=entered,remaining=count_uncompleted(),throughput=completed/(CONFIG.duration/3600),capacity_claim='finite preloaded saturation discharge; not maximum stable service rate',od=od,mean_transit_seconds=#delays>0 and sum/#delays or 'unavailable',p95_transit_seconds=delays[math.ceil(#delays*.95)] or 'unavailable',p99_transit_seconds=delays[math.ceil(#delays*.99)] or 'unavailable',records=records,samples=samples,final_train_snapshots=snapshots,no_completion_ticks=game.tick-last_completion,deadlock_proof=false,rail_pathfinder_cpu='unavailable',repath_count='unavailable'}
 result.protocol='round4-expanded-terrain-v1'
 result.damage_events=damage_events;result.damaged_amount=damaged_amount
 result.active_world=#active;result.uncompleted_active=count_uncompleted();result.retired=retired
 result.first_exit_signals=first_exit_signals;result.no_upstream_ticks=no_upstream_ticks;result.entry_supply_min=entry_supply_min
 result.measurement={from_tick=CONFIG.warmup,to_tick_exclusive=CONFIG.warmup+CONFIG.duration,entry_plane=CONFIG.entry_plane,exit_plane=CONFIG.exit_plane,sink_plane=CONFIG.sink_plane,body_margin=6,first_exit_clearance=CONFIG.exit_clearance}
 result.config.blueprint=nil;helpers.write_file('result.json',helpers.table_to_json(result),false);script.finish_test(true)
end
script.on_event(defines.events.on_tick,function(event)
 local tick=event.tick
 if tick>=CONFIG.warmup and tick<CONFIG.warmup+CONFIG.duration then
  local qs=outside_counts
  for side=1,4 do entry_supply_min[side]=math.min(entry_supply_min[side],qs[side]);if qs[side]==0 then no_upstream_ticks[side]=no_upstream_ticks[side]+1 end end
 end
 for i=#active,1,-1 do local a=active[i];assert(a.loco.valid,'collision or invalid locomotive');local train=a.train;assert(train.valid,'train reference changed');if tick%60==0 then local current=train.carriages;assert(#current==5,'collision or consist change');for j=1,5 do assert(current[j]==a.cars[j],'consist identity changed') end end
  local r=a.r;local il=(r.origin==1 or r.origin==2) and 1 or 2;local ol=(r.destination==1 or r.destination==2) and 2 or 1
  if not r.entry_tick and project(train.front_stock.position,ports[r.origin][il],r.origin)<=CONFIG.entry_plane then r.entry_tick=tick;entered=entered+1;outside_counts[r.origin]=outside_counts[r.origin]-1 end
  if r.entry_tick and not r.complete_tick then
   local done=true;for _,e in pairs(a.cars) do if project(e.position,ports[r.destination][ol],r.destination)<CONFIG.exit_plane+6 then done=false;break end end
   if done then
    r.complete_tick=tick;r.speed_at_completion=train.speed;total_completed=total_completed+1
    if tick>=CONFIG.warmup and tick<CONFIG.warmup+CONFIG.duration then completed=completed+1 end
    last_completion=tick
   end
  end
  if r.complete_tick then
   local gone=true;for _,e in pairs(a.cars) do if project(e.position,ports[r.destination][ol],r.destination)<CONFIG.sink_plane+6 then gone=false;break end end
   if gone then r.sink_tick=tick;for _,e in pairs(a.cars) do e.destroy() end;retired=retired+1;table.remove(active,i) end
  end
 end
 if tick%600==0 then log('TRAFFIC_TICK '..tick..' COMPLETED '..completed..' TOTAL '..total_completed);local states={};local queues={0,0,0,0};local inside=0;for _,a in ipairs(active) do local state=tostring(a.loco.train.state);states[state]=(states[state] or 0)+1;if not a.r.entry_tick then queues[a.r.origin]=queues[a.r.origin]+1 elseif not a.r.complete_tick then inside=inside+1 end end;samples[#samples+1]={tick=tick,completed=completed,total_completed=total_completed,active=#active,upstream_queue=queues,inside=inside,states=states} end
 if tick>=CONFIG.warmup+CONFIG.duration then finish() end
end)

-- Read-only native circuit observer, appended to the unchanged traffic runner.
-- on_nth_tick does not replace the traffic simulation's on_tick event handler.
local batch_live=nil
local batch_observation={method='read-only observation of actual vanilla circuit networks and native electric power',controllers={},samples={},warnings={}}
local function batch_initialize()
 batch_live={}
 local by_network={}
 for _,e in pairs(s.find_entities_filtered{name='arithmetic-combinator'}) do
  local p=e.get_control_behavior().parameters
  if p.output_signal and p.output_signal.name=='signal-P' then
   local connector=e.get_wire_connector(defines.wire_connector_id.combinator_output_green,false)
   local network=connector and connector.network_id
   assert(network,'Phase combinator has no green circuit')
   assert(not by_network[network],'Two independent phase outputs shorted into one network')
   local row={position=e.position,network_id=network,phase_divisor=p.second_constant,transitions={},gates={},minimum_combinator_energy=1e30}
   local live={entity=e,row=row,gates={},last_phase=nil}
   batch_live[#batch_live+1]=live;by_network[network]=live;batch_observation.controllers[#batch_observation.controllers+1]=row
  end
 end
 assert(#batch_live==(CONFIG.batch_expected_controllers or 0),'Incorrect controller count after blueprint import')
 for _,e in pairs(s.find_entities_filtered{name='rail-signal'}) do
  local cb=e.get_control_behavior()
  if cb and cb.close_signal then
   local conn=e.get_wire_connector(defines.wire_connector_id.circuit_green,false);local live=conn and by_network[conn.network_id]
   assert(live,'Gate lacks exactly one shared phase clock')
   local cond=cb.circuit_condition
   assert(cond.first_signal.name=='signal-P' and (cond.comparator=='!=' or cond.comparator=='≠'),'Invalid gate condition')
   live.gates[#live.gates+1]={entity=e,phase=cond.constant}
   live.row.gates[#live.row.gates+1]={position=e.position,direction=e.direction,rail_layer=e.rail_layer,phase=cond.constant}
  end
 end
 for _,live in ipairs(batch_live) do
  assert(#live.gates==3,'Each output must have three gates')
  local phases={};for _,g in ipairs(live.gates) do phases[g.phase]=true end
  assert(phases[0] and phases[1] and phases[2],'Missing output phase')
 end
 batch_observation.expected_controllers=CONFIG.batch_expected_controllers or 0
 batch_observation.all_combinators={}
 for _,e in pairs(s.find_entities_filtered{name='arithmetic-combinator'}) do batch_observation.all_combinators[#batch_observation.all_combinators+1]={entity=e,minimum_energy=1e30,minimum_energy_after_warmup=1e30} end
 batch_observation.batteries={}
 for _,e in pairs(s.find_entities_filtered{name='accumulator'}) do batch_observation.batteries[#batch_observation.batteries+1]={entity=e,minimum_energy_after_warmup=1e30} end
end
script.on_nth_tick(1,function(event)
 if not batch_live then batch_initialize() end
 for _,live in ipairs(batch_live) do
  local p=live.entity.get_signal({type='virtual',name='signal-P'},defines.wire_connector_id.combinator_output_green)
  if p~=live.last_phase then live.row.transitions[#live.row.transitions+1]={tick=event.tick,phase=p};live.last_phase=p end
 end
 if event.tick%60==0 then
  local sample={tick=event.tick,daytime=s.daytime,phases={},gates={},combinators={},batteries={}}
  for _,live in ipairs(batch_live) do
   sample.phases[#sample.phases+1]=live.last_phase
   for _,g in ipairs(live.gates) do sample.gates[#sample.gates+1]={phase=g.phase,actual_p=g.entity.get_signal({type='virtual',name='signal-P'},defines.wire_connector_id.circuit_green),signal_state=g.entity.signal_state,status=g.entity.status,close_condition_fulfilled=g.entity.get_control_behavior().circuit_condition.fulfilled} end
  end
  for _,r in ipairs(batch_observation.all_combinators) do
   r.minimum_energy=math.min(r.minimum_energy,r.entity.energy)
   if event.tick>=CONFIG.warmup then r.minimum_energy_after_warmup=math.min(r.minimum_energy_after_warmup,r.entity.energy) end
   sample.combinators[#sample.combinators+1]={energy=r.entity.energy,status=r.entity.status,electric_network_id=r.entity.electric_network_id}
  end
  for _,r in ipairs(batch_observation.batteries) do
   if event.tick>=CONFIG.warmup then r.minimum_energy_after_warmup=math.min(r.minimum_energy_after_warmup,r.entity.energy) end
   sample.batteries[#sample.batteries+1]=r.entity.energy
  end
  batch_observation.samples[#batch_observation.samples+1]=sample
 end
 if event.tick==CONFIG.warmup+CONFIG.duration-1 then
  local output={method=batch_observation.method,controllers=batch_observation.controllers,samples=batch_observation.samples,warnings=batch_observation.warnings,expected_controllers=batch_observation.expected_controllers,all_combinators={},batteries={},id=CONFIG.id,until_tick=event.tick}
  for _,r in ipairs(batch_observation.all_combinators) do output.all_combinators[#output.all_combinators+1]={position=r.entity.position,minimum_energy=r.minimum_energy,minimum_energy_after_warmup=r.minimum_energy_after_warmup} end
  for _,r in ipairs(batch_observation.batteries) do output.batteries[#output.batteries+1]={position=r.entity.position,minimum_energy_after_warmup=r.minimum_energy_after_warmup} end
  helpers.write_file('circuit-observations.json',helpers.table_to_json(output),false)
 end
end)
