const { authorizeCall } = require('../services/callAuthorization');
const { createLogger } = require('../utils/logger');
const logger = createLogger('callSafetyMiddleware');

/**
 * Express middleware to check authorization for call-initiating endpoints
 */
function callSafetyMiddleware(req, res, next) {
  const { targetNumber, confirmationToken, sessionId } = req.body || {};
  
  const authResult = authorizeCall({ targetNumber, confirmationToken, sessionId });
  
  if (!authResult.authorized) {
    logger.warn('Call attempt blocked by safety middleware', { 
      reason: authResult.reason, 
      targetNumber, 
      ip: req.ip 
    });
    return res.status(403).json({ 
      error: 'Call Forbidden', 
      reason: authResult.reason 
    });
  }
  
  next();
}

module.exports = {
  callSafetyMiddleware
};
