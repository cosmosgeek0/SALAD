const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../static/ps1.js'), 'utf8');
const channel = 'simulated-provider-channel';
const reading = {type: 'ps-credited', channel, gb: 1.25, bytes: 1250000000, time_ms: 1788666387000};
const response = (status, body = {}) => ({status, ok: status >= 200 && status < 300, json: async () => body});

function bridge(fetchReply, hash = '#ps1') {
  const listeners = new Map();
  const calls = [];
  const element = () => ({textContent: '', addEventListener() {}});
  const elements = {psConnect: element(), psFeedStatus: element(), history: element()};
  const location = {hash};
  const context = {
    location,
    window: {location, addEventListener: (name, handler) => listeners.set(name, handler)},
    document: {getElementById: id => elements[id]},
    sessionStorage: {getItem: key => key === 'ps-billing-channel' ? channel : null},
    AbortSignal: {timeout: () => undefined},
    fetch: async (url, options) => {
      calls.push({url, options});
      return fetchReply(url, options, calls);
    },
  };
  vm.runInNewContext(source, context, {filename: 'ps1.js'});
  return {
    calls,
    message: elements.psFeedStatus,
    location,
    emit: overrides => listeners.get('message')({
      origin: 'https://app.packetstream.io', data: {...reading}, ...overrides,
    }),
  };
}

test('untrusted origins and channels cannot fetch or save provider readings', async () => {
  const app = bridge(() => {throw new Error('Rejected messages must not fetch');});
  for (const overrides of [
    {origin: 'https://unrelated.example'},
    {origin: 'https://app.packetstream.io.unrelated.example'},
    {data: {...reading, channel: 'wrong-channel'}},
    {data: {...reading, channel: ''}},
    {data: {...reading, type: 'unrelated-message'}},
  ]) await app.emit(overrides);
  assert.equal(app.calls.length, 0);
  assert.equal(app.message.textContent, '');
});

test('provider messages are saved while either service tab is selected', async () => {
  for (const hash of ['#hg1', '#ps1']) {
    const app = bridge(url => url === '/api/ps1/view'
      ? response(200, {bridge_token: 'simulated-token', feed_age_ms: 1000})
      : response(200), hash);
    await app.emit();
    assert.deepEqual(app.calls.map(call => call.url), ['/api/ps1/view', '/api/ps1/credited']);
    const saved = app.calls[1].options;
    assert.equal(saved.method, 'POST');
    assert.equal(saved.headers['X-PS-Token'], 'simulated-token');
    assert.deepEqual(JSON.parse(saved.body), {gb: reading.gb, bytes: reading.bytes, time_ms: reading.time_ms});
    assert.equal(app.message.textContent, 'Provider reading saved.');
    assert.equal(app.location.hash, hash);
  }
});

test('a later push obtains the new token after a dashboard restart', async () => {
  let token = 'before-restart';
  const app = bridge((url, options) => {
    if (url === '/api/ps1/view') return response(200, {bridge_token: token});
    return response(options.headers['X-PS-Token'] === token ? 200 : 403);
  });
  await app.emit();
  token = 'after-restart';
  await app.emit();
  assert.deepEqual(app.calls.map(call => call.url), [
    '/api/ps1/view', '/api/ps1/credited', '/api/ps1/view', '/api/ps1/credited',
  ]);
  assert.deepEqual(app.calls.filter(call => call.url === '/api/ps1/credited')
    .map(call => call.options.headers['X-PS-Token']), ['before-restart', 'after-restart']);
  assert.equal(app.message.textContent, 'Provider reading saved.');
});

test('a 403 between reading the token and saving refreshes and retries once', async () => {
  let reads = 0;
  const app = bridge((url, options) => {
    if (url === '/api/ps1/view') return response(200, {bridge_token: ++reads === 1 ? 'expired-token' : 'fresh-token'});
    return response(options.headers['X-PS-Token'] === 'fresh-token' ? 200 : 403);
  });
  await app.emit();
  assert.deepEqual(app.calls.map(call => call.url), [
    '/api/ps1/view', '/api/ps1/credited', '/api/ps1/view', '/api/ps1/credited',
  ]);
  const saves = app.calls.filter(call => call.url === '/api/ps1/credited');
  assert.deepEqual(saves.map(call => call.options.headers['X-PS-Token']), ['expired-token', 'fresh-token']);
  assert.equal(saves[0].options.body, saves[1].options.body);
  assert.equal(app.message.textContent, 'Provider reading saved.');
});

test('a second 403 stops retrying and leaves an explicit failure', async () => {
  const app = bridge(url => url === '/api/ps1/view'
    ? response(200, {bridge_token: 'still-rejected-token'})
    : response(403));
  await app.emit();
  assert.equal(app.calls.filter(call => call.url === '/api/ps1/view').length, 2);
  assert.equal(app.calls.filter(call => call.url === '/api/ps1/credited').length, 2);
  assert.equal(app.message.textContent, 'Provider reading could not be saved.');
});
