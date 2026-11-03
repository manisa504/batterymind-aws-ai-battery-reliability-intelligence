import React, {useEffect, useMemo, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis} from 'recharts';
import {completeLogin, loadConfig, logout, startLogin, token, type AppConfig} from './auth';
import {Assistant, EvaluationView, History, SignInGate} from './Live';
import './styles.css';

type Point={cycle:number;capacity_ah:number;soh_percent:number};
type Battery={battery_id:string;cutoff_cycle:number;latest_capacity_ah:number;soh_percent:number;degradation_rate_ah_per_cycle:number;measurements:Point[];classification:{decision:string;policy_version:string;rationale:string};rul:{status:string;estimated_remaining_cycles?:number;interval_90_cycles?:number[];model_version?:string}};
type Dataset={schema_version:string;source_manifest:string;batteries:Battery[]};
const views=['Overview','Analysis','Assistant','Decision history','Evaluation'] as const;

function Metric({label,value,note}:{label:string;value:string;note?:string}){return <article className="metric"><span>{label}</span><strong>{value}</strong>{note&&<small>{note}</small>}</article>}
function App(){
 const [data,setData]=useState<Dataset|null>(null),[view,setView]=useState<(typeof views)[number]>('Overview'),[id,setId]=useState('B0005'),[cutoff,setCutoff]=useState(1);
 const [config,setConfig]=useState<AppConfig|null>(null),[signedIn,setSignedIn]=useState(false);
 useEffect(()=>{loadConfig().then(async c=>{if(c){await completeLogin(c);setConfig(c);setSignedIn(!!token())}})},[]);
 useEffect(()=>{fetch('/data/batteries.v1.json').then(r=>r.json()).then((d:Dataset)=>{setData(d);setId(d.batteries[0].battery_id);setCutoff(d.batteries[0].cutoff_cycle)})},[]);
 const battery=data?.batteries.find(b=>b.battery_id===id); const points=useMemo(()=>battery?.measurements.filter(p=>p.cycle<=cutoff)??[],[battery,cutoff]); const latest=points.at(-1);
 if(!data||!battery)return <main className="loading">Loading validated battery evidence…</main>;
 const soh=latest?.soh_percent??0; const decision=soh<=70?'EOL_REVIEW':soh<=75?'ENGINEERING_REVIEW':soh<=85?'INCREASE_TESTING':'CONTINUE_MONITORING';
 return <div className="shell"><aside><div className="brand"><span>BM</span><div><b>BatteryMind</b><small>Reliability intelligence</small></div></div><nav>{views.map(x=><button className={x===view?'active':''} onClick={()=>setView(x)} key={x}>{x}</button>)}</nav>{config&&<div className="account">{signedIn?<button onClick={()=>logout(config)}>Sign out</button>:<button onClick={()=>void startLogin(config)}>Sign in</button>}</div>}<div className="evidence">NASA Ames dataset<br/><b>Verified local export</b></div></aside><main><header><div><p className="eyebrow">ENGINEERING WORKSPACE</p><h1>{view}</h1></div><label>Battery<select value={id} onChange={e=>{const b=data.batteries.find(x=>x.battery_id===e.target.value)!;setId(e.target.value);setCutoff(b.cutoff_cycle)}}>{data.batteries.map(x=><option key={x.battery_id}>{x.battery_id}</option>)}</select></label></header>
 {view==='Overview'&&<><section className="hero"><div><p>Measured condition at cycle {cutoff}</p><h2>{decision.replaceAll('_',' ')}</h2><span>Experimental policy · {battery.classification.policy_version}</span></div><div className="gauge"><b>{soh.toFixed(1)}%</b><small>State of Health</small></div></section><section className="metrics"><Metric label="Measured capacity" value={`${latest?.capacity_ah.toFixed(3)} Ah`} note="NASA discharge measurement"/><Metric label="Cycle cutoff" value={`${cutoff}`} note={`of ${battery.cutoff_cycle} discharge cycles`}/><Metric label="RUL baseline" value={battery.rul.status==='available'?`${battery.rul.estimated_remaining_cycles?.toFixed(0)} cycles`:'Unavailable'} note="Linear model estimate"/></section><Chart points={points}/></>}
 {view==='Analysis'&&<><section className="control"><div><b>Historical cutoff</b><span>Only evidence through cycle {cutoff} is used</span></div><input aria-label="Cycle cutoff" type="range" min="1" max={battery.cutoff_cycle} value={cutoff} onChange={e=>setCutoff(+e.target.value)}/><output>{cutoff}</output></section><Chart points={points}/><section className="panel"><h3>Evidence boundary</h3><p>Solid values are measurements from the NASA MATLAB files. Remaining useful life is a model estimate against the experiment-specific 1.4 Ah threshold and is not a field safety claim.</p></section></>}
 {view==='Assistant'&&<SignInGate config={config} signedIn={signedIn}>{config&&<Assistant config={config} signedIn={signedIn} batteryId={id} cutoff={cutoff}/>}</SignInGate>}
 {view==='Decision history'&&<SignInGate config={config} signedIn={signedIn}>{config&&<History config={config} signedIn={signedIn} batteryId={id} cutoff={cutoff}/>}</SignInGate>}
 {view==='Evaluation'&&<EvaluationView config={config} signedIn={signedIn}/>}
 </main></div>
}
function Chart({points}:{points:Point[]}){return <section className="chart"><div><h3>Capacity degradation</h3><p>Measured discharge capacity by cycle</p></div><ResponsiveContainer width="100%" height={310}><AreaChart data={points}><defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#55d6be" stopOpacity={.35}/><stop offset="1" stopColor="#55d6be" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#263446" vertical={false}/><XAxis dataKey="cycle" stroke="#77859a"/><YAxis domain={['dataMin - 0.1','dataMax + 0.05']} stroke="#77859a" unit=" Ah"/><Tooltip contentStyle={{background:'#101a27',border:'1px solid #2b3a4d'}}/><Area type="monotone" dataKey="capacity_ah" stroke="#55d6be" fill="url(#fill)" dot={false}/></AreaChart></ResponsiveContainer></section>}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
