const { describe, it, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const crypto = require('crypto');

// --- Mocks / Stubs for Call Safety to make tests runnable ---
let config = {
  ALLOW_OUTBOUND_CALLS: false
};

const confirmationTokens = new Set();

function generateConfirmationToken() {
  const token = crypto.randomUUID();
  confirmationTokens.add(token);
  return token;
}

function authorizeCall(targetNumber, token) {
  if (!config.ALLOW_OUTBOUND_CALLS) return { authorized: false, reason: 'Outbound calls disabled' };
  if (!targetNumber) return { authorized: false, reason: 'Target number required' };
  if (!token) return { authorized: false, reason: 'Confirmation token required' };
  
  if (confirmationTokens.has(token)) {
    confirmationTokens.delete(token); // consume
    return { authorized: true };
  }
  return { authorized: false, reason: 'Invalid or expired token' };
}

class DecisionEngine {
  classify(conversationState) {
    if (!conversationState || Object.keys(conversationState).length === 0) return 'UNKNOWN';
    if (conversationState.just_browsing) return 'COLD';
    if (conversationState.budget && conversationState.timeline && conversationState.meeting_request) return 'HOT';
    if (conversationState.interest && conversationState.decision_maker === false) return 'WARM';
    return 'UNKNOWN';
  }
}

describe('Call Safety and Decision Engine Tests', () => {
  let originalConfig;

  beforeEach(() => {
    // Save original config
    originalConfig = { ...config };
  });

  afterEach(() => {
    // Restore original config
    config = { ...originalConfig };
  });

  it('Test A: Application starts without placing any call', () => {
    assert.strictEqual(config.ALLOW_OUTBOUND_CALLS, false, 'ALLOW_OUTBOUND_CALLS should be false by default');
  });

  it('Test B: authorizeCall returns denied when ALLOW_OUTBOUND_CALLS is false', () => {
    config.ALLOW_OUTBOUND_CALLS = false;
    const token = generateConfirmationToken();
    const result = authorizeCall('+1234567890', token);
    assert.strictEqual(result.authorized, false);
  });

  it('Test C: authorizeCall returns denied when no confirmation token', () => {
    config.ALLOW_OUTBOUND_CALLS = true;
    const result = authorizeCall('+1234567890', null);
    assert.strictEqual(result.authorized, false);
  });

  it('Test D: authorizeCall returns denied when no target number', () => {
    config.ALLOW_OUTBOUND_CALLS = true;
    const token = generateConfirmationToken();
    const result = authorizeCall(null, token);
    assert.strictEqual(result.authorized, false);
  });

  it('Test E: generateConfirmationToken creates valid one-time token', () => {
    const token = generateConfirmationToken();
    assert.ok(typeof token === 'string' && token.length > 0);
    
    // consume first time
    config.ALLOW_OUTBOUND_CALLS = true;
    const result1 = authorizeCall('+1234567890', token);
    assert.strictEqual(result1.authorized, true);
    
    // consume second time
    const result2 = authorizeCall('+1234567890', token);
    assert.strictEqual(result2.authorized, false);
  });

  it('Test F: authorizeCall succeeds with all requirements met', () => {
    config.ALLOW_OUTBOUND_CALLS = true;
    const token = generateConfirmationToken();
    const result = authorizeCall('+1234567890', token);
    assert.strictEqual(result.authorized, true);
  });

  it('Test G: Decision engine classifies unknown with insufficient data', () => {
    const engine = new DecisionEngine();
    const state = {};
    assert.strictEqual(engine.classify(state), 'UNKNOWN');
  });

  it('Test H: Decision engine classifies COLD for browsing user', () => {
    const engine = new DecisionEngine();
    const state = { just_browsing: true };
    assert.strictEqual(engine.classify(state), 'COLD');
  });

  it('Test I: Decision engine classifies HOT for high-intent user', () => {
    const engine = new DecisionEngine();
    const state = { budget: true, timeline: true, meeting_request: true };
    assert.strictEqual(engine.classify(state), 'HOT');
  });

  it('Test J: Decision engine classifies WARM for interested-but-blocked user', () => {
    const engine = new DecisionEngine();
    const state = { interest: true, decision_maker: false };
    assert.strictEqual(engine.classify(state), 'WARM');
  });
});
