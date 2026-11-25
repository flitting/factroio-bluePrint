local results={engine=script.active_mods.base,cases={}}
local function key(name,p,d) return name..':'..p.x..':'..p.y..':'..d end
script.on_init(function()
 for _,case in ipairs(CONFIG.cases) do
  log("BUILD_START "..case.id)
  local s=game.create_surface(case.id,{width=2048,height=2048,autoplace_controls={}});s.generate_with_lab_tiles=true;s.request_to_generate_chunks({0,0},12);s.force_generate_chunk_requests();game.forces.player.chart(s,{{-600,-600},{600,600}})
  local inv=game.create_inventory(1);local bp=inv[1];bp.set_stack{name='blueprint'};assert(bp.import_stack(case.blueprint)==0)
  local ghosts=bp.build_blueprint{surface=s,force='player',position={0,0},build_mode=defines.build_mode.normal};local row={id=case.id,expected=case.expected,ghosts=#ghosts,revived=0,remaining={},direction_conflicts={},path_missing={},new_signals=0};local gx,gy=1e9,1e9
  local original_ghost_specs={}
  for _,g in pairs(ghosts) do gx=math.min(gx,g.position.x);gy=math.min(gy,g.position.y);original_ghost_specs[#original_ghost_specs+1]={name=g.ghost_name,position=g.position,direction=g.direction} end
  for pass=1,30 do local n=0;for _,g in pairs(ghosts) do if g.valid then local _,e=g.revive{};if e then n=n+1;row.revived=row.revived+1 end end end;if n==0 then break end end
  row.added_supports={}
  local centers={}
  for _,g in pairs(ghosts) do if g.valid and g.ghost_name=='elevated-straight-rail' then
   local d=g.direction%8;if d==0 or d==4 then local ax=d==4 and 'x' or 'y';for _,sgn in ipairs({-1,1}) do local p={x=g.position.x,y=g.position.y};p[ax]=p[ax]+sgn;centers[#centers+1]={position=p,direction=d} end end
  end end
  -- Diagonal and half-diagonal support anchors are verified by native revival gain.
  for _,g in pairs(ghosts) do if g.valid and string.find(g.ghost_name,'elevated') then
   for ox=-2,2 do for oy=-2,2 do for di=0,7 do
    centers[#centers+1]={position={x=g.position.x+ox,y=g.position.y+oy},direction=di}
   end end end
  end end
  table.sort(centers,function(a,b) if a.position.y~=b.position.y then return a.position.y<b.position.y end;return a.position.x<b.position.x end)
  local seen={}
  for _,q in ipairs(centers) do
   local k=q.position.x..','..q.position.y..','..q.direction
   if not seen[k] then seen[k]=true
    local need=false;for _,g in pairs(ghosts) do if g.valid and string.find(g.ghost_name,'elevated') and (g.position.x-q.position.x)^2+(g.position.y-q.position.y)^2<144 then need=true;break end end
    local sp={name='rail-support',position=q.position,direction=q.direction,force='player'}
    if need and s.can_place_entity(sp) then local e=s.create_entity(sp);local total=0
     for pass=1,20 do local n=0;for _,g in pairs(ghosts) do if g.valid then local _,z=g.revive{};if z then n=n+1;row.revived=row.revived+1 end end end;total=total+n;if n==0 then break end end
     if total>0 then row.added_supports[#row.added_supports+1]={position=e.position,direction=e.direction,gain=total} else e.destroy() end
    end
   end
  end
  for _,g in pairs(ghosts) do if g.valid then row.remaining[#row.remaining+1]={name=g.ghost_name,position=g.position,direction=g.direction} end end
  row.missing_after_revival={};local lookup_actual={}
  for _,e in pairs(s.find_entities_filtered{force='player'}) do if e.type~='entity-ghost' then lookup_actual[key(e.name,e.position,e.direction)]=true end end
  for _,sp in ipairs(original_ghost_specs) do if not lookup_actual[key(sp.name,sp.position,sp.direction)] then row.missing_after_revival[#row.missing_after_revival+1]=sp end end
  row.actual_entities=#s.find_entities_filtered{force='player'};row.build_complete=#ghosts==case.expected and #row.remaining==0 and row.actual_entities==case.expected+#row.added_supports
  if row.build_complete then
   local dx,dy=gx-case.minx,gy-case.miny;row.offset={dx,dy};local lookup={};local usage={};local railset={}
   for _,e in pairs(s.find_entities_filtered{force='player'}) do if string.find(e.type,'rail') and e.type~='rail-support' then lookup[key(e.name,e.position,e.direction)]=e;railset[e.unit_number]=e end end
   for od,path in pairs(case.paths) do
    for i=1,#path-1 do local z=path[i];local p={x=z.position.x+dx,y=z.position.y+dy};local e=lookup[key(z.name,p,z.direction)];local nz=path[i+1];local np={x=nz.position.x+dx,y=nz.position.y+dy};local nxt=lookup[key(nz.name,np,nz.direction)]
     if e and nxt then local found=nil;for rd=0,1 do for cd=0,2 do local r=e.get_connected_rail{rail_direction=rd,rail_connection_direction=cd};if r and r.unit_number==nxt.unit_number then found=rd end end end
      if found~=nil then usage[e.unit_number]=usage[e.unit_number] or {};usage[e.unit_number][found]=true else row.path_missing[#row.path_missing+1]={od=od,index=i,name=z.name,position=p,reason='disconnected'} end
     else row.path_missing[#row.path_missing+1]={od=od,index=i,name=z.name,position=p,reason='missing'} end
    end
   end
   local cands={}
   for uid,dirs in pairs(usage) do
    if dirs[0] and dirs[1] then row.direction_conflicts[#row.direction_conflicts+1]={name=railset[uid].name,position=railset[uid].position}
    else local rd=dirs[0] and 0 or 1;local e=railset[uid];local loc=e.get_rail_end(rd).out_signal_location;local px,py=e.position.x-dx,e.position.y-dy;local sigtype=(math.max(math.abs(px),math.abs(py))<case.radius+60) and 'rail-chain-signal' or 'rail-signal';cands[#cands+1]={name=sigtype,position=loc.position,direction=loc.direction,rail_layer=loc.rail_layer,force='player'} end
   end
   table.sort(cands,function(a,b) if a.rail_layer~=b.rail_layer then return a.rail_layer<b.rail_layer end;if a.position.y~=b.position.y then return a.position.y<b.position.y end;if a.position.x~=b.position.x then return a.position.x<b.position.x end;return a.direction<b.direction end)
   local placed={}
   for _,seed in ipairs(case.seed_signals or {}) do
    local q={name=seed.name,position={x=seed.position.x+dx,y=seed.position.y+dy},direction=seed.direction or 0,rail_layer=seed.rail_layer or 0,force='player'}
    if s.can_place_entity(q) then local e=s.create_entity(q);if e then placed[#placed+1]=e;row.new_signals=row.new_signals+1 end end
   end
   for _,c in ipairs(cands) do local near=false;for _,p in pairs(placed) do if p.rail_layer==c.rail_layer and (p.position.x-c.position.x)^2+(p.position.y-c.position.y)^2<case.signal_spacing*case.signal_spacing then near=true;break end end
    if not near and s.can_place_entity(c) then local e=s.create_entity(c);if e then placed[#placed+1]=e;row.new_signals=row.new_signals+1 end end
   end
  end
  log("BUILD_END "..case.id.." complete="..tostring(row.build_complete).." missing="..#row.path_missing);row.surface=s.name;results.cases[#results.cases+1]=row;inv.destroy()
 end
end)
script.on_nth_tick(60,function()
 for _,row in ipairs(results.cases) do
  if row.build_complete then
   local s=game.surfaces[row.surface];row.signals={};row.removed_nonworking={}
   for _,e in pairs(s.find_entities_filtered{type={'rail-signal','rail-chain-signal'}}) do
    if e.status~=defines.entity_status.working then row.removed_nonworking[#row.removed_nonworking+1]={name=e.name,position=e.position,direction=e.direction,rail_layer=e.rail_layer,status=e.status};e.destroy() else row.signals[#row.signals+1]={name=e.name,position=e.position,direction=e.direction,rail_layer=e.rail_layer,status=e.status} end
   end
   local inv=game.create_inventory(1);local bp=inv[1];bp.set_stack{name='blueprint'};bp.create_blueprint{surface=s,force='player',area={{-512,-512},{512,512}},always_include_tiles=false,include_entities=true};bp.label=row.id;row.blueprint=bp.export_stack();row.entities=bp.get_blueprint_entities();inv.destroy()
  end
 end
 helpers.write_file('result.json',helpers.table_to_json(results),false);script.finish_test(true)
end)
