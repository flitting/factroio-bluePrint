local vec={{0,-1},{1,0},{0,1},{-1,0}};local names={'N','E','S','W'}
local s,ports,active,records,samples,last_completion
local completed,total_completed,entered=0,0,0
local damage_events=0;local damaged_amount=0;local retired=0
local first_exit_signals={};local measurement_started=false
local measured_od={};local entry_supply_min={1e9,1e9,1e9,1e9};local no_upstream_ticks={0,0,0,0}
local function count_uncompleted() local n=0;for _,a in ipairs(active or {}) do if not a.r.complete_tick then n=n+1 end end;return n end
script.on_event(defines.events.on_entity_damaged,function(e) if e.entity.valid and (e.entity.type=="locomotive" or e.entity.type=="cargo-wagon") then damage_events=damage_events+1;damaged_amount=damaged_amount+(e.final_damage_amount or 0) end end)
local block_controllers={};local block_history={};local pending={{},{},{},{}};local next_event=1;local collision_count=0
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

local preparing_save=false
local profile_running=false
local profile_event_count=0
local profile_first_tick=nil
local profile_start_completed=0
local profile_start_entered=0
local profile_active_sum=0
local profile_waiting_sum=0
local profile_pending_sum=0
local profile_start_records=0
local profile_start_damage=0
local profile_pending_flow=nil
local function checkpoint()
 storage.profile={surface=s,ports=ports,active=active,records=records,samples=samples,last_completion=last_completion,
 completed=completed,total_completed=total_completed,entered=entered,block_controllers=block_controllers,block_history=block_history,
 pending=pending,next_event=next_event,collision_count=collision_count,random_state=random_state,damage_events=damage_events,
 damaged_amount=damaged_amount,retired=retired,first_exit_signals=first_exit_signals,measurement_started=measurement_started,
 measured_od=measured_od,entry_supply_min=entry_supply_min,no_upstream_ticks=no_upstream_ticks,checkpoint_tick=game.tick}
 storage.profile_saved=true
end
script.on_load(function()
 local p=storage.profile
 if p then
  s=p.surface;ports=p.ports;active=p.active;records=p.records;samples=p.samples;last_completion=p.last_completion
  completed=p.completed;total_completed=p.total_completed;entered=p.entered;block_controllers=p.block_controllers;block_history=p.block_history
  pending=p.pending;next_event=p.next_event;collision_count=p.collision_count;random_state=p.random_state;damage_events=p.damage_events
  damaged_amount=p.damaged_amount;retired=p.retired;first_exit_signals=p.first_exit_signals;measurement_started=p.measurement_started
  measured_od=p.measured_od;entry_supply_min=p.entry_supply_min;no_upstream_ticks=p.no_upstream_ticks
  profile_running=true;profile_start_completed=total_completed;profile_start_entered=entered;profile_start_records=#records;profile_start_damage=damage_events
 end
end)
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
     local first=lane~=inlet and not first_exit_signals[side]
     if first then first_exit_signals[side]={offset=offset,position=sig.position} end
     if first and #CONFIG.demand.exit_blocks>0 then
      local combinator=place('constant-combinator',{x=rail.position.x-vec[side][2]*5,y=rail.position.y+vec[side][1]*5},0)
      local cb=combinator.get_or_create_control_behavior();local sec=cb.get_section(1) or cb.add_section();sec.set_slot(1,{value={type='virtual',name='signal-A',quality='normal'},min=1});cb.enabled=false
      local sb=sig.get_or_create_control_behavior();sb.close_signal=true;sb.circuit_condition={first_signal={type='virtual',name='signal-A'},comparator='>',constant=0}
      assert(sig.get_wire_connector(defines.wire_connector_id.circuit_red,true).connect_to(combinator.get_wire_connector(defines.wire_connector_id.circuit_red,true)))
      block_controllers[names[side]]={cb=cb,signal=sig}
     end
    end
   end
  end
  local p=ports[side][3-inlet];local dx,dy=vec[side][1],vec[side][2]
  local stop=place('train-stop',{x=p.x+dx*CONFIG.stop_offset-dy*2,y=p.y+dy*CONFIG.stop_offset+dx*2},(side-1)*4);stop.backer_name='OUT-'..names[side]
 end
 log('TRAFFIC_RAILS_READY');for i=1,7 do game.forces.player.technologies['braking-force-'..i].researched=true end
 active={};records={};samples={};last_completion=0
game.speed=1000;log('TRAFFIC_BANK_READY')
end)
local function project(p,port,side) return (p.x-port.x)*vec[side][1]+(p.y-port.y)*vec[side][2] end
local function finish()
 local od={};for o=1,4 do for d=1,4 do if o~=d then od[names[o]..'-'..names[d]]={generated=0,entered=0,completed=0,measured_completed=0,max_wait_ticks=0} end end end
 local delays={}
 for _,r in ipairs(records) do local a=od[names[r.origin]..'-'..names[r.destination]];a.generated=a.generated+1;if r.entry_tick then a.entered=a.entered+1 end;if r.complete_tick then a.completed=a.completed+1;if r.complete_tick>=CONFIG.warmup and r.complete_tick<CONFIG.warmup+CONFIG.duration then a.measured_completed=a.measured_completed+1;delays[#delays+1]=(r.complete_tick-r.entry_tick)/60 end else a.max_wait_ticks=math.max(a.max_wait_ticks,game.tick-r.arrival_tick) end end
 table.sort(delays);local sum=0;for _,d in ipairs(delays) do sum=sum+d end
 local snapshots={};for _,a in ipairs(active) do local t=a.loco.train;local rails={};for _,r in pairs(t.get_rails()) do rails[#rails+1]={id=r.unit_number,position=r.position,name=r.name} end;snapshots[#snapshots+1]={id=a.r.id,origin=a.r.origin,destination=a.r.destination,entered=a.r.entry_tick~=nil,state=t.state,speed=t.speed,has_path=t.has_path,position=a.loco.position,signal=t.signal and {name=t.signal.name,position=t.signal.position} or nil,rails=rails} end
 local result={id=CONFIG.id,scenario=CONFIG.scenario,seed=CONFIG.seed,engine=script.active_mods,config=CONFIG,completed=completed,total_completed=total_completed,entered=entered,remaining=count_uncompleted()+#pending[1]+#pending[2]+#pending[3]+#pending[4],throughput=completed/(CONFIG.duration/3600),capacity_claim='finite offered-load stability diagnostic; source-limited above the measured source supply ceiling (not calibrated here); not a proven maximum',demand_sha256=CONFIG.demand.sha256,collision_count='unavailable',collision_detection='valid locomotive and five-car consist assertions every tick',block_history=block_history,pending_requests={#pending[1],#pending[2],#pending[3],#pending[4]},od=od,mean_transit_seconds=#delays>0 and sum/#delays or 'unavailable',p95_transit_seconds=delays[math.ceil(#delays*.95)] or 'unavailable',p99_transit_seconds=delays[math.ceil(#delays*.99)] or 'unavailable',records=records,samples=samples,final_train_snapshots=snapshots,no_completion_ticks=game.tick-last_completion,arrival_model='external common demand trace with retained per-inlet FIFO',deadlock_proof=false,rail_pathfinder_cpu='unavailable',repath_count='unavailable'}
 result.protocol='round2-independent-boundaries-v1'
 result.damage_events=damage_events;result.damaged_amount=damaged_amount
 result.active_world=#active;result.uncompleted_active=count_uncompleted();result.retired=retired
 result.first_exit_signals=first_exit_signals;result.no_upstream_ticks=no_upstream_ticks;result.entry_supply_min=entry_supply_min
 result.measurement={from_tick=CONFIG.warmup,to_tick_exclusive=CONFIG.warmup+CONFIG.duration,entry_plane=CONFIG.entry_plane,exit_plane=CONFIG.exit_plane,sink_plane=CONFIG.sink_plane,body_margin=6,first_exit_clearance=CONFIG.exit_clearance}
 result.config.blueprint=nil;result.config.demand=nil;helpers.write_file('result.json',helpers.table_to_json(result),false);script.finish_test(true)
end
script.on_event(defines.events.on_tick,function(event)
 local tick=event.tick
 for _,b in ipairs(CONFIG.demand.exit_blocks) do
  local c=block_controllers[b.exit];assert(c,'missing blockage controller')
  local closed=tick>=b.from_tick and tick<b.to_tick
  if c.cb.enabled~=closed then c.cb.enabled=closed;block_history[#block_history+1]={tick=tick,exit=b.exit,closed=closed} end
 end

 while CONFIG.demand.events[next_event] and CONFIG.demand.events[next_event].tick<=tick do
  local req=CONFIG.demand.events[next_event];next_event=next_event+1
  local o,d;for i,n in ipairs(names) do if n==req.origin then o=i end;if n==req.destination then d=i end end
  local r={id=req.id,origin=o,destination=d,arrival_tick=req.tick};records[#records+1]=r;pending[o][#pending[o]+1]=r
 end
 for side=1,4 do if #pending[side]>0 and tick%2==0 then
  local inlet=(side==1 or side==2) and 1 or 2;local p=ports[side][inlet];local dx,dy=vec[side][1],vec[side][2]
  local blocked=false
  for _,a in ipairs(active) do if a.r.origin==side and not a.r.entry_tick then
   for _,c in pairs(a.loco.train.carriages) do local off=project(c.position,p,side);if off>CONFIG.spawn_offset-20 and off<CONFIG.spawn_offset+38 then blocked=true end end
  end end
  if not blocked then
   local r=table.remove(pending[side],1);local off=CONFIG.spawn_offset;local dir=((side-1)*4+8)%16
   local loco=place('locomotive',{x=p.x+dx*off,y=p.y+dy*off},dir)
   for k=1,4 do local w=place('cargo-wagon',{x=p.x+dx*(off+7*k),y=p.y+dy*(off+7*k)},dir);if CONFIG.loaded then assert(w.insert{name='iron-plate',count=4000}==4000) end end
   assert(#loco.train.carriages==5);loco.insert{name='nuclear-fuel',count=3}
   loco.train.schedule={current=1,records={{station='OUT-'..names[r.destination]}}};loco.train.manual_mode=false
   r.spawn_tick=tick;active[#active+1]={loco=loco,r=r}
  end
 end end

 for i=#active,1,-1 do local a=active[i];assert(a.loco.valid,'collision or invalid locomotive');local train=a.loco.train;assert(#train.carriages==5,'collision or consist change')
  local r=a.r;local il=(r.origin==1 or r.origin==2) and 1 or 2;local ol=(r.destination==1 or r.destination==2) and 2 or 1
  if not r.entry_tick and project(train.front_stock.position,ports[r.origin][il],r.origin)<=CONFIG.entry_plane then r.entry_tick=tick;entered=entered+1 end
  if r.entry_tick and not r.complete_tick then
   local done=true;for _,e in pairs(train.carriages) do if project(e.position,ports[r.destination][ol],r.destination)<CONFIG.exit_plane+6 then done=false;break end end
   if done then
    r.complete_tick=tick;r.speed_at_completion=train.speed;total_completed=total_completed+1
    if tick>=CONFIG.warmup and tick<CONFIG.warmup+CONFIG.duration then completed=completed+1 end
    last_completion=tick
   end
  end
  if r.complete_tick then
   local gone=true;for _,e in pairs(train.carriages) do if project(e.position,ports[r.destination][ol],r.destination)<CONFIG.sink_plane+6 then gone=false;break end end
   if gone then r.sink_tick=tick;for _,e in pairs(train.carriages) do e.destroy() end;retired=retired+1;table.remove(active,i) end
  end
 end
 if tick%600==0 then log('TRAFFIC_TICK '..tick..' COMPLETED '..completed..' TOTAL '..total_completed);local states={};local queues={0,0,0,0};local inside=0;for _,a in ipairs(active) do local state=tostring(a.loco.train.state);states[state]=(states[state] or 0)+1;if not a.r.entry_tick then queues[a.r.origin]=queues[a.r.origin]+1 elseif not a.r.complete_tick then inside=inside+1 end end;local block_states={};for n,c in pairs(block_controllers) do block_states[n]={command_closed=c.cb.enabled,signal_state=c.signal.signal_state} end;samples[#samples+1]={block_states=block_states,tick=tick,completed=completed,total_completed=total_completed,active=#active,pending_requests={#pending[1],#pending[2],#pending[3],#pending[4]},upstream_queue=queues,inside=inside,states=states} end
 if profile_running then
  profile_event_count=profile_event_count+1
  profile_first_tick=profile_first_tick or tick
  profile_active_sum=profile_active_sum+#active
  local stopped=0;for _,a in ipairs(active) do if math.abs(a.loco.train.speed)<0.000001 then stopped=stopped+1 end end
  profile_waiting_sum=profile_waiting_sum+stopped
  profile_pending_sum=profile_pending_sum+#pending[1]+#pending[2]+#pending[3]+#pending[4]
  if profile_event_count==CONFIG.profile_ticks then
   local flow={protocol='round4-expanded-offered-warmed-profile-v1',id=CONFIG.id,scenario=CONFIG.scenario,seed=CONFIG.seed,
    measurement_ticks=profile_event_count,first_tick=profile_first_tick,last_tick=tick,checkpoint_tick=storage.profile.checkpoint_tick,
    completed=total_completed-profile_start_completed,entered=entered-profile_start_entered,arrived=#records-profile_start_records,
    active_world=#active,uncompleted_active=count_uncompleted(),pending_requests={#pending[1],#pending[2],#pending[3],#pending[4]},
    mean_active_world=profile_active_sum/profile_event_count,mean_stopped_world=profile_waiting_sum/profile_event_count,
    mean_virtual_pending=profile_pending_sum/profile_event_count,damage_events=damage_events-profile_start_damage,
    next_event=next_event,total_completed=total_completed,total_records=#records,demand_sha256=CONFIG.demand.sha256,
    no_train_speed_writes=true,no_teleports=true,records=records}
   profile_pending_flow=flow
  elseif profile_event_count==CONFIG.profile_ticks+1 then
   local flow=profile_pending_flow
   local clipped={}
   for _,r in ipairs(records) do if r.arrival_tick<=flow.last_tick then
    local c={};for k,v in pairs(r) do
     if (k~='spawn_tick' and k~='entry_tick' and k~='complete_tick' and k~='sink_tick') or v<=flow.last_tick then c[k]=v end
    end
    if not c.complete_tick then c.speed_at_completion=nil end
    clipped[#clipped+1]=c
   end end
   flow.records=clipped
   helpers.write_file('profile-flows.jsonl',helpers.table_to_json(flow)..'\n',true)
   log('PROFILE_FLOW_READY measured_ticks='..flow.measurement_ticks..' completed='..flow.completed)
  end
 elseif not storage.profile_saved and tick>=CONFIG.warmup then
  checkpoint();preparing_save=true;game.tick_paused=true
  log('PROFILE_SAVE_REQUEST tick='..tick)
  game.speed=1
  game.server_save('warmed')
 elseif preparing_save and tick>=CONFIG.warmup+10 then
  log('PROFILE_PREPARATION_FINISHED tick='..tick)
  preparing_save=false
 end
end)
