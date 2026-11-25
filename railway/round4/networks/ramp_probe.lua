local s,ramps
script.on_init(function()
 s=game.surfaces[1];s.generate_with_lab_tiles=true;s.request_to_generate_chunks({0,0},3);s.force_generate_chunk_requests();ramps={}
 for d=0,12,4 do local e=s.create_entity{name='rail-ramp',position={1+d*4,0},direction=d,force='player'};ramps[#ramps+1]=e
  for _,dx in ipairs({-9,9}) do for _,nm in ipairs({'straight-rail','elevated-straight-rail'}) do local p={x=e.position.x,y=e.position.y};p[d%8==0 and 'y' or 'x']=p[d%8==0 and 'y' or 'x']+dx;s.create_entity{name=nm,position=p,direction=d%8,force='player'} end end
 end
end)
script.on_nth_tick(2,function()
 local out={ramps={},rails={}};for _,e in ipairs(ramps) do local ends={};for rd=0,1 do ends[#ends+1]=e.get_rail_end(rd) end;local con={};for rd=0,1 do for cd=0,2 do local z,zd=e.get_connected_rail{rail_direction=rd,rail_connection_direction=cd};if z then con[#con+1]={rd=rd,cd=cd,name=z.name,pos=z.position,zd=zd} end end end;out.ramps[#out.ramps+1]={direction=e.direction,pos=e.position,ends=ends,connections=con} end
 for _,e in ipairs(s.find_entities_filtered{type={'straight-rail','elevated-straight-rail'}}) do out.rails[#out.rails+1]={name=e.name,pos=e.position,ends={e.get_rail_end(0),e.get_rail_end(1)}} end
 helpers.write_file('result.json',helpers.table_to_json(out),false);script.finish_test(true)
end)
