const twilio = require('twilio');
const config = require('../config/env');
const { createLogger } = require('../utils/logger');
const logger = createLogger('twilioSignatureMiddleware');

/**
 * Twilio webhook signature validation middleware
 */
function validateTwilioSignature(req, res, next) {
  const twilioSignature = req.headers['x-twilio-signature'];
  const url = 'https://' + req.get('host') + req.originalUrl;
  
  if (!config.TWILIO_AUTH_TOKEN) {
    if (config.TEST_MODE) {
      logger.warn('Skipping Twilio signature validation in TEST_MODE (No Auth Token provided)');
      return next();
    }
    logger.error('TWILIO_AUTH_TOKEN is missing in production environment');
    return res.status(500).json({ error: 'Internal Server Error' });
  }

  if (!twilioSignature) {
    logger.warn('Missing x-twilio-signature header');
    return res.status(401).send('Unauthorized');
  }

  // Validate the signature
  const isValid = twilio.validateRequest(
    config.TWILIO_AUTH_TOKEN,
    twilioSignature,
    url,
    req.body || {}
  );

  if (isValid) {
    return next();
  }

  logger.warn('Invalid Twilio signature', { url, signature: twilioSignature });
  return res.status(401).send('Unauthorized');
}

module.exports = {
  validateTwilioSignature
};
