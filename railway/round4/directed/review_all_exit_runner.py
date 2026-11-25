"""Add assertions and observation-only evidence to the new all-exit fixture."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
H=ROOT/'round4/blockage-all';p=H/'bank.lua'
assert p.resolve()==p.absolute()
base=ROOT/'round4/protocol/bank.lua';frozen=hashlib.sha256(base.read_bytes()).hexdigest()
s=p.read_text();before=hashlib.sha256(s.encode()).hexdigest()
if 'block_signal_samples' not in s:
 s=s.replace('local block_controllers={};local block_history={};local queue_head_samples={}', 'local block_controllers={};local block_history={};local queue_head_samples={}\nlocal block_signal_samples={};local signal_state_names={};for k,v in pairs(defines.signal_state or {}) do signal_state_names[v]=k end')
 s=s.replace("block_controllers[#block_controllers+1]={cb=cb,signal=sig,side=names[side]}","block_controllers[#block_controllers+1]={cb=cb,signal=sig,side=names[side],side_index=side,offset=offset}")
 old=" log('TRAFFIC_RAILS_READY');for i=1,7 do"
 new=""" assert(#block_controllers==4,'all-exit fixture must control exactly four signals')
 local seen_exits={};for _,b in ipairs(block_controllers) do
  assert(not seen_exits[b.side],'duplicate controlled exit');seen_exits[b.side]=true
  local first=assert(first_exit_signals[b.side_index],'missing first exit signal')
  assert(b.offset==first.offset and b.signal.position.x==first.position.x and b.signal.position.y==first.position.y,'controller is not on first exit signal')
 end
 for _,name in ipairs(names) do assert(seen_exits[name],'uncontrolled exit '..name) end
 log('TRAFFIC_RAILS_READY');for i=1,7 do"""
 assert s.count(old)==1;s=s.replace(old,new)
 old=' result.block_history=block_history;result.queue_head_samples=queue_head_samples'
 new=""" result.block_history=block_history;result.queue_head_samples=queue_head_samples
 result.block_signal_samples=block_signal_samples;result.signal_state_names=signal_state_names;result.block_controller_count=#block_controllers
 result.all_exit_head_proxy_note='The single-blocked-destination/open-next-destination proxy does not apply when every exit is blocked.'
 result.controlled_exits={};for _,b in ipairs(block_controllers) do result.controlled_exits[#result.controlled_exits+1]={exit=b.side,offset=b.offset,signal_position=b.signal.position} end"""
 assert s.count(old)==1;s=s.replace(old,new)
 old=' -- Physical queue-head observations only.'
 new=""" if CONFIG.block_enabled and (tick==CONFIG.block_start+2 or tick==CONFIG.block_start+120 or tick==math.floor((CONFIG.block_start+CONFIG.block_end)/2) or tick==CONFIG.block_end-1 or tick==CONFIG.block_end+2 or tick==CONFIG.block_end+120) then
  local states={};for _,b in ipairs(block_controllers) do states[#states+1]={exit=b.side,command_closed=b.cb.enabled,signal_state=b.signal.signal_state,signal_state_name=signal_state_names[b.signal.signal_state]} end
  block_signal_samples[#block_signal_samples+1]={tick=tick,states=states}
 end
 -- Physical queue-head observations only."""
 assert s.count(old)==1;s=s.replace(old,new)
 p.write_text(s)
runner=H/'run.py';s=runner.read_text()
if 'closure_commands_verified' not in s:
 old="            raw=bank.run_case(c,identity,a.timeout);r=bank.summarize(raw)"
 new="""            raw=bank.run_case(c,identity,a.timeout);r=bank.summarize(raw)
            expected=sorted((tick,side,closed) for tick,closed in [(c['block_start'],True),(c['block_end'],False)] for side in 'NESW')
            actual=sorted((e['tick'],e['exit'],e['closed']) for e in raw['block_history'])
            assert raw['block_controller_count']==4 and actual==expected, 'all-four closure command evidence mismatch'
            assert {e['exit'] for e in raw['controlled_exits']}==set('NESW')
            assert all(e['offset']==c['exit_clearance'] for e in raw['controlled_exits'])
            midpoint=(c['block_start']+c['block_end'])//2
            mid=next(s for s in raw['block_signal_samples'] if s['tick']==midpoint)
            r.update(closure_commands_verified=True,controlled_exits=raw['controlled_exits'],block_signal_samples=raw['block_signal_samples'],all_four_midpoint_native_red=all(s.get('signal_state_name') in ('closed','reserved_by_circuit_network') for s in mid['states']),all_four_midpoint_circuit_reserved=all(s.get('signal_state_name')=='reserved_by_circuit_network' for s in mid['states']))"""
 assert s.count(old)==1;s=s.replace(old,new);runner.write_text(s)
ast.parse(runner.read_text())
assert hashlib.sha256(base.read_bytes()).hexdigest()==frozen
review={'scope':'Static review before the one requested native all-exit recovery case; no additional engine run.','all_exit_lua_before_sha256':before,'all_exit_lua_after_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'frozen_main_protocol_sha256_unchanged':frozen,'all_exits_build_assertions':'Exactly 4 unique N/E/S/W controllers, each wired to that side\'s first outlet signal.','observations':'Native signal state names/numbers sampled near transitions and at closure midpoint. Pre-reserved trains may legitimately pass during native signal propagation; no forced state mutation.','runner_assertions':'8 expected close/open commands at3600/7200, four first-signal offsets8, exact side set.','traffic_actions':'Same as root all-exit fixture: native constant combinator and rail signal close condition. Added assertions/observations only; schedules, movement, spawning, retirement and frozen capacity protocol unchanged.','python_syntax':'ast.parse passed','lua_syntax':'Small reviewed edits; actual requested engine test will compile it.','inherited_hol_proxy':'Single-blocked-destination/open-next proxy not meaningful for ALL; explicitly annotated in result.'}
(H/'review.json').write_text(json.dumps(review,indent=2));print(json.dumps(review,indent=2))
