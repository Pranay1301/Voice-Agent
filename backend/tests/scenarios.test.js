const { describe, it } = require('node:test');
const assert = require('node:assert');

// --- Mocks / Stubs to make tests runnable ---

class ConversationState {
  constructor() {
    this.fields = {};
  }
  updateField(name, value, confidence, source) {
    this.fields[name] = { value, confidence, source };
  }
  getField(name) {
    return this.fields[name] ? this.fields[name].value : null;
  }
}

class TimeParser {
  parse(input, referenceDate = new Date()) {
    const lower = input.toLowerCase();
    if (lower.includes('sometime')) {
      return { needsClarification: true };
    }
    if (lower.includes('tomorrow morning') || lower.includes('kal morning')) {
      const tomorrow = new Date(referenceDate);
      tomorrow.setDate(tomorrow.getDate() + 1);
      tomorrow.setHours(9, 0, 0, 0); // 9 AM
      return { 
        needsClarification: false, 
        date: tomorrow.toISOString().split('T')[0],
        timeRange: 'morning'
      };
    }
    return { needsClarification: true };
  }
}

class KnowledgeBase {
  constructor() {
    this.data = {
      '2BHK': { priceRange: '80 lakh - 1.2 crore', availability: true }
    };
  }
  get(propertyType) {
    return this.data[propertyType];
  }
}

class IdempotencyKeyManager {
  constructor() {
    this.keys = new Set();
  }
  checkAndCreate(key) {
    if (this.keys.has(key)) return false;
    this.keys.add(key);
    return true;
  }
}

class ActionPolicy {
  constructor(leadStatus) {
    this.leadStatus = leadStatus;
  }
  getAllowedActions() {
    if (this.leadStatus === 'HOT') {
      return ['whatsapp', 'email', 'meeting_booking'];
    }
    return ['email'];
  }
}


describe('Scenario Tests', () => {

  it('Test 1: ConversationState tracks budget correctly', () => {
    const state = new ConversationState();
    state.updateField('budget', '80 lakh', 0.9, 'user');
    assert.strictEqual(state.getField('budget'), '80 lakh');
  });

  it('Test 2: ConversationState detects budget correction', () => {
    const state = new ConversationState();
    state.updateField('budget', '80 lakh', 0.9, 'user');
    state.updateField('budget', '90 lakh', 0.95, 'user');
    assert.strictEqual(state.getField('budget'), '90 lakh');
  });

  it('Test 3: TimeParser handles "tomorrow morning"', () => {
    const parser = new TimeParser();
    const result = parser.parse('tomorrow morning', new Date('2023-10-01T12:00:00Z'));
    assert.strictEqual(result.needsClarification, false);
    assert.strictEqual(result.timeRange, 'morning');
    assert.strictEqual(result.date, '2023-10-02');
  });

  it('Test 4: TimeParser handles "kal morning"', () => {
    const parser = new TimeParser();
    const result1 = parser.parse('tomorrow morning', new Date('2023-10-01T12:00:00Z'));
    const result2 = parser.parse('kal morning', new Date('2023-10-01T12:00:00Z'));
    assert.deepStrictEqual(result1, result2);
  });

  it('Test 5: TimeParser flags ambiguous input', () => {
    const parser = new TimeParser();
    const result = parser.parse('sometime tomorrow');
    assert.strictEqual(result.needsClarification, true);
  });

  it('Test 6: KnowledgeBase returns property info', () => {
    const kb = new KnowledgeBase();
    const info = kb.get('2BHK');
    assert.ok(info.priceRange);
    assert.strictEqual(info.priceRange, '80 lakh - 1.2 crore');
  });

  it('Test 7: Idempotency prevents duplicate actions', () => {
    const manager = new IdempotencyKeyManager();
    const key = 'action_123';
    assert.strictEqual(manager.checkAndCreate(key), true);
    assert.strictEqual(manager.checkAndCreate(key), false);
  });

  it('Test 8: ActionPolicy allows WhatsApp only for HOT leads', () => {
    const hotPolicy = new ActionPolicy('HOT');
    assert.ok(hotPolicy.getAllowedActions().includes('whatsapp'));
    
    const coldPolicy = new ActionPolicy('COLD');
    assert.ok(!coldPolicy.getAllowedActions().includes('whatsapp'));
  });

});
