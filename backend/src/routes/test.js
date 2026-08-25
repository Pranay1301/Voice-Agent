const router = require('express').Router();
const ConversationEngine = require('../services/conversationEngine');
const GroqLLM = require('../providers/llm/groq');
const ActionEngine = require('../services/actionEngine');
const { broadcast } = require('../websocket/dashboardStream');
const config = require('../config/env');

const llmProvider = config.GROQ_API_KEY ? new GroqLLM({
  apiKey: config.GROQ_API_KEY,
  model: config.GROQ_MODEL,
  fallbackModel: config.GROQ_FALLBACK_MODEL
}) : null;

const actionEngine = new ActionEngine();
let activeTestEngine = null;

function getOrCreateTestEngine(callId = 'test_simulation') {
  if (!activeTestEngine || activeTestEngine.callId !== callId) {
    activeTestEngine = new ConversationEngine({
      callId,
      phone: '+919999999999',
      llmProvider,
      actionEngine,
      dashboardBroadcast: broadcast
    });
  }
  return activeTestEngine;
}

// POST /api/test/message
// Simulates user input turn for interactive test mode without telephony
router.post('/message', async (req, res) => {
  try {
    const { text, callId } = req.body;
    if (!text) {
      return res.status(400).json({ error: 'Text message is required' });
    }

    const engine = getOrCreateTestEngine(callId);
    let agentReply = '';

    engine.onAgentResponse = (chunk, isFinal) => {
      if (chunk) agentReply += chunk;
    };

    await engine.processUserInput(text);

    res.json({
      agentResponse: agentReply || "Understood. Let me note your requirements.",
      state: engine.state.getStructuredState(),
      leadTemperature: engine.state.lead_temperature,
      turns: engine.state.turns
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/test/reset
router.post('/reset', (req, res) => {
  activeTestEngine = null;
  res.json({ success: true, message: 'Test conversation reset' });
});

// GET /api/test/state
router.get('/state', (req, res) => {
  if (!activeTestEngine) {
    return res.json({ state: null, turns: [] });
  }
  res.json({
    state: activeTestEngine.state.getStructuredState(),
    leadTemperature: activeTestEngine.state.lead_temperature,
    turns: activeTestEngine.state.turns
  });
});

module.exports = router;
