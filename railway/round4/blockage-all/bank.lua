local vec={{0,-1},{1,0},{0,1},{-1,0}};local names={'N','E','S','W'}
local s,ports,active,records,samples,last_completion
local outside_counts={CONFIG.bank,CONFIG.bank,CONFIG.bank,CONFIG.bank}
local completed,total_completed,entered=0,0,0
local damage_events=0;local damaged_amount=0;local retired=0
local first_exit_signals={};local measurement_started=false
local block_controllers={};local block_history={};local queue_head_samples={}
local block_signal_samples={};local signal_state_names={};for k,v in pairs(defines.signal_state or {}) do signal_state_names[v]=k end
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
     local sig=signal(rail,dir)
     if lane~=inlet and not first_exit_signals[side] then
      first_exit_signals[side]={offset=offset,position=sig.position}
      if true then
       local combinator=place('constant-combinator',{x=rail.position.x-vec[side][2]*5,y=rail.position.y+vec[side][1]*5},0)
       local cb=combinator.get_or_create_control_behavior();local sec=cb.get_section(1) or cb.add_section();sec.set_slot(1,{value={type='virtual',name='signal-A',quality='normal'},min=1});cb.enabled=false
       local sb=sig.get_or_create_control_behavior();sb.close_signal=true;sb.circuit_condition={first_signal={type='virtual',name='signal-A'},comparator='>',constant=0}
       assert(sig.get_wire_connector(defines.wire_connector_id.circuit_red,true).connect_to(combinator.get_wire_connector(defines.wire_connector_id.circuit_red,true)))
       block_controllers[#block_controllers+1]={cb=cb,signal=sig,side=names[side],side_index=side,offset=offset}
      end
     end
    end
   end
  end
  local p=ports[side][3-inlet];local dx,dy=vec[side][1],vec[side][2]
  local stop=place('train-stop',{x=p.x+dx*CONFIG.stop_offset-dy*2,y=p.y+dy*CONFIG.stop_offset+dx*2},(side-1)*4);stop.backer_name='OUT-'..names[side]
 end
 assert(#block_controllers==4,'all-exit fixture must control exactly four signals')
 local seen_exits={};for _,b in ipairs(block_controllers) do
  assert(not seen_exits[b.side],'duplicate controlled exit');seen_exits[b.side]=true
  local first=assert(first_exit_signals[b.side_index],'missing first exit signal')
  assert(b.offset==first.offset and b.signal.position.x==first.position.x and b.signal.position.y==first.position.y,'controller is not on first exit signal')
 end
 for _,name in ipairs(names) do assert(seen_exits[name],'uncontrolled exit '..name) end
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
 result.protocol='round4-expanded-all-exits-closure-v1'
 result.block_history=block_history;result.queue_head_samples=queue_head_samples
 result.block_signal_samples=block_signal_samples;result.signal_state_names=signal_state_names;result.block_controller_count=#block_controllers
 result.all_exit_head_proxy_note='The single-blocked-destination/open-next-destination proxy does not apply when every exit is blocked.'
 result.controlled_exits={};for _,b in ipairs(block_controllers) do result.controlled_exits[#result.controlled_exits+1]={exit=b.side,offset=b.offset,signal_position=b.signal.position} end
 result.damage_events=damage_events;result.damaged_amount=damaged_amount
 result.active_world=#active;result.uncompleted_active=count_uncompleted();result.retired=retired
 result.first_exit_signals=first_exit_signals;result.no_upstream_ticks=no_upstream_ticks;result.entry_supply_min=entry_supply_min
 result.measurement={from_tick=CONFIG.warmup,to_tick_exclusive=CONFIG.warmup+CONFIG.duration,entry_plane=CONFIG.entry_plane,exit_plane=CONFIG.exit_plane,sink_plane=CONFIG.sink_plane,body_margin=6,first_exit_clearance=CONFIG.exit_clearance}
 result.config.blueprint=nil;helpers.write_file('result.json',helpers.table_to_json(result),false);script.finish_test(true)
end
script.on_event(defines.events.on_tick,function(event)
 local tick=event.tick
 if CONFIG.block_enabled then
  local closed=tick>=CONFIG.block_start and tick<CONFIG.block_end
  for _,b in ipairs(block_controllers) do if b.cb.enabled~=closed then b.cb.enabled=closed;block_history[#block_history+1]={tick=tick,exit=b.side,closed=closed} end end
 end
 if CONFIG.block_enabled and (tick==CONFIG.block_start+2 or tick==CONFIG.block_start+120 or tick==math.floor((CONFIG.block_start+CONFIG.block_end)/2) or tick==CONFIG.block_end-1 or tick==CONFIG.block_end+2 or tick==CONFIG.block_end+120) then
  local states={};for _,b in ipairs(block_controllers) do states[#states+1]={exit=b.side,command_closed=b.cb.enabled,signal_state=b.signal.signal_state,signal_state_name=signal_state_names[b.signal.signal_state]} end
  block_signal_samples[#block_signal_samples+1]={tick=tick,states=states}
 end
 -- Physical queue-head observations only. This proxy intentionally does not
 -- claim counterfactual lost capacity or detect every internal HOL condition.
 if tick%60==0 then
  local qs={{},{},{},{}}
  for _,a in ipairs(active) do
   if not a.r.complete_tick then
    local o=a.r.origin;local lane=(o==1 or o==2) and 1 or 2;local p=ports[o][lane]
    local pos=a.loco.position;local along=project(pos,p,o)
    local lateral=(pos.x-p.x)*vec[o][2]-(pos.y-p.y)*vec[o][1]
    if along>=0 and math.abs(lateral)<1e-6 then
     qs[o][#qs[o]+1]={id=a.r.id,destination=names[a.r.destination],distance=along,speed=a.train.speed,state=a.train.state}
    end
   end
  end
  local heads={}
  for o=1,4 do
   table.sort(qs[o],function(a,b) return a.distance<b.distance end)
   local h=qs[o][1];local following=qs[o][2]
   if h and h.distance<=120 then
    heads[#heads+1]={origin=names[o],head=h,following=following,external_queue_size=#qs[o],
     stopped_at_signal=h.state==defines.train_state.wait_signal and math.abs(h.speed)<1e-9,
     blocked_destination_head_with_open_destination_next=h.destination==CONFIG.block_exit and following~=nil and following.destination~=CONFIG.block_exit and h.state==defines.train_state.wait_signal and math.abs(h.speed)<1e-9}
   end
  end
  queue_head_samples[#queue_head_samples+1]={tick=tick,heads=heads}
 end
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
