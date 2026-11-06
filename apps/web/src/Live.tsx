import React, {useCallback, useEffect, useRef, useState} from 'react';
import {api, ApiError, newKey} from './api';
import type {AppConfig} from './auth';
import {startLogin} from './auth';

type Ctx = {config: AppConfig | null; signedIn: boolean; batteryId: string; cutoff: number};

export function SignInGate({config, signedIn, children}: {config: AppConfig | null; signedIn: boolean; children: React.ReactNode}) {
  if (!config) return <section className="panel"><h3>The AWS backend is offline</h3><p>BatteryMind's validated AWS stack (Cognito, ECS Fargate, RDS with pgvector, Bedrock) was deliberately torn down to avoid charges, so sign-in, the assistant, saved memory and history are unavailable right now. The Overview and Analysis views still work: they read the versioned export of the real NASA measurements.</p><p>Evidence that the live system worked is committed in the repository: 24 of 24 live checks, including MFA sign-in, recall across sessions and isolation between users. <a href="https://github.com/manisa504/batterymind-aws-ai-battery-reliability-intelligence/blob/main/reports/performance/live-performance.json">Live test report</a> · <a href="https://github.com/manisa504/batterymind-aws-ai-battery-reliability-intelligence/blob/main/docs/runbooks/deployment.md">How to redeploy</a> · <a href="https://manisa504.github.io/batterymind-aws-ai-battery-reliability-intelligence/">Explainer and video</a></p></section>;
  if (!signedIn) return <section className="panel"><h3>Sign in to use persistent memory</h3><p>Assistant conversations and assessments are stored per user in PostgreSQL. Sign-in uses Amazon Cognito with a required authenticator-app code.</p><button className="primary" onClick={() => startLogin(config)}>Sign in</button></section>;
  return <>{children}</>;
}

type Turn = {role: string; content: string};
type Reply = {answer: string; model_id: string; latency_ms: number; usage: {input_tokens: number; output_tokens: number}; context: Record<string, number | string>};

export function Assistant({config, batteryId, cutoff}: Ctx & {config: AppConfig}) {
  const base = config.apiBase;
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [last, setLast] = useState<Reply | null>(null);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSessionId(null); setTurns([]); setLast(null); setError(null);
    api<{items: {id: string}[]}>(base, `/batteries/${batteryId}/sessions`).then(async s => {
      if (!s.items.length) return;
      setSessionId(s.items[0].id);
      setTurns((await api<{items: Turn[]}>(base, `/sessions/${s.items[0].id}/turns`)).items);
    }).catch(e => setError((e as Error).message));
  }, [base, batteryId]);
  useEffect(() => end.current?.scrollIntoView({block: 'nearest'}), [turns]);

  const send = async () => {
    const message = text.trim();
    if (!message || busy) return;
    setBusy(true); setError(null);
    try {
      let id = sessionId;
      if (!id) {
        id = (await api<{id: string}>(base, '/sessions', {method: 'POST', body: {battery_id: batteryId, objective: 'Engineering assistant conversation'}})).id;
        setSessionId(id);
      }
      setTurns(t => [...t, {role: 'user', content: message}]); setText('');
      const reply = await api<Reply>(base, '/chat', {method: 'POST', body: {session_id: id, message, cutoff_cycle: cutoff}});
      setTurns(t => [...t, {role: 'assistant', content: reply.answer}]); setLast(reply);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Request failed');
    } finally { setBusy(false); }
  };

  const removeConversation = async () => {
    if (!sessionId || busy || !window.confirm('Delete this conversation and its saved assessments?')) return;
    try { await api(base, `/sessions/${sessionId}`, {method: 'DELETE'}); setSessionId(null); setTurns([]); setLast(null); }
    catch (e) { setError((e as Error).message); }
  };

  return <section className="assistant">
    <div className="chat">
      <div className="log" aria-live="polite">
        {!turns.length && <p className="hint">Ask about {batteryId} at cycle {cutoff}. Answers use the measured NASA data first, then your earlier saved assessments.</p>}
        {turns.map((t, i) => <div key={i} className={`bubble ${t.role}`}><small>{t.role === 'user' ? 'You' : 'BatteryMind'}</small><p>{t.content}</p></div>)}
        {busy && <div className="bubble assistant"><small>BatteryMind</small><p>Retrieving evidence…</p></div>}
        <div ref={end} />
      </div>
      {error && <p role="alert" className="err">{error}</p>}
      <form onSubmit={e => { e.preventDefault(); void send(); }}>
        <textarea aria-label="Message" maxLength={1000} rows={2} value={text} onChange={e => setText(e.target.value)} placeholder="e.g. How does this compare with my earlier assessment?" />
        <button className="primary" disabled={busy || !text.trim()}>Send</button>
      </form>
    </div>
    <aside>
      <h3>Context used</h3>
      {sessionId && <button disabled={busy} onClick={() => void removeConversation()}>Delete conversation</button>}
      {last ? <>
        <p>Measurements <b>{last.context.measurements_used}</b></p>
        <p>Prior assessments included <b>{last.context.prior_assessments_included}</b> of {last.context.prior_assessments_available}</p>
        <p>Semantic hits <b>{last.context.semantic_hits}</b></p>
        <p>Context size <b>{last.context.characters_before_compression} → {last.context.characters_after_compression}</b> chars</p>
        <p>Tokens <b>{last.usage.input_tokens} in / {last.usage.output_tokens} out</b></p>
        <p>Latency <b>{last.latency_ms} ms</b></p>
        <small>{last.model_id}</small>
      </> : <p className="hint">Details appear after the first reply.</p>}
    </aside>
  </section>;
}

type Item = {id: string; cutoff_cycle: number; decision: string; explanation: string; policy_version: string; model_version: string | null; validity: string; supersedes_id: string | null; version: number; created_at: string; soh_percent: number | null; latest_capacity_ah: number | null};

export function History({config, batteryId, cutoff}: Ctx & {config: AppConfig}) {
  const base = config.apiBase;
  const [items, setItems] = useState<Item[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api<{items: Item[]}>(base, `/batteries/${batteryId}/history`).then(r => setItems(r.items)).catch(e => setError((e as Error).message)), [base, batteryId]);
  useEffect(() => { setItems([]); setError(null); void load(); }, [load]);

  const record = async (supersede?: Item) => {
    setBusy(true); setError(null);
    try {
      const sessions = await api<{items: {id: string}[]}>(base, `/batteries/${batteryId}/sessions`);
      const session = sessions.items[0]?.id ?? (await api<{id: string}>(base, '/sessions', {method: 'POST', body: {battery_id: batteryId, objective: 'Engineering assessment'}})).id;
      await api(base, '/assessments', {method: 'POST', body: {session_id: session, battery_id: batteryId, cutoff_cycle: cutoff, idempotency_key: newKey(), ...(supersede ? {supersedes_id: supersede.id, expected_version: supersede.version} : {})}});
      await load();
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  const remove = async (id: string) => { setBusy(true); try { await api(base, `/assessments/${id}`, {method: 'DELETE'}); await load(); } catch (e) { setError((e as Error).message); } finally { setBusy(false); } };

  return <section className="panel">
    <div className="row"><div><h3>Assessment history · {batteryId}</h3><p>Saved to PostgreSQL for your account only. Each entry keeps its evidence, policy version and model.</p></div>
      <button className="primary" disabled={busy} onClick={() => void record()}>Record assessment at cycle {cutoff}</button></div>
    {error && <p role="alert" className="err">{error}</p>}
    {!items.length && <p className="hint">No saved assessments for this battery yet.</p>}
    <ul className="history">{items.map(x => <li key={x.id} className={x.validity}>
      <div className="row"><b>Cycle {x.cutoff_cycle} · {x.decision.replaceAll('_', ' ')}</b><span className="tag">{x.validity}</span></div>
      <p>{x.explanation}</p>
      <small>Measured {x.latest_capacity_ah?.toFixed(3)} Ah · derived SOH {x.soh_percent?.toFixed(1)}% · {x.policy_version} · {x.model_version ?? 'rule-based text'} · v{x.version} · {new Date(x.created_at).toLocaleString()}</small>
      {x.validity === 'valid' && <div className="actions"><button disabled={busy} onClick={() => void record(x)}>Correct using cycle {cutoff}</button><button disabled={busy} onClick={() => void remove(x.id)}>Delete</button></div>}
    </li>)}</ul>
  </section>;
}

type PerCell = Record<string, {linear: {mae_ah: number}; persistence: {mae_ah: number}; training_cutoff_cycle: number}>;
type Cost = {status:string;region:string;priced_on:string;currency:string;eight_hour_fixed_subtotal:number;always_on_monthly_reference:number;items:{resource:string;demo_cost:number;monthly_cost:number}[];excluded_usage:string[];note:string};
type Evaluation = {rul_baselines: {status: string; per_cell_chronological: PerCell} | null; memory_tests: {status: string; passed?: string[]; remaining?: string[]} | null; performance: {status: string; [k: string]: unknown} | null; operating_cost: Cost | null};

export function EvaluationView({config, signedIn}: {config: AppConfig | null; signedIn: boolean}) {
  const [ev, setEv] = useState<Evaluation | null>(null);
  const [usage, setUsage] = useState<{assistant_replies: number; input_tokens: number; output_tokens: number; mean_latency_ms: number} | null>(null);
  useEffect(() => {
    if (!config) return;
    api<Evaluation>(config.apiBase, '/evaluation').then(setEv).catch(() => undefined);
    if (signedIn) api<typeof usage>(config.apiBase, '/usage').then(setUsage).catch(() => undefined);
  }, [config, signedIn]);
  if (!config) return <section className="panel"><h3>Evaluation reports are served by the AWS API</h3><p>The backend is offline, so this view is empty. The same reports are committed in the repository under <code>reports/</code>: <a href="https://github.com/manisa504/batterymind-aws-ai-battery-reliability-intelligence/tree/main/reports">open the evidence reports</a>.</p></section>;
  const cells = ev?.rul_baselines?.per_cell_chronological ?? {};
  return <>
    <section className="panel"><h3>RUL baselines (chronological, no future data)</h3>
      <p>Mean absolute capacity error after each cell's training cutoff. Lower is better. Linear does not beat persistence on every cell.</p>
      <table><thead><tr><th>Cell</th><th>Train through cycle</th><th>Linear MAE (Ah)</th><th>Persistence MAE (Ah)</th></tr></thead>
        <tbody>{Object.entries(cells).map(([id, c]) => <tr key={id}><td>{id}</td><td>{c.training_cutoff_cycle}</td><td>{c.linear.mae_ah.toFixed(4)}</td><td>{c.persistence.mae_ah.toFixed(4)}</td></tr>)}</tbody></table></section>
    <section className="panel"><h3>Memory tests</h3><p>Report status: <b>{ev?.memory_tests?.status ?? 'unavailable'}</b></p>
      <ul>{(ev?.memory_tests?.passed ?? []).map(x => <li key={x}>Passed: {x}</li>)}</ul><ul>{(ev?.memory_tests?.remaining ?? []).map(x => <li key={x}>Not yet executed: {x}</li>)}</ul></section>
    <section className="panel"><h3>Operating cost reference · {ev?.operating_cost?.region ?? 'us-east-2'}</h3>
      {ev?.operating_cost ? <><p><b>${ev.operating_cost.eight_hour_fixed_subtotal.toFixed(2)}</b> modeled 8-hour fixed subtotal · <b>${ev.operating_cost.always_on_monthly_reference.toFixed(2)}</b> always-on monthly reference</p><table><thead><tr><th>Resource</th><th>8-hour demo</th><th>Monthly reference</th></tr></thead><tbody>{ev.operating_cost.items.map(x=><tr key={x.resource}><td>{x.resource}</td><td>${x.demo_cost.toFixed(2)}</td><td>${x.monthly_cost.toFixed(2)}</td></tr>)}</tbody></table><p className="hint">{ev.operating_cost.note} Excludes {ev.operating_cost.excluded_usage.join(', ')}. Priced {ev.operating_cost.priced_on}.</p></> : <p className="hint">Cost evidence is unavailable.</p>}
    </section>
    <section className="panel"><h3>Your assistant usage</h3>
      {usage ? <p>{usage.assistant_replies} replies · {usage.input_tokens} input / {usage.output_tokens} output tokens · mean latency {usage.mean_latency_ms} ms</p> : <p className="hint">{signedIn ? 'No usage recorded yet.' : 'Sign in to see your own usage.'}</p>}
      <p>Performance report: <b>{ev?.performance?.status ?? 'unavailable'}</b></p></section>
  </>;
}
