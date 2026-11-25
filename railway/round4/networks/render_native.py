"""Native adjacency schematic; not game sprites or a game screenshot."""
import argparse,json,html
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
p=argparse.ArgumentParser();p.add_argument('id');p.add_argument('--output',default='native-layout');a=p.parse_args()
selected=None;summary=None
for f in H.glob('*graph*.json'):
 d=json.loads(f.read_text())
 if not isinstance(d,dict) or 'evidence_directory' not in d:continue
 for c in d.get('cases',[]):
  if c['id']==a.id:
   raw=json.loads((ROOT/d['evidence_directory']/'script-output/result.json').read_text());selected=next(z for z in raw['cases'] if z['id']==a.id);summary=c
if selected is None:raise SystemExit('No native graph for '+a.id)
rs={r['id']:r for r in selected['rails']};bound=max(abs(x) for r in rs.values() for x in r['position'].values())+8
scale=700/(2*bound);cx,cy=450,494
xy=lambda p:(cx+p['x']*scale,cy+p['y']*scale)
color=lambda e:'#397cc5' if e['name']=='rail-ramp' else '#c28c2d' if e['name'].startswith('elevated') else '#455667'
S=['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="1000" viewBox="0 0 900 1000">','<rect width="900" height="1000" fill="#f6f8fa"/>','<style>text{font-family:"Noto Sans CJK SC","Microsoft YaHei",sans-serif;fill:#1c2c3a}</style>','<text x="40" y="42" font-size="27" font-weight="700">新的四象限定向连接</text>','<text x="40" y="74" font-size="16">Factorio 2.1.25 原生轨道图 · 结构示意，非游戏截图</text>']
for x in range(-int(bound)//32*32,int(bound)+1,32):
 xx=cx+x*scale;yy=cy+x*scale
 S.append(f'<path d="M {xx:.2f} 135 V 850 M 100 {yy:.2f} H 800" stroke="#e3e9ee" stroke-width="1"/>')
for layer in [False,True]:
 seen=set()
 for uid,r in rs.items():
  if r['name'].startswith('elevated')!=layer and r['name']!='rail-ramp':continue
  for end in r['ends']:
   for rid in end['connections']:
    edge=tuple(sorted((uid,rid)))
    if rid not in rs or edge in seen:continue
    z=rs[rid]
    if 'rail-ramp' not in (r['name'],z['name']) and z['name'].startswith('elevated')!=layer:continue
    seen.add(edge);x,y=xy(r['position']);xx,yy=xy(z['position']);co='#397cc5' if 'rail-ramp' in (r['name'],z['name']) else color(r)
    S.append(f'<path d="M{x:.2f},{y:.2f} L{xx:.2f},{yy:.2f}" stroke="{co}" stroke-width="3.0" stroke-linecap="round" fill="none"/>')
for r in rs.values():
 if r['name']=='rail-ramp':
  x,y=xy(r['position']);S.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.8" fill="#397cc5" stroke="#f6f8fa" stroke-width="1"/>')
for sig in selected['signals']:
 x,y=xy(sig['position']);S.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="1.3" fill="#14916b" opacity="0.7"/>')
for text,x,y in [('N',450,126),('S',450,884),('W',70,500),('E',820,500)]:S.append(f'<text x="{x}" y="{y}" font-size="23" font-weight="700" text-anchor="middle">{text}</text>')
for k,(label,co) in enumerate([('地面轨道','#455667'),('高架轨道','#c28c2d'),('坡道','#397cc5'),('信号灯','#14916b')]):
 x=45+k*210;S.append(f'<path d="M{x},924 h28" stroke="{co}" stroke-width="5"/><text x="{x+38}" y="930" font-size="16">{label}</text>')
S.append(f'<text x="40" y="966" font-size="15">四向各一进一出 · {summary["signals"]} 个信号 · AABB {summary["area"]:,.0f} 格² · 12 OD 原生可达</text>')
S.append('</svg>');out=H/(a.output+'.svg');out.write_text('\n'.join(S));
try:
 import cairosvg;cairosvg.svg2png(url=str(out),write_to=str(H/(a.output+'.png')),output_width=1800,output_height=2000)
except ImportError:
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.collections import LineCollection
 from matplotlib import font_manager
 from matplotlib.lines import Line2D
 font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
 plt.rcParams.update({'font.family':'Noto Sans CJK JP'})
 fig=plt.figure(figsize=(9,10),facecolor='#f6f8fa');ax=fig.add_axes([.09,.145,.82,.73],facecolor='#f6f8fa');ax.set_aspect('equal');ax.set_xlim(-bound,bound);ax.set_ylim(bound,-bound);ax.set_axis_off()
 for q in range(-int(bound)//32*32,int(bound)+1,32):ax.axhline(q,color='#e3e9ee',lw=.5,zorder=0);ax.axvline(q,color='#e3e9ee',lw=.5,zorder=0)
 groups={'ground':[],'high':[],'ramp':[]};seen=set()
 for uid,r in rs.items():
  for end in r['ends']:
   for rid in end['connections']:
    edge=tuple(sorted((uid,rid)))
    if rid not in rs or edge in seen:continue
    seen.add(edge);z=rs[rid];kind='ramp' if 'rail-ramp' in (r['name'],z['name']) else 'high' if r['name'].startswith('elevated') else 'ground'
    groups[kind].append([(r['position']['x'],r['position']['y']),(z['position']['x'],z['position']['y'])])
 for i,(kind,co) in enumerate([('ground','#455667'),('high','#c28c2d'),('ramp','#397cc5')]):
  if i:ax.add_collection(LineCollection(groups[kind],colors='#f6f8fa',linewidths=5,zorder=i*2))
  ax.add_collection(LineCollection(groups[kind],colors=co,linewidths=2.3,zorder=i*2+1))
 ax.scatter([z['position']['x'] for z in selected['signals']],[z['position']['y'] for z in selected['signals']],s=2.2,color='#14916b',zorder=8)
 fig.text(.045,.958,'新的四象限定向连接',fontsize=24,weight='bold',color='#1c2c3a');fig.text(.045,.926,'Factorio 2.1.25 原生轨道图 · 结构示意，非游戏截图',fontsize=11,color='#455667')
 for label,x,y in [('N',.5,.89),('S',.5,.125),('W',.06,.51),('E',.94,.51)]:fig.text(x,y,label,ha='center',fontsize=17,weight='bold')
 handles=[Line2D([0],[0],color=co,lw=3,label=lab) for lab,co in [('地面轨道','#455667'),('高架轨道','#c28c2d'),('坡道','#397cc5'),('信号灯','#14916b')]]
 fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.069),ncol=4,frameon=False,fontsize=11)
 fig.text(.045,.039,f'四向各一进一出 · {summary["signals"]} 个信号 · AABB {summary["area"]:,.0f} 格² · 12 OD 原生可达',fontsize=11)
 fig.savefig(H/(a.output+'.png'),dpi=180,facecolor=fig.get_facecolor());plt.close(fig)
(H/(a.output+'-provenance.json')).write_text(json.dumps({'id':a.id,'summary':summary,'rendering':'Native rail-center adjacency schematic, not exact curve sprite geometry and not an in-game screenshot.','script':'round4/networks/render_native.py'},indent=2));print(out)
