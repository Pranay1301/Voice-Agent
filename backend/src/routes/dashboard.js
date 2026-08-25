const router = require('express').Router();
const database = require('../config/database');
const envConfig = require('../config/env');
const { getMetrics } = require('../utils/latencyTracker');

// GET /api/dashboard/state
router.get('/state', (req, res) => {
  const recentCalls = database.getCalls(10);
  const recentLeads = database.getLeads(10);

  res.json({
    testMode: envConfig.TEST_MODE === true,
    allowOutboundCalls: envConfig.ALLOW_OUTBOUND_CALLS === true,
    requireManualTrigger: envConfig.REQUIRE_MANUAL_CALL_TRIGGER === true,
    activeCall: null,
    recentCalls,
    recentLeads,
    providers: {
      telephony: Boolean(envConfig.TWILIO_ACCOUNT_SID && envConfig.TWILIO_AUTH_TOKEN),
      asr: Boolean(envConfig.DEEPGRAM_API_KEY),
      llm: Boolean(envConfig.GROQ_API_KEY),
      tts: Boolean(envConfig.ELEVENLABS_API_KEY && envConfig.ELEVENLABS_VOICE_ID),
      messaging: Boolean(envConfig.WHATSAPP_ACCESS_TOKEN),
      email: Boolean(envConfig.EMAIL_USER)
    }
  });
});

// GET /api/dashboard/calls/:id/debug
router.get('/calls/:id/debug', (req, res) => {
  const callId = req.params.id;
  const call = database.getCall(callId);
  const state = database.getConversationState(callId);
  const actions = database.getActionsByCallId(callId);
  const metrics = getMetrics(callId);

  res.json({
    call,
    state: state ? (typeof state.structured_state === 'string' ? JSON.parse(state.structured_state) : state.structured_state) : null,
    actions,
    metrics
  });
});

module.exports = router;
