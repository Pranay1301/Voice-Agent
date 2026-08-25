const { db } = require('../config/database');

/**
 * Generates a deterministic idempotency key
 * @param {string} callId 
 * @param {string} actionType 
 * @param {string|number} version 
 * @returns {string}
 */
function generateKey(callId, actionType, version) {
  return callId + ':' + actionType + ':' + version;
}

/**
 * Checks if key exists, if not creates a placeholder action record.
 * @param {string} key 
 * @returns {boolean} true if new, false if already exists
 */
function checkAndCreate(key) {
  try {
    const stmt = db.prepare('INSERT INTO actions (id, idempotency_key, type, status) VALUES (@id, @key, @type, @status)');
    stmt.run({
      id: require('crypto').randomUUID(),
      key: key,
      type: 'idempotency_lock',
      status: 'pending'
    });
    return true; // Key was inserted successfully
  } catch (error) {
    if (error.code === 'SQLITE_CONSTRAINT_UNIQUE') {
      return false; // Key already exists
    }
    throw error;
  }
}

module.exports = {
  generateKey,
  checkAndCreate
};
