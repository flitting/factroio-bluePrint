-- Native vanilla circuit builder. No tick-time actuator writes.
local function build_native_controller(surface, ox, oy, phase_ticks, ident)
 assert(phase_ticks % 2 == 0)
 local function put(name,x,y,d)
  local args={name=name,position={x=x,y=y},direction=d or 0,force='player'}
  assert(surface.can_place_entity(args),'Cannot place '..name..' '..x..','..y)
  return assert(surface.create_entity(args))
 end
 local a=put('arithmetic-combinator',ox+.5,oy,0)
 local b=put('arithmetic-combinator',ox+3.5,oy,0)
 local c=put('arithmetic-combinator',ox+6.5,oy,0)
 local sub=put('substation',ox+3,oy+3,0)
 local solar1=put('solar-panel',ox+1.5,oy+7.5,0)
 local solar2=put('solar-panel',ox+5.5,oy+7.5,0)
 local battery=put('accumulator',ox+9,oy+3,0)
 local function sig(name) return {type='virtual',name='signal-'..name} end
 a.get_or_create_control_behavior().parameters={first_signal=sig('T'),operation='+',second_constant=1,output_signal=sig('I')}
 b.get_or_create_control_behavior().parameters={first_signal=sig('I'),operation='%',second_constant=3*phase_ticks/2,output_signal=sig('T')}
 c.get_or_create_control_behavior().parameters={first_signal=sig('T'),operation='/',second_constant=phase_ticks/2,output_signal=sig('P')}
 local function connect(e,from,f,to)
  assert(e.get_wire_connector(from,true).connect_to(f.get_wire_connector(to,true),true),'wire out of reach')
 end
 connect(a,defines.wire_connector_id.combinator_output_red,b,defines.wire_connector_id.combinator_input_red)
 connect(b,defines.wire_connector_id.combinator_output_red,a,defines.wire_connector_id.combinator_input_red)
 connect(b,defines.wire_connector_id.combinator_output_red,c,defines.wire_connector_id.combinator_input_red)
 connect(c,defines.wire_connector_id.combinator_output_green,sub,defines.wire_connector_id.circuit_green)
 return {id=ident,A=a,B=b,C=c,substation=sub,solar={solar1,solar2},battery=battery,phase_ticks=phase_ticks,relays={},gates={}}
end
local function link_gate(surface,module,gate,phase)
 assert(phase>=0 and phase<=2)
 local cb=gate.get_or_create_control_behavior()
 cb.close_signal=true;cb.read_signal=false
 cb.circuit_condition={first_signal={type='virtual',name='signal-P'},comparator='!=',constant=phase}
 -- Medium-pole relays have real legal collision boxes and circuit reach checks.
 local current=module.substation
 local function dist(a,b) return ((a.x-b.x)^2+(a.y-b.y)^2)^.5 end
 local guard=0
 while not current.get_wire_connector(defines.wire_connector_id.circuit_green,true).connect_to(gate.get_wire_connector(defines.wire_connector_id.circuit_green,true),true) do
  guard=guard+1;assert(guard<800,'wire routing did not converge')
  local cp,gp=current.position,gate.position;local best,bestscore
  for dx=-8,8 do for dy=-8,8 do
   local p={x=math.floor(cp.x)+dx+.5,y=math.floor(cp.y)+dy+.5}
   local step=dist(cp,p);local remaining=dist(p,gp)
   if step<=8.5 and step>=2 and remaining<dist(cp,gp)-.25 then
    local args={name='medium-electric-pole',position=p,force='player'}
    if surface.can_place_entity(args) then
     local score=remaining+.02*math.abs(step-7)
     if not bestscore or score<bestscore then best=p;bestscore=score end
    end
   end
  end end
  assert(best,'No legal forward pole route')
  local e=assert(surface.create_entity{name='medium-electric-pole',position=best,force='player'})
  assert(current.get_wire_connector(defines.wire_connector_id.circuit_green,true).connect_to(e.get_wire_connector(defines.wire_connector_id.circuit_green,true),true),'relay wire failed')
  module.relays[#module.relays+1]=e;current=e
 end
 module.gates[#module.gates+1]={entity=gate,phase=phase}
end
local function read_module(module)
 local row={id=module.id,phase=module.C.get_signal({type='virtual',name='signal-P'},defines.wire_connector_id.combinator_output_green),counter=module.B.get_signal({type='virtual',name='signal-T'},defines.wire_connector_id.combinator_output_red),gates={},combinators={},battery_energy=module.battery.energy}
 for _,e in ipairs({module.A,module.B,module.C}) do row.combinators[#row.combinators+1]={energy=e.energy,status=e.status,electric_network_id=e.electric_network_id} end
 for _,g in ipairs(module.gates) do row.gates[#row.gates+1]={phase=g.phase,p=g.entity.get_signal({type='virtual',name='signal-P'},defines.wire_connector_id.circuit_green),state=g.entity.signal_state,status=g.entity.status,fulfilled=g.entity.get_control_behavior().circuit_condition.fulfilled} end
 return row
end
