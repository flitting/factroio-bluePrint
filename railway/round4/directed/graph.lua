local surfaces={};local result={cases={},engine=nil,entity_status={}}
local vec={{0,-1},{1,0},{0,1},{-1,0}}
local function place(s,spec) spec.force='player';assert(s.can_place_entity(spec),'illegal entity '..spec.name);return assert(s.create_entity(spec)) end
script.on_init(function()
 result.engine=script.active_mods
 for k,v in pairs(defines.entity_status) do result.entity_status[tostring(v)]=k end
 for _,case in ipairs(CONFIG.cases) do
  local s=game.create_surface(case.id,{width=4096,height=4096,autoplace_controls={}});s.generate_with_lab_tiles=true
  s.request_to_generate_chunks({0,0},34);s.force_generate_chunk_requests()
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
  row.rails={}
  for _,e in ipairs(c.core) do if string.find(e.type,'rail') and e.type~='rail-signal' and e.type~='rail-chain-signal' and e.type~='rail-support' then
   local rail={id=e.unit_number,name=e.name,position=e.position,direction=e.direction,ends={}}
   for rd=0,1 do
    local ending=e.get_rail_end(rd);local outgoing={}
    for cd=0,2 do local next=e.get_connected_rail{rail_direction=rd,rail_connection_direction=cd};if next then outgoing[#outgoing+1]=next.unit_number end end
    rail.ends[#rail.ends+1]={rd=rd,out_signal=ending.out_signal_location,in_signal=ending.in_signal_location,connections=outgoing}
   end
   row.rails[#row.rails+1]=rail
  end end
  for o=1,4 do for d=1,4 do if o~=d then
   local lane=(o==1 or o==2) and 1 or 2;local p=c.ports[o][lane];local dx,dy=vec[o][1],vec[o][2];local direction=(o*4+4)%16
   local loco=place(c.s,{name='locomotive',position={x=p.x+dx*120,y=p.y+dy*120},direction=direction})
   for k=1,4 do place(c.s,{name='cargo-wagon',position={x=p.x+dx*(120+7*k),y=p.y+dy*(120+7*k)},direction=direction}) end
   assert(#loco.train.carriages==5,'1-4 consist')
   local path=game.train_manager.request_train_path{train=loco.train,goals={c.stops[d]},type='path',return_path=true}
   local railpath={}
   if path.found_path then for _,r in ipairs(path.path) do railpath[#railpath+1]=r.unit_number end end
   row.paths[#row.paths+1]={origin=o,destination=d,found=path.found_path,steps=path.steps_count,length=path.total_length,penalty=path.penalty,rails=railpath}
   if not path.found_path then row.all_12_od=false end
   for _,e in pairs(loco.train.carriages) do e.destroy() end
  end end end
 end
 helpers.write_file('result.json',helpers.table_to_json(result),false);script.finish_test(true)
end)
