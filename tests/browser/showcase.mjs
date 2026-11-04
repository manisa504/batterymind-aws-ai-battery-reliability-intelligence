import {existsSync, mkdtempSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawn} from 'node:child_process';

const candidates = [
  process.env.CHROME_BIN,
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
].filter(Boolean);
const chromePath = candidates.find(existsSync);
// SHOWCASE_URL lets CI test the locally built artifact; the default checks the public deployment.
const showcaseUrl = process.env.SHOWCASE_URL ?? 'https://batterymind-showcase.vercel.app';
if (!chromePath) throw new Error('Chrome or Chromium was not found');

const profile = mkdtempSync(join(tmpdir(), 'batterymind-browser-'));
const chrome = spawn(chromePath, [
  '--headless=new',
  '--disable-gpu',
  '--no-sandbox',
  '--remote-debugging-port=9223',
  `--user-data-dir=${profile}`,
  'about:blank',
], {stdio: 'ignore'});

const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
let socket;
let sequence = 0;
const pending = new Map();

async function command(method, params = {}) {
  const id = ++sequence;
  socket.send(JSON.stringify({id, method, params}));
  return new Promise((resolve, reject) => pending.set(id, {resolve, reject}));
}

try {
  let target;
  for (let attempt = 0; attempt < 40; attempt++) {
    try {
      target = await fetch(
        `http://127.0.0.1:9223/json/new?${showcaseUrl}`,
        {method: 'PUT'},
      ).then(response => response.json());
      break;
    } catch {
      await delay(250);
    }
  }
  if (!target) throw new Error('Chrome debugging endpoint did not start');
  socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.onopen = resolve;
    socket.onerror = reject;
  });
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (!message.id || !pending.has(message.id)) return;
    const request = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) request.reject(new Error(message.error.message));
    else request.resolve(message.result);
  };
  await command('Page.enable');
  for (let attempt = 0; attempt < 40; attempt++) {
    const ready = await command('Runtime.evaluate', {
      returnByValue: true,
      expression: "Boolean(document.querySelector('select') && document.querySelector('input[type=range]'))",
    });
    if (ready.result.value) break;
    await delay(250);
  }
  const result = await command('Runtime.evaluate', {
    awaitPromise: true,
    returnByValue: true,
    expression: `(async () => {
      const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
      const select = document.querySelector('select');
      const cutoff = document.querySelector('input[type=range]');
      if (!select || !cutoff) return {ok:false, reason:'controls missing', url:location.href, title:document.title, text:document.body.innerText.slice(0,200)};
      select.value = 'B0006';
      select.dispatchEvent(new Event('change', {bubbles:true}));
      await wait(250);
      cutoff.value = '50';
      cutoff.dispatchEvent(new Event('input', {bubbles:true}));
      cutoff.dispatchEvent(new Event('change', {bubbles:true}));
      await wait(250);
      const text = document.body.innerText;
      const architecture = document.querySelector('a[href="/architecture/"]');
      return {
        ok: select.value === 'B0006' && cutoff.value === '50',
        battery: select.value,
        cutoff: cutoff.value,
        measured: text.includes('MEASURED CAPACITY'),
        soh: text.includes('CALCULATED SOH'),
        comparison: text.includes('Compare cells'),
        decision: text.includes('DECISION'),
        rul: text.includes('RUL BASELINE'),
        architecture: Boolean(architecture),
      };
    })()`,
  });
  const evidence = result.result.value;
  const passed = evidence.ok && ['measured', 'soh', 'comparison', 'decision', 'rul', 'architecture'].every(k => evidence[k]);
  console.log(JSON.stringify(evidence, null, 2));
  if (!passed) process.exitCode = 1;
} finally {
  socket?.close();
  chrome.kill('SIGTERM');
  await delay(500);
  rmSync(profile, {recursive: true, force: true, maxRetries: 5, retryDelay: 200});
}
