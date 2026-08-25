const ConversationState = require('./conversationState');
const decisionEngine = require('./decisionEngine');

class TestModeEngine {
  constructor({ llmProvider, actionEngine, db }) {
    this.llmProvider = llmProvider;
    this.actionEngine = actionEngine;
    this.db = db;
    this.state = new ConversationState();
  }

  async simulateUserInput(text) {
    this.state.addTurn('user', text);
    
    // In a real system, you'd pass this to your LLM tool chain
    // Here we'll mock a simple response
    let agentResponse = "I understand. Can you tell me more about your requirements?";
    this.state.addTurn('assistant', agentResponse);
    
    // Simulate some state updates based on simple keyword matching for test purposes
    if (text.toLowerCase().includes('budget')) {
      this.state.updateField('budget', 'mentioned budget', 0.8, 'test');
    }
    if (text.toLowerCase().includes('meeting')) {
      this.state.updateField('meeting_interest', true, 0.9, 'test');
    }

    const classification = decisionEngine.classify(this.state);
    
    return {
      agentResponse,
      leadTemperature: classification.temperature,
      state: this.state.getStructuredState(),
      actions: []
    };
  }

  getState() {
    return this.state.getStructuredState();
  }

  reset() {
    this.state = new ConversationState();
  }
}

module.exports = TestModeEngine;
