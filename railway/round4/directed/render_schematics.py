"""Native-adjacency centerline preview. Deliberately not a game screenshot."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
rows={}
for f in ['round4/reference-graphs.json','round4/directed/structural-audit.json','round4/directed/packed-structural-audit.json']:
 m=json.loads((ROOT/f).read_text()); raw=json.loads((ROOT/m['evidence_directory']/'script-output/result.json').read_text())
 for c in raw['cases']:rows[c['id']]=c
cases=[('r3-sig-turbine2-dense2','Original reference: dense turbine'),('r4-dir-crossbar64-source','New crossbar: generous spacing'),('r4-dir-crossbar16-source','New crossbar: shorter rows'),('r4-dir-pack0-fwd','New crossbar: six-row packing')]
fig,axs=plt.subplots(2,2,figsize=(14,12),facecolor='#f6f7fa')
colors={'ground':'#555f74','high':'#b6781f','ramp':'#2d6cbd'}
for ax,(ident,label) in zip(axs.flat,cases):
 c=rows[ident];rails={r['id']:r for r in c['rails']};edges=set()
 for r in rails.values():
  for end in r['ends']:
   for other in end['connections']:
    if other in rails:edges.add(tuple(sorted([r['id'],other])))
 for a,b in sorted(edges,key=lambda e:any('elevated' in rails[q]['name'] for q in e)):
  ra,rb=rails[a],rails[b]
  k='ramp' if 'rail-ramp' in [ra['name'],rb['name']] else 'high' if any('elevated' in q['name'] for q in [ra,rb]) else 'ground'
  ax.plot([ra['position']['x'],rb['position']['x']],[ra['position']['y'],rb['position']['y']],color=colors[k],lw=.85 if k!='ramp' else 1.5,solid_capstyle='round')
 ax.set_aspect('equal');ax.invert_yaxis();ax.set_facecolor('white')
 ax.tick_params(labelsize=8,color='#c6cbd5');ax.grid(lw=.4,alpha=.12)
 for spine in ax.spines.values():spine.set_color('#d5d9e1')
 ax.set_title(label,loc='left',fontsize=12,pad=10,fontweight='semibold')
 ax.set_xlabel(f"{c['bounds']['area']:,.0f} tiles² AABB · {len(c['signals'])} working signals",fontsize=10,labelpad=10)
 ax.text(.02,.98,ident,transform=ax.transAxes,va='top',fontsize=8,color='#69758b',bbox={'facecolor':'white','edgecolor':'none','alpha':.8})
fig.suptitle('From native blueprints: new crossbar embeddings',fontsize=20,fontweight='semibold',x=.06,ha='left',y=.98)
fig.text(.06,.945,'Native rail adjacency schematic — not an in-game screenshot. Each panel has its own scale.',fontsize=11,color='#59657b')
fig.legend([Line2D([0],[0],color=colors[k],lw=3) for k in ['ground','high','ramp']],['Ground rails','Elevated rails','Ramps'],loc='lower left',bbox_to_anchor=(.05,.03),ncol=3,frameon=False,fontsize=10)
fig.text(.06,.02,'Rail centers are linked by native connectivity; curves are approximated. Signals and supports are omitted from the drawing.',fontsize=9,color='#69758b')
fig.tight_layout(rect=(.035,.075,.98,.92),h_pad=3,w_pad=3)
fig.savefig(HERE/'crossbar-embeddings.png',dpi=160,facecolor=fig.get_facecolor())
fig.savefig(HERE/'crossbar-embeddings.svg',facecolor=fig.get_facecolor())
plt.close(fig)
(HERE/'schematic-provenance.json').write_text(json.dumps({'type':'native graph centerline schematic','in_game_screenshot':False,'curve_geometry':'approximated by connected entity centers','signal_support_positions_drawn':False,'panels':[x[0] for x in cases]},indent=2))
