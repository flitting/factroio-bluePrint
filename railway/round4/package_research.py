#!/usr/bin/env python3
"""Archive completed round4 evidence and source, excluding engine/game assets."""
from pathlib import Path
import hashlib,json,zipfile

ROOT=Path(__file__).resolve().parents[1];HERE=ROOT/'round4'
DEST=ROOT.parents[1]/'railway-optimization-round4.zip'

def sha_bytes(b):return hashlib.sha256(b).hexdigest()

def main():
    result=json.loads((HERE/'final/results-summary.json').read_text());assert result['publication_gate_complete']
    publication=json.loads((HERE/'publish/publication.json').read_text());assert publication['branch_verified']
    selected={}
    skip_parts={'__pycache__','temp'}
    def add(p):
        if not p.is_file() or p.is_symlink():return
        rel=p.relative_to(ROOT)
        if any(x in skip_parts for x in rel.parts):return
        if p.suffix in ['.pyc','.tmp']:return
        if rel.parts[:2]==('round4','publish') and p.name not in ['manifest.json','publication.json','binary-blobs.json','pr-body.md']:return
        if str(rel)=='round4/final/analysis-progress.json':return
        if p.name in ['report-preview.png','report-mobile-preview.png']:return
        # Preserve exact blueprint source data, not entire unrelated forum webpages.
        if 'sources' in rel.parts and p.suffix.lower() in ['.html','.htm']:return
        selected[str(rel)]=p
    for p in HERE.rglob('*'):add(p)
    for folder in ['scripts','lua']:
        for p in (ROOT/folder).rglob('*'):
            if p.suffix in ['.py','.lua','.md']:add(p)
    for folder in ['round2','round3']:
        for p in (ROOT/folder).rglob('*'):
            if not any(x in ['experiments','validation','profiles','temp','final','publish','sources','__pycache__'] for x in p.relative_to(ROOT/folder).parts) and p.suffix in ['.py','.lua']:add(p)
    add(ROOT/'round2/final/validate_books.lua')
    # Referenced old/new fixture-equivalence evidence, as well as all fourth-round native gates.
    old=ROOT/'round3/protocol/experiments/bank-r3-sig-turbine2-dense2-S1-b1811fb1b0a9f12d'
    for p in old.rglob('*'):add(p)
    for d in (ROOT/'experiments').glob('r4-*'):
        for p in d.rglob('*'):add(p)
    controls={'r3-sig-turbine2-dense2','r2-sig-stacked-cloverleaf-all4-clean','r2-sig-turbine-2-trim-all4-clean'}
    for p in (ROOT/'blueprints').iterdir():
        if p.stem.startswith('r4-') or p.stem in controls:add(p)
    readme=f'''# 铁路研究第四轮完整证据包

先打开 round4/final/report.html，或阅读 round4/final/REPORT.zh-CN.md。
导入 round4/final/junctions-round4.txt（三分叉大型研究候选与两张紧凑对照）。

本轮有 {result['search_counts']['completed_cases']} 次完成的原生流量案例、{result['search_counts']['new_exact_configurations_tested']} 种新实体配置、{result['search_counts']['new_distinct_non_signal_geometries_tested']} 种不同轨道/坡道/支撑几何；这些不是同样数量的抽象拓扑家族。
独立较长确认组：涡轮对照 {result['holdout_pair']['reference_mean']:.2f} → 三分叉 {result['holdout_pair']['trident_mean']:.2f} 列/游戏分钟，增加 {result['holdout_pair']['relative_gain_percent']:.2f}%；新方案占地约46.44倍，存在延迟、CPU与方向服务代价。

固定 Factorio Headless 2.1.25 build88022，base/quality/elevated-rails/space-age。
完整的原生配置、逐车记录、建造拒绝、执行会话中断日志、生成器与运行脚本均保留。实验目录的失败候选不是推荐成品。
不包含 Factorio 引擎或游戏资产，请将用户有权使用的固定版本安装至 engine/factorio。具体复现命令见报告。
已有相同hash的完成结果会被缓存复用；独立重跑时请使用新工作目录，并保留原证据，将对应旧experiments和CPU profiles输出移至归档后运行。

公共研究分支：{publication['branch_url']}
提交：{publication['commit_url']}
PR：{publication['pull_request_url']}

来源与版权归属记录在 round4/external/source-catalog.json。公共仓库不复制未明确许可的第三方蓝图本体；本证据包保留实际测试输入。
ARCHIVE-MANIFEST.json 给出除其自身外所有文件的SHA256。实验秒/分钟均为游戏时间，图表为原生数据/邻接示意，不是游戏截图。
'''
    extra={'PACKAGE-README.md':readme.encode()}
    entries=[]
    for rel,p in sorted(selected.items()):
        b=p.read_bytes();entries.append({'path':rel,'bytes':len(b),'sha256':sha_bytes(b)})
    for rel,b in extra.items():entries.append({'path':rel,'bytes':len(b),'sha256':sha_bytes(b)})
    manifest={'format':'round4-complete-native-evidence-v1','files':entries,'engine_assets_excluded':True,
              'git_publication':publication,'files_excluding_manifest':len(entries)}
    extra['ARCHIVE-MANIFEST.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
    with zipfile.ZipFile(DEST,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for rel,p in sorted(selected.items()):z.write(p,'railway-research-round4/'+rel)
        for rel,b in extra.items():z.writestr('railway-research-round4/'+rel,b)
    with zipfile.ZipFile(DEST) as z:
        assert z.testzip() is None
        assert len(z.infolist())==len(entries)+1
        for e in entries:
            b=z.read('railway-research-round4/'+e['path'])
            assert len(b)==e['bytes'] and sha_bytes(b)==e['sha256'],e['path']
    record={'file':str(DEST),'bytes':DEST.stat().st_size,'sha256':sha_bytes(DEST.read_bytes()),
            'files':len(entries)+1,'zip_crc_and_every_file_sha256_verified':True,
            'publication_commit':publication['commit_sha']}
    (ROOT.parents[1]/'railway-round4-archive.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record))

if __name__=='__main__':main()
