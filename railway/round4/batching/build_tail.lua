local result={engine=script.active_mods,cases={}};local live={}
local function board_free(s,x,y)
 for _,z in ipairs({{'arithmetic-combinator',.5,0},{'arithmetic-combinator',3.5,0},{'arithmetic-combinator',6.5,0},{'substation',3,3},{'solar-panel',1.5,7.5},{'solar-panel',5.5,7.5},{'accumulator',9,3}}) do
  if not s.can_place_entity{name=z[1],position={x=x+z[2],y=y+z[3]},direction=0,force='player'} then return false end
 end
 return true
end
script.on_init(function()
 for _,case in ipairs(CONFIG.cases) do
  local row={id=case.id,expected=case.expected,phase_ticks=case.phase_ticks,modules={},remaining={},phase_traces={},gate_traces={}}
  local s=game.create_surface(case.id,{width=4096,height=4096,autoplace_controls={}});s.generate_with_lab_tiles=true;s.request_to_generate_chunks({0,0},math.ceil(case.extent/32)+2);s.force_generate_chunk_requests()
  for _,e in pairs(s.find_entities()) do e.destroy() end
  local inv=game.create_inventory(1);local bp=inv[1];bp.set_stack{name='blueprint'};assert(bp.import_stack(case.blueprint)==0)
  local gs=bp.build_blueprint{surface=s,force='player',position={0,0},build_mode=defines.build_mode.normal};row.ghosts=#gs
  local minx,miny=1e9,1e9;for _,g in pairs(gs) do minx=math.min(minx,g.position.x);miny=math.min(miny,g.position.y) end
  row.dx=minx-case.minx;row.dy=miny-case.miny
  row.revived=0;for pass=1,40 do local n=0;for _,g in pairs(gs) do if g.valid then local _,e=g.revive{};if e then n=n+1;row.revived=row.revived+1 end end end;if n==0 then break end end
  for _,g in pairs(gs) do if g.valid then row.remaining[#row.remaining+1]={name=g.ghost_name,position=g.position,direction=g.direction} end end
  row.normal_build_complete=#gs==case.expected and #row.remaining==0;assert(row.normal_build_complete,'Base normal construction failed')
  inv.destroy();local modules={}
  for destination=1,4 do
   local wanted={};local center={x=0,y=0}
   for _,g in ipairs(case.gates) do if g.destination==destination then wanted[#wanted+1]=g;center.x=center.x+g.signal.position.x+row.dx;center.y=center.y+g.signal.position.y+row.dy end end
   center.x=math.floor(center.x/#wanted/2)*2;center.y=math.floor(center.y/#wanted/2)*2
   local bx,by
   for radius=16,256,8 do
    if bx then break end
    for x=-radius,radius,4 do
     if bx then break end
     for y=-radius,radius,4 do
      if (math.abs(x)==radius or math.abs(y)==radius) and board_free(s,center.x+x,center.y+y) then bx=center.x+x;by=center.y+y;break end
     end
    end
   end
   assert(bx,'No board site found')
   local m=build_native_controller(s,bx,by,case.phase_ticks,'output-'..destination);m.destination=destination;m.trace={};m.gate_trace={};m.power_samples={}
   for _,g in ipairs(wanted) do
    local p={x=g.signal.position.x+row.dx,y=g.signal.position.y+row.dy};local match
    for _,e in pairs(s.find_entities_filtered{name=g.signal.name,position=p,radius=.01}) do if e.direction==g.signal.direction and e.rail_layer==g.signal.rail_layer then match=e;break end end
    assert(match,'Missing private gate');link_gate(s,m,match,g.phase);m.gates[#m.gates].origin=g.origin;m.gates[#m.gates].destination=g.destination
   end
   modules[#modules+1]=m;row.modules[#row.modules+1]={destination=destination,board_origin={x=bx,y=by},relay_count=#m.relays,gates=wanted}
  end
  live[#live+1]={surface=s,modules=modules,row=row};result.cases[#result.cases+1]=row
 end
end)
script.on_event(defines.events.on_tick,function(event)
 for _,case in ipairs(live) do for _,m in ipairs(case.modules) do
  local r=read_module(m)
  if m.last_phase~=r.phase then m.trace[#m.trace+1]={tick=event.tick,phase=r.phase,counter=r.counter};m.last_phase=r.phase end
  local states='';for _,g in ipairs(r.gates) do states=states..g.state..',' end
  if m.last_states~=states then m.gate_trace[#m.gate_trace+1]={tick=event.tick,gates=r.gates};m.last_states=states end
  if event.tick%600==0 then r.tick=event.tick;m.power_samples[#m.power_samples+1]=r end
 end end
 if event.tick>=CONFIG.duration then
  for _,case in ipairs(live) do
   local row,s=case.row,case.surface;row.controllers={};row.signal_status={};row.nonworking_signals={}
   for _,m in ipairs(case.modules) do
    row.controllers[#row.controllers+1]={id=m.id,destination=m.destination,phase_trace=m.trace,gate_trace=m.gate_trace,power_samples=m.power_samples,final=read_module(m)}
   end
   for _,e in pairs(s.find_entities_filtered{type={'rail-signal','rail-chain-signal'}}) do
    local status=tostring(e.status);row.signal_status[status]=(row.signal_status[status] or 0)+1
    if e.status~=defines.entity_status.working and e.status~=defines.entity_status.disabled_by_control_behavior then row.nonworking_signals[#row.nonworking_signals+1]={name=e.name,position=e.position,direction=e.direction,status=e.status} end
   end
   local inv=game.create_inventory(1);local bp=inv[1];bp.set_stack{name='blueprint'};bp.create_blueprint{surface=s,force='player',area={{-1600,-1600},{1600,1600}},always_include_tiles=false,include_entities=true};bp.label=row.id;row.blueprint=bp.export_stack();row.entities=bp.get_blueprint_entities();inv.destroy()
  end
  helpers.write_file('result.json',helpers.table_to_json(result),false);script.finish_test(true)
 end
end)
