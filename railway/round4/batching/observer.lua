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
