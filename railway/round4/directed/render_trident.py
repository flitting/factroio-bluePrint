"""Native connectivity schematic and actual fork-degree closeups."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
proof=json.loads((HERE/'trident-native-proof.json').read_text());data={}
for name,summary in [('reference','round4/reference-graphs.json'),('trident','round4/directed/trident-structural-audit.json')]:
 s=json.loads((ROOT/summary).read_text());raw=json.loads((ROOT/s['evidence_directory']/'script-output/result.json').read_text())
 wanted='r3-sig-turbine2-dense2' if name=='reference' else 'r4-dir-trident32-32'
 data[name]=next(c for c in raw['cases'] if c['id']==wanted)
colors={'ground':'#657086','high':'#b6781f','ramp':'#2d6cbd'}
def draw(ax,c,zoom=None):
 rails={r['id']:r for r in c['rails']};edges=set()
 for r in rails.values():
  for e in r['ends']:
   for q in e['connections']:
    if q in rails:edges.add(tuple(sorted([r['id'],q])))
 for a,b in sorted(edges,key=lambda e:any('elevated' in rails[q]['name'] for q in e)):
  ra,rb=rails[a],rails[b];k='ramp' if 'rail-ramp' in [ra['name'],rb['name']] else 'high' if any('elevated' in r['name'] for r in [ra,rb]) else 'ground'
  ax.plot([ra['position']['x'],rb['position']['x']],[ra['position']['y'],rb['position']['y']],color=colors[k],lw=.7 if not zoom else 1.4,solid_capstyle='round')
 if zoom:
  p=zoom['native_trunk_position'];ax.set_xlim(p['x']-27,p['x']+27);ax.set_ylim(p['y']-10,p['y']+42)
  ax.scatter([p['x']],[p['y']],s=45,color='#172239',zorder=10)
  ax.annotate('Common trunk',xy=(p['x'],p['y']),xytext=(p['x']+7,p['y']-6),fontsize=9,color='#172239',arrowprops={'arrowstyle':'-','color':'#172239','lw':1})
 ax.invert_yaxis();ax.set_aspect('equal');ax.set_facecolor('white');ax.grid(lw=.4,alpha=.15);ax.tick_params(labelsize=8)
 for sp in ax.spines.values():sp.set_color('#d5d9e1')
fig=plt.figure(figsize=(14,10),facecolor='#f6f7fa');g=fig.add_gridspec(2,2,width_ratios=[1.7,1],left=.05,right=.96,bottom=.17,top=.86,hspace=.42,wspace=.24)
main=fig.add_subplot(g[:,0]);draw(main,data['trident']);main.set_title('Whole native network: 24 private leaf columns',loc='left',fontsize=13,fontweight='semibold',pad=12)
main.set_xlabel('808,934 tiles² AABB · 2,824 working signals · 12/12 OD paths',fontsize=11,labelpad=12)
for ax,key,pidx,title in [(fig.add_subplot(g[0,1]),'reference',0,'Reference: 2 native successors'),(fig.add_subplot(g[1,1]),'trident',1,'Trident: 3 native successors')]:
 draw(ax,data[key],proof['cases'][pidx]['first_forks'][0]);ax.set_title(title,loc='left',fontsize=12,fontweight='semibold',pad=10)
 ax.set_xlabel('Closeup: north entry first split',fontsize=9)
fig.suptitle('A true three-way fork and merge network',fontsize=21,fontweight='semibold',x=.05,ha='left',y=.97)
fig.text(.05,.925,'All four first entry forks and all four final exit merges have three native neighbors, verified through the engine.',fontsize=11,color='#5a657a')
fig.text(.05,.9,'Native blueprint schematic — not an in-game screenshot. Panels use different scales; rail-center curves are approximated.',fontsize=10,color='#5a657a')
fig.legend([Line2D([0],[0],color=colors[k],lw=3) for k in ['ground','high','ramp']],['Ground rails','Elevated rails','Ramps'],loc='lower left',bbox_to_anchor=(.04,.047),ncol=3,frameon=False,fontsize=10)
fig.text(.05,.03,'Blueprint: r4-dir-trident32-32. Native degree evidence: trident-native-proof.json. Signals and supports are omitted from this drawing.',fontsize=9,color='#69758b')
fig.savefig(HERE/'trident-native-structure.png',dpi=160,facecolor=fig.get_facecolor());plt.close(fig)
