"""Steady-state screening model, pure H2O/Ar only. No kinetics or RF field solver."""
from dataclasses import dataclass, asdict, replace
import math

VERSION = '5.1 RF'
H2_PER_WATER = 2.016 / 18.015
HHV = 39.4  # kWh/kg H2, liquid water reference approximately 25 C
LHV = 33.33

@dataclass
class Inputs:
    name: str = 'Exploratory scenario'
    evidence: str = 'Uncalibrated assumptions'
    catalyst: str = 'None / to be defined'
    coupling: str = 'To be confirmed'
    frequency_mhz: float = 100.0
    duty: float = 1.0
    rf_on_kw: float = 120.0
    generator_eff: float = .85
    reflected: float = .10
    coupling_eff: float = .80
    water_kg_h: float = 12.0
    conversion: float = .40
    absorbed_sec: float = 60.0
    h2_recovery: float = .92
    o2_recovery: float = .88
    purge: float = .04
    ar_nm3_h: float = 18.0
    ar_recovery: float = .86
    water_recovery: float = .78
    steam_kwh_kg: float = .90
    heater_eff: float = .95
    recoverable_fraction: float = .50
    exchanger_eff: float = .72
    auxiliary_kw: float = 3.0
    separation_kwh_kg: float = 2.0
    electricity_chf_kwh: float = .18
    ar_chf_nm3: float = .65
    water_chf_m3: float = 1.2
    fixed_chf_day: float = 0.0
    hours_day: float = 24.0

BOUNDS = {
 'frequency_mhz':(5.000001,10000), 'duty':(.001,1), 'rf_on_kw':(0,100000),
 'generator_eff':(.01,1), 'reflected':(0,1), 'coupling_eff':(.01,1),
 'water_kg_h':(.001,100000),'conversion':(0,1),'absorbed_sec':(.01,10000),
 'h2_recovery':(0,1),'o2_recovery':(0,1),'purge':(0,1),
 'ar_nm3_h':(0,100000),'ar_recovery':(0,1),'water_recovery':(0,1),
 'steam_kwh_kg':(0,100),'heater_eff':(.01,1),'recoverable_fraction':(0,1),
 'exchanger_eff':(0,1),'auxiliary_kw':(0,100000),'separation_kwh_kg':(0,10000),
 'electricity_chf_kwh':(0,100),'ar_chf_nm3':(0,10000),'water_chf_m3':(0,10000),
 'fixed_chf_day':(0,1e9),'hours_day':(.01,24)
}

def validate(i):
    for k,(lo,hi) in BOUNDS.items():
        v=getattr(i,k)
        if isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) or not lo<=v<=hi:
            raise ValueError(f'{k}: allowed value between {lo} e {hi}')
    for k in ('name','evidence','catalyst','coupling'):
        if not isinstance(getattr(i,k),str) or len(getattr(i,k))>2000:
            raise ValueError(f'{k}: invalid text')

def calculate(i):
    validate(i)
    forward=i.rf_on_kw*i.duty
    reflected=forward*i.reflected
    absorbed=(forward-reflected)*i.coupling_eff
    gen_input=forward/i.generator_eff
    h2_feed=i.water_kg_h*H2_PER_WATER*i.conversion
    h2_power=absorbed/i.absorbed_sec
    gross=min(h2_feed,h2_power)
    consumed=gross/H2_PER_WATER
    o2_gross=consumed-gross
    h2=gross*i.h2_recovery*(1-i.purge)
    o2=o2_gross*i.o2_recovery*(1-i.purge)
    unreacted=i.water_kg_h-consumed
    water_recycle=unreacted*i.water_recovery
    ar_recycle=i.ar_nm3_h*i.ar_recovery*(1-i.purge)
    steam=i.water_kg_h*i.steam_kwh_kg
    chemical=gross*HHV
    # Reference: feed liquid water ~25 C, products cooled to reference.
    # All uncollected H2 remains an output stream (no combustion credit).
    residual=absorbed+steam-chemical
    eligible=residual>=-1e-8
    heat_recovered=max(0,residual)*i.recoverable_fraction*i.exchanger_eff
    reused=min(steam,heat_recovered)
    available_export=heat_recovered-reused
    heater_input=(steam-reused)/i.heater_eff
    sep=h2*i.separation_kwh_kg
    electric=gen_input+heater_input+i.auxiliary_kw+sep
    dissipated=(gen_input-absorbed)+(heater_input-(steam-reused))+max(0,residual)-heat_recovered+i.auxiliary_kw+sep
    energy_error=electric-chemical-available_export-dissipated
    makeup_water=i.water_kg_h-water_recycle
    makeup_ar=i.ar_nm3_h-ar_recycle
    costs=(electric*i.electricity_chf_kwh+makeup_ar*i.ar_chf_nm3+makeup_water/1000*i.water_chf_m3)*i.hours_day+i.fixed_chf_day
    net_day=h2*i.hours_day
    return dict(h2_kg_h=h2,h2_kg_day=net_day,o2_kg_h=o2,h2_gross_kg_h=gross,
        h2_tail_kg_h=gross-h2,o2_tail_kg_h=o2_gross-o2,
        water_consumed_kg_h=consumed,water_recycle_kg_h=water_recycle,
        water_discharge_kg_h=unreacted-water_recycle,water_makeup_kg_h=makeup_water,
        ar_recycle_nm3_h=ar_recycle,ar_makeup_nm3_h=makeup_ar,
        forward_kw=forward,reflected_kw=reflected,absorbed_kw=absorbed,rf_electric_kw=gen_input,
        steam_duty_kw=steam,heater_electric_kw=heater_input,heat_recovered_kw=heat_recovered,
        heat_reused_kw=reused,heat_export_kw=available_export,electric_kw=electric,
        electric_kwh_day=electric*i.hours_day,chemical_kw=chemical,dissipated_kw=dissipated,
        energy_error_kw=energy_error,thermal_margin_kw=residual,eligible=eligible,
        sec_kwh_kg=electric/h2 if h2>0 else None,
        lhv_efficiency=h2*LHV/electric if electric>0 else None,
        cost_chf_day=costs,cost_chf_kg=costs/net_day if net_day>0 else None,
        mass_error_kg_h=i.water_kg_h-(gross+o2_gross+unreacted),
        actual_conversion=consumed/i.water_kg_h,
        limitation='Absorbed power' if h2_power<h2_feed else 'Feed rate and assumed conversion')

def sweep(i, feeds, powers, target_day, max_sec, max_ar):
    """Grid comparison at fixed chemistry, frequency and efficiencies; no physical optimum claim."""
    rows=[]
    for feed in feeds:
        for power in powers:
            r=calculate(replace(i,water_kg_h=float(feed),rf_on_kw=float(power)))
            accepted=(r['eligible'] and r['h2_kg_day']>=target_day and r['sec_kwh_kg'] is not None
                      and r['sec_kwh_kg']<=max_sec and r['ar_makeup_nm3_h']<=max_ar)
            rows.append(dict(water_kg_h=feed,rf_on_kw=power,accepted=accepted,**r))
    return sorted(rows,key=lambda r:(not r['accepted'],r['cost_chf_kg'] if r['cost_chf_kg'] is not None else math.inf))

def serialize(i):
    return {'version':VERSION,'inputs':asdict(i),'results':calculate(i)}

def from_dict(d):
    if d.get('version')!=VERSION: raise ValueError('Expected V5.1 RF scenario format')
    i=Inputs(**d['inputs']);validate(i);return i
