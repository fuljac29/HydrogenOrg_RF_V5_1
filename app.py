"""HydrogenOrg public research interface. Model schema remains V5.1 compatible."""
import json
from dataclasses import asdict
import pandas as pd
import streamlit as st
from model import Inputs, BOUNDS, calculate, serialize, from_dict, sweep
from reactor_animation import render_reactor

st.set_page_config(page_title='HydrogenOrg | RF Research Lab', page_icon='⚗️', layout='wide')
st.markdown('''<style>.stApp{background:#07131f;color:#e6eff6}section[data-testid="stSidebar"]{background:#102434}h1,h2,h3{color:#56dce5!important}div[data-testid="stMetric"]{background:#102a3b;padding:10px;border-radius:12px;border-top:2px solid #86d766}.stButton>button{border-color:#56cbd9}.block-container{padding-top:3.5rem}h1{font-size:2rem!important;margin-bottom:0!important}</style>''',unsafe_allow_html=True)
st.link_button('← Back to HydrogenOrg', 'https://hydrogenorg.ch/', type='primary', help='Opens the website in a new tab and keeps this simulation available.')
st.caption('Navigation update · NAV-02')
st.title('HydrogenOrg · RF Research Lab')
st.caption('Research simulation · Uncalibrated assumptions · Not measured reactor performance')
if 'base' not in st.session_state: st.session_state.base=asdict(Inputs())
if 'revision' not in st.session_state: st.session_state.revision=0
if 'scenarios' not in st.session_state: st.session_state.scenarios=[]
# Explicit labels and bounds shared with the model prevent input drift.
GROUPS=[('AC / RF power',[
 ('frequency_mhz','Excitation frequency (MHz)',1.),('rf_on_kw','Forward RF power during ON (kW)',1.),('duty','Modulation duty cycle',.01),('generator_eff','Electrical-to-RF efficiency',.01),('reflected','Reflected power fraction',.01),('coupling_eff','Plasma coupling efficiency after reflection',.01)]),
 ('Water and conversion', [('water_kg_h','Total water feed including recycle (kg/h)',1.),('conversion','Assumed maximum single-pass conversion',.01),('absorbed_sec','Assumed absorbed energy (kWh/kg gross H₂)',1.)]),
 ('Separation and recycling',[('h2_recovery','H₂ recovery before purge',.01),('o2_recovery','O₂ recovery before purge',.01),('purge','Common gas purge fraction',.01),('ar_nm3_h','Total circulating argon (Nm³/h)',1.),('ar_recovery','Argon recovery before purge',.01),('water_recovery','Unconverted water recovery',.01)]),
 ('Heat and auxiliary loads',[('steam_kwh_kg','Steam preparation duty (kWh/kg water)',.05),('heater_eff','Electric heater efficiency',.01),('recoverable_fraction','Recoverable residual heat fraction',.01),('exchanger_eff','Heat recovery efficiency',.01),('auxiliary_kw','Other auxiliary loads (kW)',.1),('separation_kwh_kg','Separation/compression (kWh/kg net H₂)',.1)]),
 ('Operating costs',[('hours_day','Operating hours per day',1.),('electricity_chf_kwh','Electricity (CHF/kWh)',.01),('ar_chf_nm3','Make-up argon (CHF/Nm³)',.1),('water_chf_m3','Make-up water (CHF/m³)',.1),('fixed_chf_day','Other included costs (CHF/day)',10.)])]
with st.sidebar:
 st.link_button('← Back to HydrogenOrg', 'https://hydrogenorg.ch/', help='Opens the website in a new tab.')
 st.header('Configure your scenario')
 with st.expander('Import / reset'):
  uploaded=st.file_uploader('Scenario JSON (V5.1 RF)',type=['json'])
  if st.button('Load scenario',disabled=uploaded is None):
   try:
    if uploaded.size>1_000_000: raise ValueError('Maximum file size: 1 MB.')
    loaded=from_dict(json.loads(uploaded.getvalue()))
    st.session_state.base=asdict(loaded);st.session_state.revision+=1;st.rerun()
   except (ValueError,TypeError,KeyError,AttributeError,UnicodeDecodeError) as exc: st.error(f'Cannot load scenario: {exc}')
  if st.button('Reset assumptions'):
   st.session_state.base=asdict(Inputs());st.session_state.revision+=1;st.rerun()
 d=st.session_state.base; vals={}
 for k,label in [('name','Scenario name'),('evidence','Data source / evidence')]:
  vals[k]=st.text_input(label,value=d[k],max_chars=2000,key=f'{st.session_state.revision}_{k}')
 for index,(title,fields) in enumerate(GROUPS):
  with st.expander(title,expanded=index==0):
   for key,label,step in fields:
    lo,hi=BOUNDS[key]
    vals[key]=st.number_input(label,min_value=float(lo),max_value=float(hi),value=float(d[key]),step=step,key=f'{st.session_state.revision}_{key}')
   if index==0:
    vals['coupling']=st.text_input('Coupling configuration',value=d['coupling'],max_chars=2000,key=f'{st.session_state.revision}_coupling')
    st.caption('Frequency is recorded, not a predictor of temperature or yield. 100 MHz is an illustrative input, not a confirmed operating frequency.')
   if index==1:
    vals['catalyst']=st.text_input('Metal catalyst / sample',value=d['catalyst'],max_chars=2000,key=f'{st.session_state.revision}_catalyst')
    st.caption('Catalyst names do not apply a performance bonus. Calibrate conversion and energy demand against measurements.')
 st.caption('All fractions range from 0 to 1. Costs remain in CHF. Export scenarios before closing the session.')
i=Inputs(**vals);r=calculate(i)
cols=st.columns(4)
for col,label,value in zip(cols,['Net H₂ production','Total electricity','Specific electricity','Included production cost'],[f"{r['h2_kg_day']:.2f} kg/day",f"{r['electric_kw']:.2f} kW",f"{r['sec_kwh_kg']:.1f} kWh/kg" if r['sec_kwh_kg'] is not None else 'No H₂ output',f"{r['cost_chf_kg']:.2f} CHF/kg" if r['cost_chf_kg'] is not None else 'No H₂ output']): col.metric(label,value)
if not r['eligible']: st.error('Energy-infeasible assumptions: available process energy cannot cover gross H₂ chemical enthalpy. All displayed results are diagnostic; animation is suspended.')
elif not r['h2_kg_h']: st.warning('No hydrogen output for this scenario.')
else: pass
tabs=st.tabs(['Live reactor','Mass & energy','Compare scenarios','Parameter sweep','Method & limitations'])
with tabs[0]:
 controls=st.columns([1,1,1])
 motion=controls[0].toggle('Animate process flows',value=True)
 enlarged=controls[1].toggle('Enlarge diagram',value=False)
 diagram=render_reactor(i,r,motion,enlarged=enlarged)
 controls[2].download_button('Openable reactor view',render_reactor(i,r,motion,enlarged=True),'HydrogenOrg_reactor.html','text/html',help='Download and open in your browser for a separate full-window view of this scenario.')
 st.iframe(diagram,height="content")
 st.caption('Change sidebar inputs to update the diagram. Motion is illustrative, not a dynamic simulation. Scroll horizontally on smaller screens.')
 a,b,c=st.columns(3)
 a.metric('Absorbed RF',f"{r['absorbed_kw']:.2f} kW")
 b.metric('Heat reused for steam',f"{r['heat_reused_kw']:.2f} kW")
 c.metric('Actual model conversion',f"{100*r['actual_conversion']:.1f}%")
 st.write('Active model constraint:',r['limitation'])
with tabs[1]:
 left,right=st.columns(2)
 with left:
  st.subheader('Water and products · kg/h')
  rows=[('Total reactor water',i.water_kg_h)]+[(label,r[k]) for label,k in [('Water consumed','water_consumed_kg_h'),('Water recycled','water_recycle_kg_h'),('Water discharged','water_discharge_kg_h'),('Fresh water make-up','water_makeup_kg_h'),('Net H₂','h2_kg_h'),('Unrecovered / purged H₂','h2_tail_kg_h'),('Net O₂','o2_kg_h'),('Unrecovered / purged O₂','o2_tail_kg_h')]]
  st.dataframe(pd.DataFrame(rows,columns=['Stream','kg/h']),hide_index=True,width='stretch')
 with right:
  st.subheader('External energy balance · kW')
  rows=[(label,r[k]) for label,k in [('Electrical input','electric_kw'),('Gross H₂ chemical energy (HHV)','chemical_kw'),('Available exported heat','heat_export_kw'),('Dissipation / losses','dissipated_kw'),('Closure residual','energy_error_kw')]]
  st.dataframe(pd.DataFrame(rows,columns=['Term','kW']),hide_index=True,width='stretch')
  st.metric('Make-up argon',f"{r['ar_makeup_nm3_h']:.2f} Nm³/h")
 st.caption('Steady state; liquid-water reference near 25 °C, products cooled to the reference state. No free external heat or combustion credit for unrecovered H₂. Gas recovery does not establish product purity.')
with tabs[2]:
 st.subheader('Session comparison')
 a,b=st.columns(2)
 if a.button('Save current scenario'): st.session_state.scenarios.append(serialize(i))
 if b.button('Clear comparison'): st.session_state.scenarios=[]
 if st.session_state.scenarios:
  rows=[]
  for s in st.session_state.scenarios:
   x=s['inputs'];y=s['results'];rows.append({'Scenario':x['name'],'Evidence':x['evidence'],'Catalyst':x['catalyst'],'RF MHz':x['frequency_mhz'],'H₂ kg/day':y['h2_kg_day'],'kWh/kg H₂':y['sec_kwh_kg'],'CHF/kg':y['cost_chf_kg'],'Energy check':y['eligible']})
  frame=pd.DataFrame(rows);st.dataframe(frame,hide_index=True,width='stretch')
  st.download_button('Download comparison CSV',frame.to_csv(index=False).encode('utf-8-sig'),'comparison.csv','text/csv')
  st.download_button('Download complete session archive',json.dumps(st.session_state.scenarios,ensure_ascii=False,indent=2,allow_nan=False),'scenario_archive.json','application/json')
 else: st.info('Save two or more configurations to compare their results here.')
 st.download_button('Download current scenario JSON',json.dumps(serialize(i),ensure_ascii=False,indent=2,allow_nan=False),'rf_scenario.json','application/json')
 st.caption('Single-scenario JSON files can be imported in the sidebar. The session archive is a list for offline analysis, not a single-scenario import. Session data is not saved automatically.')
with tabs[3]:
 st.subheader('Explore water feed and RF power')
 st.write('Rank feasible grid points by included cost. Chemistry, frequency, catalyst and efficiencies remain fixed at the sidebar assumptions.')
 a,b=st.columns(2)
 with a:
  fmin=st.number_input('Minimum water feed (kg/h)',.001,100000.,max(.001,i.water_kg_h*.5))
  fmax=st.number_input('Maximum water feed (kg/h)',.001,100000.,min(100000.,i.water_kg_h*1.5))
  goal=st.number_input('Minimum H₂ production (kg/day)',0.,1e6,10.)
 with b:
  pmin=st.number_input('Minimum RF ON power (kW)',0.,100000.,i.rf_on_kw*.5)
  pmax=st.number_input('Maximum RF ON power (kW)',0.,100000.,min(100000.,max(1.,i.rf_on_kw*1.5)))
  maxsec=st.number_input('Maximum specific electricity (kWh/kg)',.01,1e6,200.)
 maxar=st.number_input('Maximum make-up argon (Nm³/h)',0.,1e6,100.)
 n=st.slider('Grid points per axis',3,25,9)
 signature=json.dumps([asdict(i),fmin,fmax,pmin,pmax,goal,maxsec,maxar,n],sort_keys=True)
 if st.button('Run parameter sweep',type='primary'):
  if fmin>fmax or pmin>pmax: st.error('Minimum values must not exceed maximum values.')
  else: st.session_state.grid=(signature,sweep(i,[fmin+(fmax-fmin)*k/(n-1) for k in range(n)],[pmin+(pmax-pmin)*k/(n-1) for k in range(n)],goal,maxsec,maxar))
 if 'grid' in st.session_state:
  old,results=st.session_state.grid
  if old!=signature: st.info('Inputs changed. Run the sweep again to refresh results.')
  else:
   ok=[x for x in results if x['accepted']];st.write(f'{len(ok)} accepted scenarios out of {len(results)}')
   if ok:
    best=ok[0];st.success(f"Lowest included cost in this grid: water {best['water_kg_h']:.2f} kg/h, RF ON {best['rf_on_kw']:.2f} kW, H₂ {best['h2_kg_day']:.2f} kg/day. A candidate for validation, not a proven optimum.")
   else: st.warning('No scenario meets all constraints.')
   frame=pd.DataFrame(results)
   st.dataframe(frame[['water_kg_h','rf_on_kw','h2_kg_day','sec_kwh_kg','cost_chf_kg','eligible','accepted']],hide_index=True,width='stretch')
   chart=frame[frame['eligible']].pivot_table(index='rf_on_kw',columns='water_kg_h',values='sec_kwh_kg',aggfunc='first')
   if not chart.empty:
    chart.columns=[f'{x:.2f} kg/h water' for x in chart.columns];st.caption('Specific electricity (kWh/kg net H₂) versus RF ON power (kW)');st.line_chart(chart)
   st.download_button('Download sweep CSV',frame.to_csv(index=False).encode('utf-8-sig'),'rf_sweep.csv','text/csv')
with tabs[4]:
 st.markdown('''### What this model calculates
- Average forward RF power = ON power × duty cycle.
- Absorbed RF = average forward RF × (1 − reflected fraction) × coupling efficiency.
- Gross H₂ = the smaller of the water-conversion limit and absorbed power / assumed specific absorbed energy.
- Net gas output = gross output × separator recovery × (1 − purge).
- Residual process heat = absorbed RF + steam duty − gross H₂ chemical energy (HHV).
- Recovered heat is a specified fraction of positive residual heat, multiplied by exchanger efficiency. Reuse is capped at steam demand; the remainder is available export heat.
- Total electricity includes the RF generator, remaining electric heating, auxiliaries and separation/compression.

### What still needs validation
This is a pure H₂O/argon screening model, not a construction design. It does not solve RF fields, impedance matching, molecular resonance, kinetics, equilibrium, pressure, temperature, geometry, quench rates or product purity. Frequency and catalyst names are recorded as metadata only. Conversion and specific energy must be calibrated together.

Recovered heat requires a suitable temperature level and a feasible exchanger: neither is resolved here. Start-up energy and transient storage are excluded. Recycling is referenced to the same liquid-water state as fresh feed. A balance that closes is necessary but not sufficient for a functioning reactor.

Ammonia, hydrocarbons, vehicle range and batteries are outside this edition. No automatic credits are assigned to oxygen or exported heat. Cost figures include only the costs entered; add capital, maintenance and staffing assumptions before drawing financial conclusions.

### Using this public research tool
Inputs and saved comparisons belong to the current session. Export JSON to retain your assumptions. The animation uses a compressed visual scale and does not represent real fluid velocities or MHz oscillations. Dashed component outlines identify conceptual blocks.
''')
st.divider();st.caption('HydrogenOrg · Research model • AC/RF plasma • Transparent assumptions • Experimental validation required')
