local modules={};local result={engine=script.active_mods,cases={},signal_state=defines.signal_state,entity_status=defines.entity_status}
script.on_init(function()
 for _,phase_ticks in ipairs(CONFIG.phases) do
  local s=game.create_surface('phase-'..phase_ticks,{width=128,height=128,autoplace_controls={}});s.generate_with_lab_tiles=true;s.request_to_generate_chunks({0,0},3);s.force_generate_chunk_requests()
  for _,e in pairs(s.find_entities()) do e.destroy() end
  local m=build_native_controller(s,0,0,phase_ticks,'phase-'..phase_ticks)
  for j=0,2 do
   local mid
   for y=-7,7,2 do local e=assert(s.create_entity{name='straight-rail',position={x=21+8*j,y=y},direction=0,force='player'});if y==1 then mid=e end end
   local loc=mid.get_rail_end(0).out_signal_location
   local args={name='rail-signal',position=loc.position,direction=loc.direction,rail_layer=loc.rail_layer,force='player'}
   assert(s.can_place_entity(args));local gate=assert(s.create_entity(args));link_gate(s,m,gate,j)
  end
  m.surface=s;m.trace={};m.gate_trace={};m.snapshots={};modules[#modules+1]=m
 end
end)
script.on_event(defines.events.on_tick,function(event)
 for _,m in ipairs(modules) do
  local r=read_module(m)
  if m.previous_phase~=r.phase then m.trace[#m.trace+1]={tick=event.tick,phase=r.phase,counter=r.counter};m.previous_phase=r.phase end
  local states='';for _,g in ipairs(r.gates) do states=states..g.state..',' end
  if states~=m.previous_states then m.gate_trace[#m.gate_trace+1]={tick=event.tick,gates=r.gates};m.previous_states=states end
  if event.tick%600==0 then r.tick=event.tick;m.snapshots[#m.snapshots+1]=r end
 end
 if event.tick>=CONFIG.duration then
  for _,m in ipairs(modules) do
   local row={id=m.id,requested_phase_ticks=m.phase_ticks,phase_trace=m.trace,gate_trace=m.gate_trace,snapshots=m.snapshots,final=read_module(m),relay_count=#m.relays,daytime=m.surface.daytime}
   local inv=game.create_inventory(1);local bp=inv[1];bp.set_stack{name='blueprint'};bp.create_blueprint{surface=m.surface,force='player',area={{-64,-64},{64,64}},always_include_tiles=false,include_entities=true};bp.label=m.id;row.blueprint=bp.export_stack();row.entities=bp.get_blueprint_entities();inv.destroy();result.cases[#result.cases+1]=row
  end
  helpers.write_file('result.json',helpers.table_to_json(result),false);script.finish_test(true)
 end
end)
