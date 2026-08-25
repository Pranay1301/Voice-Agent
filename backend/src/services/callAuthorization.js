const crypto = require('crypto');
const config = require('../config/env');
const { createLogger } = require('../utils/logger');
const logger = createLogger('callAuthorization');

const activeTokens = new Set();
const sessionCallCounts = new Map();

/**
 * Creates a one-time use UUID token
 * @returns {string}
 */
function generateConfirmationToken() {
  const token = crypto.randomUUID();
  activeTokens.add(token);
  // Expire token after 10 minutes to prevent leaks
  setTimeout(() => activeTokens.delete(token), 10 * 60 * 1000);
  return token;
}

/**
 * Validates and removes token
 * @param {string} token 
 * @returns {boolean}
 */
function consumeConfirmationToken(token) {
  if (!token) return false;
  if (activeTokens.has(token)) {
    activeTokens.delete(token);
    return true;
  }
  return false;
}

/**
 * Quick check to see if calls are broadly allowed without token validation
 * @returns {boolean}
 */
function isCallAllowed() {
  return config.ALLOW_OUTBOUND_CALLS === true && config.REQUIRE_MANUAL_CALL_TRIGGER === true;
}

/**
 * Authorizes an outbound call request. NEVER bypass this.
 * @param {Object} params 
 * @param {string} params.targetNumber
 * @param {string} params.confirmationToken
 * @param {string} [params.sessionId]
 * @returns {{ authorized: boolean, reason: string }}
 */
function authorizeCall({ targetNumber, confirmationToken, sessionId }) {
  if (config.ALLOW_OUTBOUND_CALLS !== true) {
    return { authorized: false, reason: 'Outbound calls are disabled by system configuration (ALLOW_OUTBOUND_CALLS !== true).' };
  }
  
  if (config.REQUIRE_MANUAL_CALL_TRIGGER !== true) {
    return { authorized: false, reason: 'System safety requirement violated: REQUIRE_MANUAL_CALL_TRIGGER must be true.' };
  }

  if (!targetNumber || typeof targetNumber !== 'string') {
    return { authorized: false, reason: 'Invalid or missing target number.' };
  }

  if (sessionId) {
    const currentCount = sessionCallCounts.get(sessionId) || 0;
    if (currentCount >= config.MAX_CALLS_PER_SESSION) {
      return { authorized: false, reason: 'Maximum calls per session exceeded.' };
    }
    // Increment on successful auth
    sessionCallCounts.set(sessionId, currentCount + 1);
  }

  if (!consumeConfirmationToken(confirmationToken)) {
    logger.warn('Failed call authorization attempt: invalid or missing token', { targetNumber, sessionId });
    return { authorized: false, reason: 'Invalid, missing, or expired confirmation token.' };
  }

  logger.info('Call authorized successfully', { targetNumber, sessionId });
  return { authorized: true, reason: 'Authorized' };
}

module.exports = {
  generateConfirmationToken,
  consumeConfirmationToken,
  isCallAllowed,
  authorizeCall
};
