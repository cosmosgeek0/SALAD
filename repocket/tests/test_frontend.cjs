const assert = require('assert');
const {normalize} = require('../dashboard/static/fleet-test.js');
const now = 1788800000000;
const data = {generated_ms: now - 50000, inventory_ms: now - 120000, desired: 1, running: 1, connected: 1,
  workers: [{current: true, salad_instance: 'fixture', salad_state: 'running', status: 'connected', phase: 'connected', native_fresh: true, network_fresh: true, source_ms: now - 50000, last_end_ms: now - 50000, last_mb_per_minute: 3}]};
let model = normalize('rp', data, now);
assert.equal(model.running, null); assert.equal(model.working, null);
assert.equal(model.nodes[0].rate, null); assert.equal(model.nodes[0].status, 'Unverified');
data.inventory_ms = now - 50000;
model = normalize('rp', data, now);
assert.equal(model.working, 1); assert.equal(model.nodes[0].rate, 3);
console.log('PASS independent inventory expiry and fresh native/network values.');
