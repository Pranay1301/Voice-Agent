class ConversationState {
  constructor() {
    this.name = { value: null, confidence: 0, source: null, turn: null };
    this.phone = { value: null, confidence: 0, source: null, turn: null };
    this.email = { value: null, confidence: 0, source: null, turn: null };
    this.language = { value: null, confidence: 0, source: null, turn: null };
    this.location = { value: null, confidence: 0, source: null, turn: null };
    this.property_interest = { value: null, confidence: 0, source: null, turn: null };
    this.property_type = { value: null, confidence: 0, source: null, turn: null };
    this.budget = { value: null, confidence: 0, source: null, turn: null };
    this.budget_numeric = { value: null, confidence: 0, source: null, turn: null };
    this.timeline = { value: null, confidence: 0, source: null, turn: null };
    this.purpose = { value: null, confidence: 0, source: null, turn: null };
    this.number_of_properties = { value: null, confidence: 0, source: null, turn: null };
    this.requirements = { value: null, confidence: 0, source: null, turn: null };
    this.features = { value: null, confidence: 0, source: null, turn: null };
    this.decision_maker = { value: null, confidence: 0, source: null, turn: null };
    this.decision_stage = { value: null, confidence: 0, source: null, turn: null };
    
    this.objections = [];
    this.concerns = [];
    this.buying_intent = 'unknown';
    this.lead_temperature = 'UNKNOWN';
    this.meeting_interest = false;
    this.preferred_callback_time = null;
    this.callback_requested = false;
    
    this.questions_asked = [];
    this.questions_answered = [];
    this.promises_made = [];
    this.important_quotes = [];
    
    this.conversation_summary = '';
    this.next_action = '';
    this.turns = [];
    this.current_turn = 0;
    this.changes = [];
  }

  updateField(field, value, confidence, source) {
    if (!this.hasOwnProperty(field)) {
      return { updated: false, error: 'Field does not exist' };
    }

    const previousValue = this[field].value;
    const conflict = previousValue !== null && previousValue !== value;

    if (conflict) {
      this.changes.push({
        field,
        oldValue: previousValue,
        newValue: value,
        turn: this.current_turn
      });
    }

    this[field] = {
      value,
      confidence,
      source,
      turn: this.current_turn
    };

    return { updated: true, previousValue, conflict };
  }

  getField(field) {
    if (this.hasOwnProperty(field) && typeof this[field] === 'object' && this[field] !== null && 'value' in this[field]) {
      return this[field].value;
    }
    return this[field];
  }

  getStructuredState() {
    const structured = {};
    for (const [key, prop] of Object.entries(this)) {
      if (prop && typeof prop === 'object' && 'value' in prop) {
        if (prop.value !== null) {
          structured[key] = prop.value;
        }
      } else if (key !== 'turns' && key !== 'changes') {
        structured[key] = prop;
      }
    }
    return structured;
  }

  addTurn(role, content, metadata = {}) {
    this.turns.push({
      role,
      content,
      metadata,
      turn: this.current_turn
    });
    this.current_turn++;
  }

  addObjection(objection) {
    this.objections.push({
      objection,
      turn: this.current_turn
    });
  }

  addQuote(quote) {
    this.important_quotes.push({
      quote,
      turn: this.current_turn
    });
  }

  getTranscript() {
    return this.turns
      .map(t => `${t.role.toUpperCase()}: ${t.content}`)
      .join('\n');
  }

  toJSON() {
    return JSON.stringify(this);
  }

  static fromJSON(json) {
    const state = new ConversationState();
    const data = typeof json === 'string' ? JSON.parse(json) : json;
    Object.assign(state, data);
    return state;
  }
}

module.exports = ConversationState;
