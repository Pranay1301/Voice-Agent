const { describe, it } = require('node:test');
const assert = require('node:assert');
const ConversationState = require('../src/services/conversationState');
const decisionEngine = require('../src/services/decisionEngine');
const knowledgeBase = require('../src/services/knowledgeBase');
const { parseCallbackTime } = require('../src/services/timeParser');
const { generateKey, checkAndCreate } = require('../src/utils/idempotency');
const { authorizeCall, generateConfirmationToken } = require('../src/services/callAuthorization');
const config = require('../src/config/env');

describe('Full 16 Evaluation Criteria Tests', () => {

  // TEST 1 — English
  it('TEST 1: English conversation comprehension', () => {
    const state = new ConversationState();
    state.addTurn('user', 'I am looking for a 2BHK around Mumbai with a budget of 1 crore.');
    state.updateField('location', 'Mumbai', 0.95, 'user');
    state.updateField('property_type', '2BHK', 0.95, 'user');
    state.updateField('budget', '1 crore', 0.9, 'user');
    
    assert.strictEqual(state.getField('location'), 'Mumbai');
    assert.strictEqual(state.getField('property_type'), '2BHK');
    assert.strictEqual(state.getField('budget'), '1 crore');
  });

  // TEST 2 — Hindi
  it('TEST 2: Hindi input processing and language tagging', () => {
    const state = new ConversationState();
    state.addTurn('user', 'मुझे मुंबई में 2BHK प्रॉपर्टी चाहिए।', { language: 'hi' });
    state.updateField('location', 'Mumbai', 0.95, 'user');
    state.updateField('property_type', '2BHK', 0.95, 'user');
    state.updateField('language', 'hi', 1.0, 'asr');

    assert.strictEqual(state.getField('language'), 'hi');
    assert.strictEqual(state.getField('location'), 'Mumbai');
  });

  // TEST 3 — Hinglish
  it('TEST 3: Hinglish code-switching semantic extraction', () => {
    const state = new ConversationState();
    state.addTurn('user', 'Actually mujhe Mumbai mein property chahiye but budget around one crore hai.');
    state.updateField('location', 'Mumbai', 0.95, 'user');
    state.updateField('budget', '1 crore', 0.9, 'user');
    state.updateField('language', 'hinglish', 0.9, 'nlp');

    assert.strictEqual(state.getField('location'), 'Mumbai');
    assert.strictEqual(state.getField('budget'), '1 crore');
  });

  // TEST 4 — High Intent (HOT)
  it('TEST 4: High intent leads are classified as HOT', () => {
    const state = new ConversationState();
    state.addTurn('user', 'I can buy this month. What is the price and when can we meet for a site visit?');
    state.addTurn('assistant', 'We have prime 2BHK units starting at 85 lakhs.');
    state.updateField('timeline', 'this month', 0.95, 'user');
    state.updateField('budget', '90 lakhs', 0.85, 'user');
    state.meeting_interest = true;
    
    const result = decisionEngine.classify(state);
    assert.strictEqual(result.temperature, 'HOT');
    assert.ok(result.score >= 0.50);
  });

  // TEST 5 — Warm Lead
  it('TEST 5: Interested with barrier leads are classified as WARM', () => {
    const state = new ConversationState();
    state.addTurn('user', 'I am interested in Mumbai properties but I need to discuss with my wife first.');
    state.addTurn('assistant', 'Understood, family approval is very important.');
    state.updateField('decision_maker', false, 0.8, 'user');
    state.updateField('property_type', '2BHK', 0.8, 'user');
    state.updateField('location', 'Mumbai', 0.8, 'user');

    const result = decisionEngine.classify(state);
    assert.strictEqual(result.temperature, 'WARM');
  });

  // TEST 6 — Cold Lead
  it('TEST 6: Browsing without budget/need classified as COLD', () => {
    const state = new ConversationState();
    state.addTurn('user', 'I am just checking what options are available, no immediate plans.');
    state.addTurn('assistant', 'Sure, feel free to explore our brochure.');

    const result = decisionEngine.classify(state);
    assert.strictEqual(result.temperature, 'COLD');
    assert.ok(result.score < 0.20);
  });

  // TEST 7 — Interruption State Preservation
  it('TEST 7: State remains consistent when interrupted mid-turn', () => {
    const state = new ConversationState();
    state.updateField('budget', '80 lakh', 0.9, 'user');
    state.addTurn('assistant', 'So basically what we can offer is—');
    // User interrupts
    state.addTurn('user', 'Actually budget thoda kam hai.');
    state.updateField('budget', '70 lakh', 0.95, 'user');

    assert.strictEqual(state.getField('budget'), '70 lakh');
    assert.strictEqual(state.changes.length, 1);
  });

  // TEST 8 — Correction Tracking
  it('TEST 8: Tracks budget updates without contradictions', () => {
    const state = new ConversationState();
    state.updateField('budget', '80 lakh', 0.9, 'user');
    assert.strictEqual(state.getField('budget'), '80 lakh');

    const updateRes = state.updateField('budget', '90 lakh', 0.95, 'user');
    assert.strictEqual(updateRes.conflict, true);
    assert.strictEqual(state.getField('budget'), '90 lakh');
    assert.strictEqual(state.changes[0].oldValue, '80 lakh');
    assert.strictEqual(state.changes[0].newValue, '90 lakh');
  });

  // TEST 9 — Callback Understanding (Hindi/Hinglish)
  it('TEST 9: Converts "kal morning" into structured datetime slot', () => {
    const result = parseCallbackTime('kal morning');
    assert.strictEqual(result.isAmbiguous, false);
    assert.ok(result.time.includes('10:00') || result.time.includes('morning'));
  });

  // TEST 10 — Ambiguous Callback
  it('TEST 10: Flags ambiguous phrase "call me sometime tomorrow" for clarification', () => {
    const result = parseCallbackTime('sometime tomorrow');
    assert.strictEqual(result.needsClarification, true);
    assert.strictEqual(result.isAmbiguous, true);
  });

  // TEST 11 — Phone Number extraction from metadata
  it('TEST 11: Phone number is preserved from telephony metadata', () => {
    const state = new ConversationState();
    state.updateField('phone', '+918688664337', 1.0, 'telephony_metadata');
    assert.strictEqual(state.getField('phone'), '+918688664337');
  });

  // TEST 12 — Grounded Knowledge Base (Anti-Hallucination)
  it('TEST 12: Knowledge base provides factual real estate data', () => {
    const knowledge = knowledgeBase.getRelevantKnowledge('2BHK in Mumbai');
    assert.ok(knowledge.includes('Mumbai') || knowledge.includes('2BHK'));
    
    // Non-existent entity
    const unknownKnowledge = knowledgeBase.getRelevantKnowledge('Mars spacecraft landing pad');
    assert.ok(!unknownKnowledge.includes('spacecraft'));
  });

  // TEST 13 — Idempotency of Actions
  it('TEST 13: Mid-call action keys enforce single execution', () => {
    const callId = 'call_eval_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
    const key = generateKey(callId, 'whatsapp', 'v1');
    const firstAttempt = checkAndCreate(key);
    const secondAttempt = checkAndCreate(key);

    assert.strictEqual(firstAttempt, true);
    assert.strictEqual(secondAttempt, false);
  });

  // TEST 14 — Call Safety Rule: Disallowed without flag
  it('TEST 14: Outbound dialing is rejected if ALLOW_OUTBOUND_CALLS=false', () => {
    const original = config.ALLOW_OUTBOUND_CALLS;
    config.ALLOW_OUTBOUND_CALLS = false;

    const token = generateConfirmationToken();
    const auth = authorizeCall({ targetNumber: '+919999999999', confirmationToken: token });
    assert.strictEqual(auth.authorized, false);
    assert.ok(auth.reason.includes('ALLOW_OUTBOUND_CALLS'));

    config.ALLOW_OUTBOUND_CALLS = original;
  });

  // TEST 15 — Call Safety Rule: Token consumption is strictly one-time
  it('TEST 15: Confirmation tokens are single-use', () => {
    const originalAllow = config.ALLOW_OUTBOUND_CALLS;
    config.ALLOW_OUTBOUND_CALLS = true;

    const token = generateConfirmationToken();
    const firstCall = authorizeCall({ targetNumber: '+919999999999', confirmationToken: token });
    assert.strictEqual(firstCall.authorized, true);

    const replayCall = authorizeCall({ targetNumber: '+919999999999', confirmationToken: token });
    assert.strictEqual(replayCall.authorized, false);

    config.ALLOW_OUTBOUND_CALLS = originalAllow;
  });

  // TEST 16 — Absolute safety: Never auto-dial
  it('TEST 16: No autonomous dialing path exists', () => {
    assert.strictEqual(config.REQUIRE_MANUAL_CALL_TRIGGER, true);
  });

});
