"""Native construction + 12 independent 1-4 routes for selected signal candidates.

Runs one engine at a time; uses lab tiles only to accelerate map generation.
No profiler timings are collected, because other workers may run engines.
"""
import argparse, hashlib, json, pathlib, subprocess, time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def source(kind, full_paths=False):
    filename = 'audit.lua' if kind == 'audit' else 'probe_paths.lua'
    text = (ROOT / 'lua' / filename).read_text()
    # These one-line terrain fills do not affect any rail or train rule.
    text = '\n'.join(line for line in text.splitlines()
                     if not line.strip().startswith('local tiles=')
                     and not line.strip().startswith('for batch=1,5 do')) + '\n'
    text = text.replace("s.request_to_generate_chunks", "s.generate_with_lab_tiles=true\n s.request_to_generate_chunks", 1)
    if kind == 'drive':
        if full_paths:
            text = text.replace('return_path=false', 'return_path=true')
            probe = 'active.path_probe={found_path=path.found_path,steps_count=path.steps_count,total_length=path.total_length,penalty=path.penalty}'
            text = text.replace(probe, probe + ";active.path_rails={};for _,r in ipairs(path.path) do active.path_rails[#active.path_rails+1]={name=r.name,position=r.position,direction=r.direction} end")
        text = text.replace("game.forces.player.technologies['braking-force-7'].researched=true",
                            "for k=1,7 do game.forces.player.technologies['braking-force-'..k].researched=true end")
        text = text.replace(' inv.destroy()', " assert(#ghosts==case.count,'blueprint ghost count')\n for _,g in pairs(ghosts) do assert(not g.valid,'unbuilt blueprint entity') end\n inv.destroy()", 1)
        text = text.replace(" helpers.write_file('path-probes.json',helpers.table_to_json(result),false)\n script.finish_test(true)",
                            " local passed=(result.rolling_stock_damage_events or 0)==0\n for _,c in pairs(result.cases) do if #c.trials~=12 then passed=false end;for _,t in pairs(c.trials) do if not t.completed or t.carriages~=5 or not t.path_probe.found_path then passed=false end end end\n result.passed=passed\n helpers.write_file('path-probes.json',helpers.table_to_json(result),false)\n script.finish_test(passed)")
        text += "script.on_event(defines.events.on_entity_damaged,function(e) if e.entity.type=='locomotive' or e.entity.type=='cargo-wagon' then result.rolling_stock_damage_events=(result.rolling_stock_damage_events or 0)+1 end end)\n"
    return text


def run(kind, cases, full_paths=False):
    control = source(kind, full_paths)
    case_text = 'return {' + ','.join('{id=' + json.dumps(c['id']) + ',count=' + str(c['count']) + ',blueprint=' + json.dumps(c['blueprint']) + '}' for c in cases) + '}'
    digest = hashlib.sha256((control + case_text).encode()).hexdigest()
    out = HERE / 'validation' / f'{kind}-{digest[:16]}'
    scene = out / 'scenarios/probe'
    scene.mkdir(parents=True, exist_ok=True)
    (out / 'mods').mkdir(exist_ok=True)
    (scene / 'control.lua').write_text(control)
    (scene / 'cases.lua').write_text(case_text)
    (out / 'config.ini').write_text(f'[path]\nread-data={ROOT}/engine/factorio/data\nwrite-data={out}\n')
    (out / 'mods/mod-list.json').write_text(json.dumps({'mods': [{'name': n, 'enabled': True} for n in ['base', 'quality', 'elevated-rails', 'space-age']]}))
    command = [str(ROOT / 'engine/factorio/bin/x64/factorio'), '-c', str(out / 'config.ini'), '--mod-directory', str(out / 'mods'), '--test-scenario', 'probe', '--test-ticks', '2' if kind == 'audit' else '200000']
    started = time.monotonic()
    with (out / 'run.log').open('w') as log:
        process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=240)
    request = {'case_sha256': digest, 'control_sha256': hashlib.sha256(control.encode()).hexdigest(), 'command': command, 'exit_code': process.returncode, 'wall_seconds': time.monotonic() - started}
    (out / 'request.json').write_text(json.dumps(request, indent=2))
    if process.returncode:
        raise RuntimeError(f'Native {kind} failed: {out}/run.log')
    result = json.loads((out / 'script-output' / ('audit.json' if kind == 'audit' else 'path-probes.json')).read_text())
    result['evidence_directory'] = str(out.relative_to(ROOT))
    return result


def component_sizes(case):
    rails = {r['unit_number']: r for r in case['rails']}
    seen, sizes = set(), []
    for first in rails:
        if first in seen:
            continue
        seen.add(first)
        queue, count = [first], 0
        while queue:
            rail = queue.pop()
            count += 1
            for conn in rails[rail]['connections']:
                if conn['to'] not in seen:
                    seen.add(conn['to'])
                    queue.append(conn['to'])
        sizes.append(count)
    return sorted(sizes, reverse=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('ids', nargs='+')
    parser.add_argument('--output', default='validation-summary.json')
    parser.add_argument('--full-paths', action='store_true')
    args = parser.parse_args()
    cases = [{'id': i, 'count': len(json.loads((ROOT / 'blueprints' / f'{i}.json').read_text())['blueprint']['entities']), 'blueprint': (ROOT / 'blueprints' / f'{i}.txt').read_text().strip()} for i in args.ids]
    audit = run('audit', cases, args.full_paths)
    summary = {'audit_evidence': audit['evidence_directory'], 'engine': audit['engine'], 'cases': []}
    for case in audit['cases']:
        assert case['normal_blueprint_build_complete'], case['id']
        sizes = component_sizes(case)
        assert len(sizes) == 1, (case['id'], sizes)
        summary['cases'].append({k: case[k] for k in ['id', 'expected_entities', 'revived', 'normal_blueprint_build_complete', 'counts', 'bounds', 'bounding_box_union_tiles', 'rail_length', 'rail_block_count', 'rail_segment_count']})
        summary['cases'][-1]['connected_component_sizes'] = sizes
    drive = run('drive', cases, args.full_paths)
    summary['drive_evidence'] = drive['evidence_directory']
    summary['drive_passed'] = drive['passed']
    summary['rolling_stock_damage_events'] = drive.get('rolling_stock_damage_events', 0)
    for row, driven in zip(summary['cases'], drive['cases']):
        row['all_od_native_found_path'] = all(t['path_probe']['found_path'] for t in driven['trials'])
        row['independent_od_completed'] = sum(t['completed'] for t in driven['trials'])
        row['independent_od_trials'] = len(driven['trials'])
        row['static_path_steps_sum'] = sum(t['path_probe']['steps_count'] for t in driven['trials'])
        row['static_path_length_mean'] = sum(t['path_probe']['total_length'] for t in driven['trials']) / len(driven['trials'])
        row['independent_transit_seconds_mean'] = sum(t['elapsed_ticks'] for t in driven['trials']) / len(driven['trials']) / 60
    (HERE / args.output).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
