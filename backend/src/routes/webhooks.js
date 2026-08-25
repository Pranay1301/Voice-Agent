const router = require('express').Router();
const database = require('../config/database');
const envConfig = require('../config/env');
const { createLogger } = require('../utils/logger');
const logger = createLogger('webhooks');

// POST /api/twilio/voice
// Invoked by Twilio when an outbound/inbound call is connected
router.post('/voice', (req, res) => {
  const host = envConfig.TWILIO_WEBHOOK_BASE_URL 
    ? envConfig.TWILIO_WEBHOOK_BASE_URL.replace(/^https?:\/\//, '')
    : req.headers.host;
    
  const streamUrl = `wss://${host}/media-stream`;
  logger.info(`Generating TwiML MediaStream connection: ${streamUrl}`);

  const twiml = `<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="${streamUrl}">
      <Parameter name="phoneNumber" value="${req.body.To || req.body.From || ''}" />
    </Stream>
  </Connect>
</Response>`;

  res.type('text/xml');
  res.send(twiml);
});

// POST /api/twilio/status
// Status callback for call lifecycle events
router.post('/status', (req, res) => {
  const { CallSid, CallStatus, CallDuration } = req.body;
  logger.info(`Twilio Call Status Callback: CallSid=${CallSid}, Status=${CallStatus}, Duration=${CallDuration}`);

  try {
    const existingCall = database.getCall(CallSid);
    if (existingCall) {
      database.updateCall(existingCall.id, {
        status: CallStatus,
        duration: CallDuration ? parseInt(CallDuration, 10) : existingCall.duration
      });
    }
  } catch (err) {
    logger.error('Error updating call status from webhook', err);
  }

  res.sendStatus(200);
});

module.exports = router;
