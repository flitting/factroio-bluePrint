local function aabb(b)
 local cx=(b.left_top.x+b.right_bottom.x)/2;local cy=(b.left_top.y+b.right_bottom.y)/2
 local hx=(b.right_bottom.x-b.left_top.x)/2;local hy=(b.right_bottom.y-b.left_top.y)/2
 local angle=(b.orientation or 0)*math.pi*2;local c=math.abs(math.cos(angle));local s=math.abs(math.sin(angle))
 local wx=c*hx+s*hy;local wy=s*hx+c*hy
 return {left_top={x=cx-wx,y=cy-wy},right_bottom={x=cx+wx,y=cy+wy}}
end
local surfaces={};local result={cases={},engine=nil,entity_status={}}
local vec={{0,-1},{1,0},{0,1},{-1,0}}
local function place(s,spec) spec.force='player';assert(s.can_place_entity(spec),'illegal entity '..spec.name);return assert(s.create_entity(spec)) end
script.on_init(function()
 result.engine=script.active_mods
 for k,v in pairs(defines.entity_status) do result.entity_status[tostring(v)]=k end
 for _,case in ipairs(CONFIG.cases) do
  local s=game.create_surface(case.id,{width=case.surface_size or 4096,height=case.surface_size or 4096,autoplace_controls={}});s.generate_with_lab_tiles=true
  s.request_to_generate_chunks({0,0},case.core_chunk_radius or 16);s.force_generate_chunk_requests()
  for _,e in pairs(s.find_entities()) do e.destroy() end
  local inv=game.create_inventory(1);local bp=inv[1];bp.set_stack{name='blueprint'};assert(bp.import_stack(case.blueprint)==0)
  local ghosts=bp.build_blueprint{surface=s,force='player',position={0,0},build_mode=defines.build_mode.normal}
  assert(#ghosts==case.entities,'ghost count mismatch '..case.id)
  for pass=1,20 do local n=0;for _,g in pairs(ghosts) do if g.valid then local _,e=g.revive{};if e then n=n+1 end end end;if n==0 then break end end
  for _,g in pairs(ghosts) do assert(not g.valid,'unbuilt '..case.id) end;inv.destroy()
  local core=s.find_entities_filtered{force='player'};local rs=s.find_entities_filtered{name='straight-rail'}
  local xmin,xmax,ymin,ymax=1e9,-1e9,1e9,-1e9
  for _,r in pairs(rs) do xmin=math.min(xmin,r.position.x);xmax=math.max(xmax,r.position.x);ymin=math.min(ymin,r.position.y);ymax=math.max(ymax,r.position.y) end
  local edges={{},{},{},{}}
  for _,r in pairs(rs) do local p=r.position;if p.y==ymin then edges[1][#edges[1]+1]=r end;if p.x==xmax then edges[2][#edges[2]+1]=r end;if p.y==ymax then edges[3][#edges[3]+1]=r end;if p.x==xmin then edges[4][#edges[4]+1]=r end end
  local ports={};local stops={}
  for side=1,4 do
   assert(#edges[side]==2,'not two ports '..case.id)
   table.sort(edges[side],function(a,b) if side==1 or side==3 then return a.position.x<b.position.x else return a.position.y<b.position.y end end)
   ports[side]={}
   for _,r in ipairs(edges[side]) do for off=0,272,32 do s.request_to_generate_chunks({x=r.position.x+vec[side][1]*off,y=r.position.y+vec[side][2]*off},1) end end
   s.force_generate_chunk_requests()
   for lane,r in ipairs(edges[side]) do local p=r.position;ports[side][lane]=p
    for off=2,240,2 do place(s,{name='straight-rail',position={x=p.x+vec[side][1]*off,y=p.y+vec[side][2]*off},direction=r.direction}) end
   end
   local outlet=(side==1 or side==2) and 2 or 1;local p=ports[side][outlet];local dx,dy=vec[side][1],vec[side][2]
   local stop=place(s,{name='train-stop',position={x=p.x+dx*200-dy*2,y=p.y+dy*200+dx*2},direction=(side-1)*4});stop.backer_name='OUT-'..side;stops[side]=stop
  end
  surfaces[#surfaces+1]={s=s,core=core,ports=ports,stops=stops};result.cases[#result.cases+1]={id=case.id,normal_build_complete=true,entities=#core,core_straight_bounds={xmin,xmax,ymin,ymax}}
 end
end)
script.on_event(defines.events.on_tick,function(event)
 if event.tick~=60 then return end
 for i,c in ipairs(surfaces) do
  local row=result.cases[i];row.non_working={};row.signal_counts={};row.signals={};row.paths={};row.all_12_od=true
  for _,e in ipairs(c.core) do if e.type=='rail-signal' or e.type=='rail-chain-signal' then
   local status=result.entity_status[tostring(e.status)];row.signal_counts[status]=(row.signal_counts[status] or 0)+1
   local r={name=e.name,position=e.position,direction=e.direction,rail_layer=e.rail_layer,status=status,state=e.signal_state};row.signals[#row.signals+1]=r
   if status~='working' then row.non_working[#row.non_working+1]=r end
  end end
  row.all_signals_working=#row.non_working==0
  row.rails={};local core_rail_ids={};local block_representatives={};local segment_representatives={}
  local minx,miny,maxx,maxy=1e9,1e9,-1e9,-1e9;local occupied={};local cellcount=0
  for _,e in ipairs(c.core) do
   local b=aabb(e.bounding_box);local secondary=e.secondary_bounding_box
   if secondary then local q=aabb(secondary);b.left_top.x=math.min(b.left_top.x,q.left_top.x);b.left_top.y=math.min(b.left_top.y,q.left_top.y);b.right_bottom.x=math.max(b.right_bottom.x,q.right_bottom.x);b.right_bottom.y=math.max(b.right_bottom.y,q.right_bottom.y) end
   minx=math.min(minx,b.left_top.x);miny=math.min(miny,b.left_top.y);maxx=math.max(maxx,b.right_bottom.x);maxy=math.max(maxy,b.right_bottom.y)
   for x=math.floor(b.left_top.x),math.ceil(b.right_bottom.x)-1 do for y=math.floor(b.left_top.y),math.ceil(b.right_bottom.y)-1 do local key=x..','..y;if not occupied[key] then occupied[key]=true;cellcount=cellcount+1 end end end
  end
  row.bounds={min_x=minx,min_y=miny,max_x=maxx,max_y=maxy,width=maxx-minx,height=maxy-miny,area=(maxx-minx)*(maxy-miny)}
  row.bounding_box_union_tiles=cellcount
  row.occupancy_note='orientation-correct primary/secondary bbox projected tile envelope; same definition as prior rounds'
  for _,e in ipairs(c.core) do if string.find(e.type,'rail') and e.type~='rail-signal' and e.type~='rail-chain-signal' and e.type~='rail-support' then
   core_rail_ids[e.unit_number]=true
   local block_id,segment_id
   for k,r in ipairs(block_representatives) do if e.is_rail_in_same_rail_block_as(r) then block_id=k;break end end
   if not block_id then block_representatives[#block_representatives+1]=e;block_id=#block_representatives end
   for k,r in ipairs(segment_representatives) do if e.is_rail_in_same_rail_segment_as(r) then segment_id=k;break end end
   if not segment_id then segment_representatives[#segment_representatives+1]=e;segment_id=#segment_representatives end
   local rail={id=e.unit_number,name=e.name,position=e.position,direction=e.direction,length=e.rail_length,block=block_id,segment=segment_id,ends={}}
   for rd=0,1 do
    local ending=e.get_rail_end(rd);local outgoing={}
    for cd=0,2 do local next=e.get_connected_rail{rail_direction=rd,rail_connection_direction=cd};if next then outgoing[#outgoing+1]=next.unit_number end end
    local loc=ending.out_signal_location;local can=c.s.can_place_entity{name='rail-signal',position=loc.position,direction=loc.direction,rail_layer=loc.rail_layer,force='player'}
    rail.ends[#rail.ends+1]={rd=rd,out_signal=loc,in_signal=ending.in_signal_location,can_place_signal=can,connections=outgoing}
   end
   row.rails[#row.rails+1]=rail
  end end
  row.native_core_rail_blocks=#block_representatives;row.native_core_rail_segments=#segment_representatives
  for o=1,4 do for d=1,4 do if o~=d then
   local lane=(o==1 or o==2) and 1 or 2;local p=c.ports[o][lane];local dx,dy=vec[o][1],vec[o][2];local direction=(o*4+4)%16
   local loco=place(c.s,{name='locomotive',position={x=p.x+dx*120,y=p.y+dy*120},direction=direction})
   for k=1,4 do place(c.s,{name='cargo-wagon',position={x=p.x+dx*(120+7*k),y=p.y+dy*(120+7*k)},direction=direction}) end
   assert(#loco.train.carriages==5,'1-4 consist')
   local path=game.train_manager.request_train_path{train=loco.train,goals={c.stops[d]},type='path',return_path=true}
   local railpath={}
   if path.found_path then for _,r in ipairs(path.path) do if core_rail_ids[r.unit_number] then railpath[#railpath+1]=r.unit_number end end end
   row.paths[#row.paths+1]={origin=o,destination=d,found=path.found_path,steps=path.steps_count,length=path.total_length,penalty=path.penalty,rails=railpath}
   if not path.found_path then row.all_12_od=false end
   for _,e in pairs(loco.train.carriages) do e.destroy() end
  end end end
 end
 helpers.write_file('result.json',helpers.table_to_json(result),false);script.finish_test(true)
end)
