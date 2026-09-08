"use strict";

// The official PR native client, with measurements and recovery on the Salad node.
const fs = require("fs");
const os = require("os");
const crypto = require("crypto");
const net = require("net");
const readline = require("readline");
const {spawn} = require("child_process");

const POLICY = {connect_ms: 60000, registration_ms: 900000, process_stall_ms: 60000,
  provider_step_ms: 300000, provider_fresh_ms: 900000, offline_ms: 600000};
const API = "https://peer.proxyrack.com/api/";
const CLIENT_URL = "https://app-updates.sock.sh/peerclient/go/client";
const VERSION_URL = "https://app-updates.sock.sh/peerclient/go/version.txt";
const CLIENT = "/app/pr-client";
const instance = process.env.SALAD_INSTANCE_ID;
const machine = process.env.SALAD_MACHINE_ID;
const namespace = process.env.PR_NAMESPACE;
const key = process.env.PR_API_KEY || "";
delete process.env.PR_API_KEY;
const device = crypto.createHash("sha256").update(namespace + ":" + instance).digest("hex").toUpperCase();
const name = "PR-" + String(instance).slice(0, 8);
const pending = new Set();
const timers = new Set();
let child, ending = false, connected = false, registered = false, state = "starting", error = "none";
let observer, seq = 0, eventSeq = 0, base, previous, previousMs, bucketMs, ip = "-";
let connectSince = Date.now(), lastActivity = Date.now(), watchCounters, providerBusy = false;
let registrationAt, registrationDeadline, registrationAttempts = 0, providerAt = Infinity, providerKind = "status";
let lastNativeError = null, nativeErrors = [];
const providerErrors = {};
let providerOnline = null, statusChecked = null, offlineSince = null;
let creditValue = null, creditObserved = null, creditChecked = null, lastCreditIncrease = null;
let accountIssue = null, processStalledSince = null;

const now = () => Math.floor(Date.now() / 1000) * 1000;
const jitter = maximum => crypto.randomInt(maximum + 1);
const safe = value => (key ? String(value).split(key).join("[redacted]") : String(value)).slice(0, 240);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
function event(kind, fields = {}) {
  console.log("PR_EVENT_V1 " + JSON.stringify({kind, time_ms: Date.now(), instance, machine, device,
    observer, event_seq: eventSeq++, ...fields}));
}
function counters() {
  const rx = Number(fs.readFileSync("/sys/class/net/eth0/statistics/rx_bytes", "utf8").trim());
  const tx = Number(fs.readFileSync("/sys/class/net/eth0/statistics/tx_bytes", "utf8").trim());
  if (![rx, tx].every(value => Number.isSafeInteger(value) && value >= 0)) throw Error("Invalid network counters");
  return {rx, tx};
}
function resetCounters(current) {
  observer = now(); seq = 0; base = previous = current; previousMs = observer;
  bucketMs = Math.floor(previousMs / 60000) * 60000; watchCounters = current;
}
function policy() {
  const at = Date.now(), usable = creditObserved !== null && at - creditObserved <= POLICY.provider_fresh_ms && !providerErrors.bandwidth;
  return {state: ending ? state : accountIssue ? "account_cooldown" : !registered ? "registering" : !usable ? "provider_unknown" : "observing",
    ...POLICY, account_issue: accountIssue, retry_at_ms: registered ? providerAt : registrationAt,
    last_credit_increase_ms: lastCreditIncrease,
    last_activity_ms: lastActivity, provider_online: providerOnline, provider_checked_ms: statusChecked,
    credit_checked_ms: creditChecked, credit_observed_ms: creditObserved, provider_errors: {...providerErrors},
    native_error: lastNativeError, native_errors_5m: nativeErrors.filter(atMs => at - atMs <= 300000).length};
}
function record(final = 0, uncertainIp = false) {
  if (!base) return;
  const current = counters(), end = now();
  let sampleState = state, sampleError = error;
  if (!ending && connected && !registered) { sampleState = "starting"; sampleError = "registration_pending"; }
  const values = {worker: name, device, instance, machine, observer, seq, start_ms: previousMs, end_ms: end,
    rx: current.rx - previous.rx, tx: current.tx - previous.tx,
    total_rx: current.rx - base.rx, total_tx: current.tx - base.tx, ip,
    state: sampleState, error: sampleError, final, registered: Number(registered), bucket_ms: bucketMs,
    valid: Number(current.rx >= previous.rx && current.tx >= previous.tx && end >= previousMs)};
  if (uncertainIp) values.ip = "-";
  console.log("PR_MINUTE_V2 " + JSON.stringify({...values, policy: policy(), event_seq: eventSeq++}));
  previous = current; previousMs = end; bucketMs = Math.floor(end / 60000) * 60000; seq++;
  if (values.rx < 0 || values.tx < 0 || end < values.start_ms) {
    event("counter_reset"); resetCounters(current); seq = 1;
  }
}
function scheduleMinute() {
  const timer = setTimeout(() => {
    timers.delete(timer);
    if (!ending) { record(); scheduleMinute(); }
  }, 60000 - Date.now() % 60000 + 5);
  timers.add(timer);
}

function curl(url, args = [], headers = [], body, timeout = 25000) {
  return new Promise((resolve, reject) => {
    const process = spawn("curl", ["-sS", "--connect-timeout", "5", "--max-time", "15", "--config", "-",
      ...args, "--write-out", "\n%{http_code}", url], {stdio: ["pipe", "pipe", "pipe"]});
    pending.add(process);
    let out = "", err = "", settled = false;
    const timer = setTimeout(() => process.kill("SIGKILL"), timeout);
    process.stdout.on("data", bytes => { out += bytes; if (out.length > 2000000) process.kill("SIGKILL"); });
    process.stderr.on("data", bytes => { err = (err + bytes).slice(-1000); });
    const finish = (failure, result) => {
      if (settled) return; settled = true; clearTimeout(timer); pending.delete(process);
      if (failure) reject(failure); else resolve(result);
    };
    process.on("error", failure => finish(failure));
    process.on("close", status => {
      const newline = out.lastIndexOf("\n"), code = Number(out.slice(newline + 1));
      if (status || newline < 0 || !Number.isInteger(code)) {
        const failure = Error(safe(err || "Request did not complete")); failure.transport = true; finish(failure);
      } else finish(null, {code, body: out.slice(0, newline)});
    });
    const config = headers.map(header => "header = " + JSON.stringify(header)).join("\n") + "\n";
    process.stdin.on("error", () => {});
    process.stdin.end(config + (body === undefined ? "" : "data-binary = " + JSON.stringify(JSON.stringify(body)) + "\n"));
  });
}
function providerFailure(http, message) {
  const failure = Error(safe(message)); failure.http = http;
  if (http === 429 || /limit.*exceed|rate.?limit|too many requests|quota.*(?:exceed|limit)/i.test(failure.message)) failure.account = "rate_limited";
  else if (http === 401 || http === 403 || /(?:invalid|expired|revoked).*(?:key|token)|unauthori[sz]ed|authentication|forbidden/i.test(failure.message)) failure.account = "authorization";
  return failure;
}
async function peer(method, body) {
  const headers = ["Api-Key: " + key, "Content-Type: application/json", "Accept: application/json"];
  let response;
  try { response = await curl(API + method, ["-X", "POST"], headers, body); }
  catch (failure) {
    if (!/Could not resolve host|Resolving timed out/i.test(failure.message)) throw failure;
    event("dns_fallback", {method});
    response = await curl(API + method, ["-X", "POST", "--doh-url", "https://1.1.1.1/dns-query"], headers, body);
  }
  let value;
  try { value = JSON.parse(response.body); } catch (_) { throw providerFailure(response.code, "Provider returned invalid JSON"); }
  if (response.code !== 200 || !value || value.status !== "success" || !value.data || typeof value.data !== "object") {
    throw providerFailure(response.code, value && value.error || "Provider HTTP " + response.code);
  }
  return value.data;
}
function providerTime(text, checked) {
  if (typeof text !== "string") return null;
  if (/updated\s+(?:just now|a few seconds ago)/i.test(text)) return checked;
  const match = text.match(/updated\s+(\d+)\s+(second|minute|hour|day)s?\s+ago/i);
  if (!match) return null;
  return checked - Number(match[1]) * {second: 1000, minute: 60000, hour: 3600000, day: 86400000}[match[2].toLowerCase()];
}
async function register() {
  providerBusy = true;
  try {
    let data;
    try { data = await peer("device/add", {device_id: device, device_name: name}); }
    catch (failure) {
      if (failure.http !== 400 || !/already.*taken|already.*exist/i.test(failure.message)) throw failure;
      data = await peer("device/status", {device_id: device});
    }
    if (data.device_id !== device) throw Error("Provider returned a different device identity");
    if (ending) return;
    registered = true; accountIssue = null; delete providerErrors.registration;
    providerAt = Date.now() + 30000 + jitter(POLICY.provider_step_ms);
    event("registered", {checked_ms: Date.now()});
  } catch (failure) {
    if (!ending) {
      providerErrors.registration = safe(failure.message);
      accountIssue = failure.account ? {kind: failure.account, error: providerErrors.registration, since_ms: Date.now()} : null;
      if (accountIssue) registrationDeadline = Date.now() + POLICY.registration_ms;
      event("registration_retry", {error: providerErrors.registration, http: failure.http || 0, account_issue: failure.account || null});
      registrationAttempts++;
      registrationAt = Date.now() + Math.min(300000, 60000 * 2 ** Math.min(registrationAttempts - 1, 4)) + jitter(60000);
    }
  } finally { providerBusy = false; watchCounters = base ? counters() : null; }
}
async function checkProvider() {
  providerBusy = true;
  const kind = providerKind;
  providerKind = kind === "status" ? "bandwidth" : "status";
  providerAt = Date.now() + POLICY.provider_step_ms + jitter(30000);
  try {
    const body = {device_id: device};
    if (kind === "bandwidth") Object.assign(body, {date_start: process.env.PR_BANDWIDTH_START || new Date(observer).toISOString().slice(0, 10), date_end: new Date().toISOString().slice(0, 10)});
    const data = await peer(kind === "status" ? "device/status" : "bandwidth", body);
    if (ending) return;
    const checked = Date.now();
    accountIssue = null;
    if (kind === "status") {
      if (data.device_id !== device || typeof data.status !== "string") throw Error("Invalid provider status identity");
      const match = data.status.match(/^(Online|Offline)(?::\s*(\S+))?$/i);
      if (!match) throw Error("Unrecognized provider connection status");
      providerOnline = match[1].toLowerCase() === "online"; statusChecked = checked;
      delete providerErrors.status;
      offlineSince = providerOnline ? null : offlineSince === null ? checked : offlineSince;
      if (match[2] && net.isIP(match[2])) {
        if (ip !== match[2]) {
          record(0, ip !== "-");
          event("ip_changed", {previous_ip: ip, ip: match[2], checked_ms: checked});
        }
        ip = match[2];
      }
      event("provider", {reading: {kind, checked_ms: checked, status: data.status, online: providerOnline, ip: ip === "-" ? null : ip}});
      if (!providerOnline && checked - offlineSince >= POLICY.offline_ms) await finish("provider_offline", true);
    } else {
      const days = data.bandwidth;
      if (!days || typeof days !== "object" || Array.isArray(days) || !Object.keys(days).length ||
          !Object.entries(days).every(([day, value]) => /^\d{4}-\d{2}-\d{2}$/.test(day) && day >= body.date_start && day <= body.date_end &&
            typeof value === "number" && Number.isFinite(value) && value >= 0)) throw Error("Provider has not returned valid dated bandwidth readings");
      const value = Object.values(days).reduce((sum, amount) => sum + amount, 0);
      if (!Number.isFinite(value)) throw Error("Invalid provider bandwidth total");
      const observed = providerTime(data.state, checked);
      creditChecked = checked;
      delete providerErrors.bandwidth;
      if (observed !== null && checked - observed <= POLICY.provider_fresh_ms && (creditObserved === null || observed > creditObserved)) {
        if (creditValue !== null && value > creditValue) lastCreditIncrease = observed;
        else if (creditValue !== null && value < creditValue) event("provider_adjustment", {previous: creditValue, value, observed_ms: observed});
        creditValue = value; creditObserved = observed;
      }
      event("provider", {reading: {kind, checked_ms: checked, observed_ms: observed, provider_state: data.state || null,
        value, days, date_start: body.date_start, date_end: body.date_end}});
    }
  } catch (failure) {
    if (!ending) {
      providerErrors[kind] = safe(failure.message);
      if (failure.account) accountIssue = {kind: failure.account, error: providerErrors[kind], since_ms: Date.now()};
      event("provider", {reading: {kind, checked_ms: Date.now(), error: providerErrors[kind], http: failure.http || 0}});
    }
  } finally { providerBusy = false; watchCounters = base ? counters() : null; }
}
function nativeLine(line) {
  if (ending) return;
  console.log("PR_LOG worker=" + name + " instance=" + instance + " " + safe(line));
  if (line.includes("connected to home:")) { connected = true; state = "running"; error = "none"; connectSince = null; }
  else if (line.includes("connecting to home:")) {
    connected = false; state = "starting"; error = "connecting";
    if (connectSince === null) connectSince = Date.now();
  }
  if (/i\/o timeout|connection refused|no such host|network is unreachable|panic:|fatal error:/i.test(line)) {
    lastNativeError = {time_ms: Date.now(), message: safe(line)};
    nativeErrors = nativeErrors.filter(at => Date.now() - at <= 300000); nativeErrors.push(Date.now());
    event("native_error", {message: safe(line)});
  }
}
async function finish(reason, reallocate) {
  if (ending) return;
  ending = true; state = reallocate ? "reallocating" : "exited"; error = reason;
  for (const timer of timers) { clearInterval(timer); clearTimeout(timer); }
  for (const process of pending) process.kill("SIGKILL");
  if (child && child.exitCode === null) {
    child.kill("SIGTERM"); await delay(1000);
    if (child.exitCode === null) child.kill("SIGKILL");
  }
  try { record(1); } catch (failure) { event("measurement_error", {message: safe(failure.message)}); }
  if (reallocate) {
    event("reallocate_requested", {reason});
    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        const response = await curl("http://169.254.169.254/v1/reallocate",
          ["--noproxy", "*", "-X", "POST", "--connect-timeout", "3", "--max-time", "10"],
          ["Metadata: true", "Content-Type: application/json"], {reason: "PR " + reason}, 12000);
        const accepted = response.code === 200 || response.code === 204;
        event("reallocate_response", {reason, attempt, http: response.code, accepted});
        if (accepted) break;
      } catch (failure) { event("reallocate_response", {reason, attempt, http: 0, accepted: false, error: safe(failure.message)}); }
      if (attempt < 3) await delay(5000);
    }
  } else event("operator_stop");
  process.exit(reallocate ? 75 : 0);
}
async function main() {
  if (!instance || !machine || !namespace || !/^[A-Za-z0-9]+$/.test(key)) throw Error("Missing or invalid PR configuration");
  observer = now();
  const downloaded = await curl(CLIENT_URL, ["--retry", "2", "--retry-delay", "3", "--max-time", "45", "-o", CLIENT], [], undefined, 150000);
  if (downloaded.code !== 200) throw Error("Native client download HTTP " + downloaded.code);
  const version = await curl(VERSION_URL, ["--retry", "2", "--retry-delay", "3"]);
  if (version.code !== 200 || !/^\d+$/.test(version.body.trim())) throw Error("Native client version is unavailable");
  fs.chmodSync(CLIENT, 0o700);
  try {
    const answer = await curl("https://api.ipify.org", ["--max-time", "5"], [], undefined, 7000);
    if (answer.code === 200 && net.isIP(answer.body.trim())) ip = answer.body.trim();
  } catch (_) {}
  if (ending) return;
  resetCounters(counters()); lastActivity = connectSince = Date.now();
  registrationAt = Date.now() + 60000 + jitter(120000);
  registrationDeadline = Date.now() + POLICY.registration_ms;
  event("started", {version: version.body.trim(), policy: POLICY}); record(); scheduleMinute();
  child = spawn(CLIENT, ["--homeIp", "point-of-presence.sock.sh", "--homePort", "443", "--id", device,
    "--version", version.body.trim(), "--clientKey", "proxyrack-pop-client", "--clientType", "PoP",
    "--ppid", String(process.pid), "--osType", os.type(), "--osRelease", os.release(), "--osArch", os.arch()],
  {stdio: ["pipe", "pipe", "pipe"]});
  // The native program requires its stdin pipe to remain open.
  child.stdin.on("error", () => {});
  for (const stream of [child.stdout, child.stderr]) readline.createInterface({input: stream}).on("line", nativeLine);
  child.on("error", failure => { event("native_error", {message: safe(failure.message)}); finish("client_start_failed", true); });
  child.on("exit", () => { if (!ending) finish("client_exited", true); });
  const timer = setInterval(() => {
    if (ending) return;
    const at = Date.now(), current = counters();
    if (!providerBusy && watchCounters && (current.rx > watchCounters.rx || current.tx > watchCounters.tx)) lastActivity = at;
    watchCounters = current;
    if (connectSince !== null && at - connectSince >= POLICY.connect_ms) return void finish("connection_timeout", true);
    if (!registered && !accountIssue && at >= registrationDeadline) return void finish("registration_timeout", true);
    try {
      const stat = fs.readFileSync("/proc/" + child.pid + "/stat", "utf8");
      const processState = stat.slice(stat.lastIndexOf(")") + 2).split(" ")[0];
      if (["T", "t", "D"].includes(processState)) {
        if (processStalledSince === null) processStalledSince = at;
        if (at - processStalledSince >= POLICY.process_stall_ms) return void finish("process_stalled", true);
      } else processStalledSince = null;
    } catch (_) {} // The child exit event handles a process that disappeared.
    if (!providerBusy && !registered && at >= registrationAt) register();
    else if (!providerBusy && registered && at >= providerAt) checkProvider();
  }, 1000);
  timers.add(timer);
}
process.on("SIGTERM", () => finish("operator_stop", false));
process.on("SIGINT", () => finish("operator_stop", false));
process.on("uncaughtException", failure => { event("supervisor_error", {message: safe(failure.message)}); finish("supervisor_error", true); });
process.on("unhandledRejection", failure => { event("supervisor_error", {message: safe(failure)}); finish("supervisor_error", true); });
main().catch(failure => { event("startup_error", {message: safe(failure.message)}); finish("startup_failed", true); });
