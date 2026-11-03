import React, {useCallback, useEffect, useRef, useState} from 'react';
import {api, ApiError, newKey} from './api';
import type {AppConfig} from './auth';
import {startLogin} from './auth';

type Ctx = {config: AppConfig | null; signedIn: boolean; batteryId: string; cutoff: number};

export function SignInGate({config, signedIn, children}: {config: AppConfig | null; signedIn: boolean; children: React.ReactNode}) {
  if (!config) return <section className="panel"><h3>Live backend not configured</h3><p>This build is running as a static evidence export. The assistant, saved memory and history need the AWS-hosted deployment, which provides sign-in and the API.</p></section>;
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
type Evaluation = {rul_baselines: {status: string; per_cell_chronological: PerCell} | null; memory_tests: {status: string; passed?: string[]; remaining?: string[]} | null; performance: {status: string; [k: string]: unknown} | null};

export function EvaluationView({config, signedIn}: {config: AppConfig | null; signedIn: boolean}) {
  const [ev, setEv] = useState<Evaluation | null>(null);
  const [usage, setUsage] = useState<{assistant_replies: number; input_tokens: number; output_tokens: number; mean_latency_ms: number} | null>(null);
  useEffect(() => {
    if (!config) return;
    api<Evaluation>(config.apiBase, '/evaluation').then(setEv).catch(() => undefined);
    if (signedIn) api<typeof usage>(config.apiBase, '/usage').then(setUsage).catch(() => undefined);
  }, [config, signedIn]);
  if (!config) return <section className="panel"><h3>Evaluation needs the live backend</h3><p>Reports are served by the AWS API.</p></section>;
  const cells = ev?.rul_baselines?.per_cell_chronological ?? {};
  return <>
    <section className="panel"><h3>RUL baselines (chronological, no future data)</h3>
      <p>Mean absolute capacity error after each cell's training cutoff. Lower is better. Linear does not beat persistence on every cell.</p>
      <table><thead><tr><th>Cell</th><th>Train through cycle</th><th>Linear MAE (Ah)</th><th>Persistence MAE (Ah)</th></tr></thead>
        <tbody>{Object.entries(cells).map(([id, c]) => <tr key={id}><td>{id}</td><td>{c.training_cutoff_cycle}</td><td>{c.linear.mae_ah.toFixed(4)}</td><td>{c.persistence.mae_ah.toFixed(4)}</td></tr>)}</tbody></table></section>
    <section className="panel"><h3>Memory tests</h3><p>Report status: <b>{ev?.memory_tests?.status ?? 'unavailable'}</b></p>
      <ul>{(ev?.memory_tests?.passed ?? []).map(x => <li key={x}>Passed: {x}</li>)}</ul><ul>{(ev?.memory_tests?.remaining ?? []).map(x => <li key={x}>Not yet executed: {x}</li>)}</ul></section>
    <section className="panel"><h3>Your assistant usage</h3>
      {usage ? <p>{usage.assistant_replies} replies · {usage.input_tokens} input / {usage.output_tokens} output tokens · mean latency {usage.mean_latency_ms} ms</p> : <p className="hint">{signedIn ? 'No usage recorded yet.' : 'Sign in to see your own usage.'}</p>}
      <p>Performance report: <b>{ev?.performance?.status ?? 'unavailable'}</b></p></section>
  </>;
}
