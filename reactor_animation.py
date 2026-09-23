"""Schematic visualization only; consumes results without changing the model."""
from html import escape
from math import log1p


def render_reactor(i, r, animate=True, enlarged=False):
    valid = r['eligible']
    moving = animate and valid
    pieces = []
    def pipe(path, color, value, reference=10):
        speed = max(.5, 4 / (1 + log1p(max(0, value) / reference)))
        active = moving and value > 0
        pieces.append(f'<path d="{path}" class="pipe"/><path d="{path}" stroke="{color}" class="flow {"moving" if active else ""}" style="animation-duration:{speed:.3f}s;opacity:{1 if value > 0 else .18}"/>')
    def box(x,y,w,h,title,lines,concept=False):
        texts = ''.join(f'<text x="{x+16}" y="{y+63+24*k}" class="small">{escape(str(t))}</text>' for k,t in enumerate(lines))
        pieces.append(f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" fill="url(#metal)" stroke="{"#708397" if concept else "#329db8"}" stroke-dasharray="{"6 5" if concept else "none"}"/><text x="{x+16}" y="{y+30}" class="label">{escape(title)}</text>{texts}</g>')
    f=lambda k: f'{r[k]:.2f}'
    # Main process, individual modelled outlets and separate return circuits.
    pipe('M20 245 H75','#33bffd',r['water_makeup_kg_h'])
    for path in ['M275 245 H325','M525 245 H575','M795 245 H845','M1045 245 H1095','M1295 245 H1345']:
        pipe(path,'#32c6f2',i.water_kg_h)
    pipe('M1445 175 V100 H1575','#92e25f',r['h2_kg_h'],1)
    pipe('M1445 320 V370 H1575','#ff895c',r['o2_kg_h'],8)
    pipe('M425 120 V175','#c4a3ff',i.ar_nm3_h)
    pipe('M685 555 V340','#ee98ff',r['absorbed_kw'],100)
    pipe('M1195 330 V480 H1035 V555','#ffb65c',r['heat_recovered_kw'],50)
    pipe('M935 630 H175 V335','#ffb65c',r['heat_reused_kw'],50)
    pipe('M1035 710 V770 H1170','#ffb65c',r['heat_export_kw'],50)
    pipe('M1445 330 V835 H65 V300 H75','#32c6f2',r['water_recycle_kg_h'])
    pipe('M1390 330 V880 H425 V330','#c4a3ff',r['ar_recycle_nm3_h'])
    pipe('M1490 330 V475 H1575','#a9b7c6',r['h2_tail_kg_h']+r['o2_tail_kg_h']+r['water_discharge_kg_h'])
    box(75,175,200,160,'01 · STEAM PREPARATION',[f'Total water {i.water_kg_h:.2f} kg/h',f'Heat demand {f("steam_duty_kw")} kW',f'Electricity {f("heater_electric_kw")} kW'])
    box(325,175,200,160,'02 · MIXING',[f'Total Ar {i.ar_nm3_h:.2f} Nm³/h',f'Make-up {f("ar_makeup_nm3_h")}', 'H₂O + argon'])
    box(575,155,220,190,'03 · AC / RF PLASMA',[f'Absorbed {f("absorbed_kw")} kW',f'Conversion {100*r["actual_conversion"]:.1f}%',f'Gross H₂ {f("h2_gross_kg_h")} kg/h'])
    glow = min(.85, .15 + r['absorbed_kw']/(r['absorbed_kw']+100)*.7) if valid and r['absorbed_kw']>0 else 0
    pieces.append(f'<ellipse cx="685" cy="320" rx="65" ry="14" fill="#ec82ff" opacity="{glow:.3f}" class="{"pulse" if moving and glow else ""}"/>')
    box(845,175,200,160,'04 · FIELD SEPARATION',['Conceptual module','Field / geometry undefined','No additional yield credit'],True)
    box(1095,175,200,160,'05 · QUENCH',['Rapid cooling','Temperature not calculated','Kinetics require validation'],True)
    box(1345,155,200,190,'06 · SEPARATION',[f'H₂ recovery {100*i.h2_recovery:.1f}%',f'O₂ recovery {100*i.o2_recovery:.1f}%','Purity not calculated'])
    box(575,555,220,155,'07 · RF GENERATOR',[f'{i.frequency_mhz:g} MHz · duty {100*i.duty:.1f}%',f'Electricity {f("rf_electric_kw")} kW',f'Reflected RF {f("reflected_kw")} kW'])
    box(935,555,230,155,'08 · HEAT RECOVERY',[f'Recovered {f("heat_recovered_kw")} kW',f'Reused {f("heat_reused_kw")} kW','Schematic thermal circuit'])
    box(75,460,370,120,'09 · RECYCLE STREAMS',[f'Recovered water {f("water_recycle_kg_h")} kg/h',f'Recovered argon {f("ar_recycle_nm3_h")} Nm³/h'])
    box(1215,555,330,155,'10 · CONTROL / CATALYSIS',['Sensors / interlocks: conceptual','Catalyst: '+i.catalyst[:30],'No automatic yield bonus'],True)
    labels=[(22,148,'Fresh H₂O '+f('water_makeup_kg_h')+' kg/h','#33bffd'),(330,98,'ARGON · purple circuit','#c4a3ff'),(1310,77,'Net H₂ '+f('h2_kg_h')+' kg/h','#92e25f'),(1320,410,'Net O₂ '+f('o2_kg_h')+' kg/h','#ff895c'),(1230,508,'Residues / purge → dedicated handling','#a9b7c6'),(1175,777,'Export heat '+f('heat_export_kw')+' kW','#ffb65c'),(90,817,'WATER RECYCLE','#33bffd'),(480,863,'ARGON RECYCLE','#c4a3ff')]
    for x,y,t,c in labels: pieces.append(f'<text x="{x}" y="{y}" fill="{c}" class="small">{escape(t)}</text>')
    status = 'ENERGY CHECK FAILED · animation paused · diagnostic values' if not valid else ('NO ABSORBED PLASMA POWER' if r['absorbed_kw']==0 else 'EXPLORATORY SCENARIO · values from the steady-state model')
    document = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><style>
body{margin:0;background:#06111d;color:#dbeaf5;font:14px system-ui}header{padding:12px 16px;border-bottom:1px solid #28465b}p{color:#a6bac9;margin:8px 0}svg{width:100%;height:auto;min-width:950px}.viewport{overflow:auto}.label{fill:#61d9e8;font-size:12px;font-weight:700}.small{font-size:12px;fill:#d3e1eb}.pipe{fill:none;stroke:#213c50;stroke-width:12;stroke-linejoin:round}.flow{fill:none;stroke-width:4;stroke-dasharray:10 14;stroke-linejoin:round}.moving{animation:travel 2s linear infinite}.pulse{animation:glow 2s ease-in-out infinite}@keyframes travel{to{stroke-dashoffset:-48}}@keyframes glow{50%{transform:translateY(-3px)}}@media(prefers-reduced-motion:reduce){*{animation:none!important}}
</style></head><body><header><strong>''' + escape(status) + '''</strong></header><div class="viewport"><svg viewBox="0 55 1620 855" role="img" aria-label="Animated reactor: steam, argon, RF plasma, separation, heat recovery and recycling"><defs><linearGradient id="metal" x2="100%" y2="0%"><stop stop-color="#132f44"/><stop offset=".5" stop-color="#0b1c2b"/><stop offset="1" stop-color="#19394c"/></linearGradient></defs>''' + ''.join(pieces) + '''</svg></div><p>Dashed outlines = conceptual components. Assumed recovery ≠ purity. Connections and dimensions are not a construction design.</p></body></html>'''

    return document.replace("min-width:950px", "min-width:1620px" if enlarged else "min-width:950px")
