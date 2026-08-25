const router = require('express').Router();
const crypto = require('crypto');
const database = require('../config/database');
const envConfig = require('../config/env');
const { authorizeCall, generateConfirmationToken } = require('../services/callAuthorization');
const TwilioTelephony = require('../providers/telephony/twilio');
const { createLogger } = require('../utils/logger');
const logger = createLogger('callsRoute');

const twilioProvider = envConfig.TWILIO_ACCOUNT_SID && envConfig.TWILIO_AUTH_TOKEN ? new TwilioTelephony({
  accountSid: envConfig.TWILIO_ACCOUNT_SID,
  authToken: envConfig.TWILIO_AUTH_TOKEN,
  phoneNumber: envConfig.TWILIO_PHONE_NUMBER
}) : null;

// GET /api/calls/confirmation-token
// Generates a one-time confirmation token for the manual button trigger
router.get('/confirmation-token', (req, res) => {
  const token = generateConfirmationToken();
  res.json({ token });
});

// POST /api/calls/start
// STRICTLY VALIDATED: Requires manual confirmationToken, explicit targetNumber, and ALLOW_OUTBOUND_CALLS=true
router.post('/start', async (req, res) => {
  try {
    const { targetNumber, confirmationToken, sessionId } = req.body;

    if (envConfig.TEST_MODE) {
      const testCallId = 'test_call_' + Date.now();
      logger.info(`Test Mode active: Simulated outbound call to ${targetNumber}`);
      
      database.insertCall({
        id: testCallId,
        twilio_call_sid: 'SIMULATED_' + crypto.randomUUID().substring(0, 8),
        metadata: { targetNumber, mode: 'test_mode' },
        status: 'simulated_active'
      });

      return res.json({
        callId: testCallId,
        status: 'test_mode',
        message: 'Test mode active - conversation simulated without telephony charges'
      });
    }

    // Full Authorization Check
    const authResult = authorizeCall({ targetNumber, confirmationToken, sessionId });
    if (!authResult.authorized) {
      logger.warn(`Call blocked: ${authResult.reason}`, { targetNumber });
      return res.status(403).json({
        error: 'Outbound call authorization denied',
        reason: authResult.reason
      });
    }

    if (!twilioProvider) {
      return res.status(500).json({
        error: 'Twilio telephony provider not configured. Please supply TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env'
      });
    }

    const callId = 'call_' + crypto.randomUUID();
    const webhookBaseUrl = envConfig.TWILIO_WEBHOOK_BASE_URL;
    const webhookUrl = `${webhookBaseUrl}/api/twilio/voice`;
    const statusCallbackUrl = `${webhookBaseUrl}/api/twilio/status`;

    logger.info(`Placing authorized manual outbound call to ${targetNumber}`);
    const callResult = await twilioProvider.createOutboundCall({
      to: targetNumber,
      webhookUrl,
      statusCallbackUrl
    });

    database.insertCall({
      id: callId,
      twilio_call_sid: callResult.callSid,
      metadata: { targetNumber },
      status: 'initiated'
    });

    res.json({
      callId,
      twilioCallSid: callResult.callSid,
      status: 'initiating'
    });

  } catch (err) {
    logger.error('Error initiating outbound call', err);
    res.status(500).json({ error: err.message });
  }
});

// GET /api/calls/:id
router.get('/:id', (req, res) => {
  const call = database.getCall(req.params.id);
  if (!call) {
    return res.status(404).json({ error: 'Call not found' });
  }
  res.json(call);
});

// POST /api/calls/:id/end
router.post('/:id/end', async (req, res) => {
  try {
    const call = database.getCall(req.params.id);
    if (call && call.twilio_call_sid && twilioProvider) {
      await twilioProvider.endCall(call.twilio_call_sid);
    }
    database.updateCall(req.params.id, { status: 'completed', ended_at: new Date().toISOString() });
    res.json({ success: true, message: 'Call terminated' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/calls
router.get('/', (req, res) => {
  const calls = database.getCalls(20);
  res.json(calls);
});

module.exports = router;
