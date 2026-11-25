local result={engine=script.active_mods,cases={}}
local function key(name,p,d) return name..':'..p.x..':'..p.y..':'..(d or 0) end
script.on_init(function()
 for _,case in ipairs(CONFIG.cases) do
  local row={id=case.id,expected=case.expected,signals={},remaining={},missing={},direction_conflicts={}}
  local s=game.create_surface(case.id,{width=4096,height=4096,autoplace_controls={}});s.generate_with_lab_tiles=true;s.request_to_generate_chunks({0,0},math.ceil(case.extent/32)+2);s.force_generate_chunk_requests()
  local inv=game.create_inventory(1);local bp=inv[1];bp.set_stack{name='blueprint'};assert(bp.import_stack(case.blueprint)==0)
  local gs=bp.build_blueprint{surface=s,force='player',position={0,0},build_mode=defines.build_mode.normal};row.ghosts=#gs
  local minx,miny=1e9,1e9;for _,g in pairs(gs) do minx=math.min(minx,g.position.x);miny=math.min(miny,g.position.y) end
  row.dx=minx-case.minx;row.dy=miny-case.miny
  row.revived=0;for pass=1,40 do local n=0;for _,g in pairs(gs) do if g.valid then local _,e=g.revive{};if e then n=n+1;row.revived=row.revived+1 end end end;if n==0 then break end end
  for _,g in pairs(gs) do if g.valid then row.remaining[#row.remaining+1]={name=g.ghost_name,position=g.position,direction=g.direction} end end
  row.build_complete=#gs==case.expected and #row.remaining==0
  if row.build_complete then
   local lookup={};local usage={};local rails={}
   for _,e in pairs(s.find_entities_filtered{force='player'}) do if string.find(e.type,'rail') and e.type~='rail-support' then lookup[key(e.name,e.position,e.direction)]=e;rails[e.unit_number]=e end end
   for segidx,seg in ipairs(case.segments) do
    local native={};for i,z in ipairs(seg) do native[i]=lookup[key(z.name,{x=z.position.x+row.dx,y=z.position.y+row.dy},z.direction)] end
    for i,e in ipairs(native) do
     local next=native[i+1];local prev=native[i-1];local rd=nil
     if next then
      for dir=0,1 do for turn=0,2 do local other=e.get_connected_rail{rail_direction=dir,rail_connection_direction=turn};if other and other.unit_number==next.unit_number then rd=dir end end end
     elseif prev then
      for dir=0,1 do for turn=0,2 do local other=e.get_connected_rail{rail_direction=dir,rail_connection_direction=turn};if other and other.unit_number==prev.unit_number then rd=1-dir end end end
     end
     if rd==nil then row.missing[#row.missing+1]={segment=segidx,index=i,name=e.name,position=e.position,next=next and {name=next.name,position=next.position} or nil}
     else usage[e.unit_number]=usage[e.unit_number] or {};usage[e.unit_number][rd]=true end
    end
   end
   local cs={};for id,dirs in pairs(usage) do
    if dirs[0] and dirs[1] then row.direction_conflicts[#row.direction_conflicts+1]={name=rails[id].name,position=rails[id].position}
    elseif rails[id].type~='rail-ramp' then local rd=dirs[0] and 0 or 1;local loc=rails[id].get_rail_end(rd).out_signal_location;cs[#cs+1]={name='rail-signal',position=loc.position,direction=loc.direction,rail_layer=loc.rail_layer,force='player'} end
   end
   table.sort(cs,function(a,b) if a.rail_layer~=b.rail_layer then return a.rail_layer<b.rail_layer end;if a.position.y~=b.position.y then return a.position.y<b.position.y end;if a.position.x~=b.position.x then return a.position.x<b.position.x end;return a.direction<b.direction end)
   local placed={};for _,c in ipairs(cs) do local close=false;for _,e in ipairs(placed) do if e.rail_layer==c.rail_layer and (e.position.x-c.position.x)^2+(e.position.y-c.position.y)^2<(case.signal_spacing or 4)^2 then close=true;break end end
    if not close and s.can_place_entity(c) then local e=s.create_entity(c);if e then placed[#placed+1]=e end end
   end
  end
  row.surface=s.name;result.cases[#result.cases+1]=row;inv.destroy()
 end
end)
script.on_nth_tick(60,function()
 for _,row in ipairs(result.cases) do if row.build_complete then
  local s=game.surfaces[row.surface];row.nonworking={}
  for _,e in pairs(s.find_entities_filtered{type={'rail-signal','rail-chain-signal'}}) do
   if e.status~=defines.entity_status.working then row.nonworking[#row.nonworking+1]={name=e.name,position=e.position,direction=e.direction,rail_layer=e.rail_layer,status=e.status};e.destroy()
   else row.signals[#row.signals+1]={name=e.name,position=e.position,direction=e.direction,rail_layer=e.rail_layer} end
  end
  local inv=game.create_inventory(1);local bp=inv[1];bp.set_stack{name='blueprint'};bp.create_blueprint{surface=s,force='player',area={{-1600,-1600},{1600,1600}},always_include_tiles=false,include_entities=true};bp.label=row.id;row.blueprint=bp.export_stack();row.entities=bp.get_blueprint_entities();inv.destroy()
 end end
 helpers.write_file('result.json',helpers.table_to_json(result),false);script.finish_test(true)
end)
