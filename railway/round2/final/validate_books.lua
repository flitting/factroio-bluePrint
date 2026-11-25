script.on_init(function()
 local result={engine=script.active_mods.base,mods=script.active_mods,books={}}
 for _,b in ipairs(CONFIG.books) do
  local inv=game.create_inventory(1);local stack=inv[1];stack.set_stack{name='blueprint-book'}
  local status=stack.import_stack(b.code);assert(status==0,'book import failed');assert(stack.is_blueprint_book)
  assert(stack.label==b.label,'book label mismatch')
  local contents=stack.get_inventory(defines.inventory.item_main);local n=0;local total=0;local items={}
  for i=1,#contents do if contents[i].valid_for_read then
   n=n+1;local expected=b.entries[n];assert(expected,'unexpected book entry')
   local leaf=contents[i];assert(leaf.is_blueprint,'non-blueprint entry')
   assert(leaf.label==expected.label,'entry label mismatch')
   local entities=leaf.get_blueprint_entities() or {};assert(#entities==expected.entities,'entity count mismatch')
   total=total+#entities;items[#items+1]={source_id=expected.id,slot=i,label=leaf.label,entities=#entities,expected_entities=expected.entities,matched=true}
  end end
  assert(n==#b.entries,'book entry count mismatch');assert(total==b.total_entities,'book total entities mismatch')
  result.books[#result.books+1]={file=b.file,label=stack.label,import_status=status,entry_count=n,total_entities=total,entries=items,passed=true}
  inv.destroy()
 end
 result.passed=true;helpers.write_file('result.json',helpers.table_to_json(result),false);script.finish_test(true)
end)
