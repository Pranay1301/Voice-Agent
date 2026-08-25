const timers = new Map();

/**
 * Starts a timer for a specific phase
 * @param {string} callId 
 * @param {string|number} turnId 
 * @param {string} phase (e.g., 'asr', 'llm', 'tts', 'total', 'action')
 */
function startTimer(callId, turnId, phase) {
  const key = callId + ':' + turnId;
  if (!timers.has(key)) {
    timers.set(key, {});
  }
  timers.get(key)[phase] = { start: process.hrtime.bigint(), end: null, durationMs: null };
}

/**
 * Ends a timer and returns duration in ms
 * @param {string} callId 
 * @param {string|number} turnId 
 * @param {string} phase 
 * @returns {number|null}
 */
function endTimer(callId, turnId, phase) {
  const key = callId + ':' + turnId;
  const turnTimers = timers.get(key);
  if (!turnTimers || !turnTimers[phase] || !turnTimers[phase].start) return null;
  
  const end = process.hrtime.bigint();
  const start = turnTimers[phase].start;
  const durationMs = Number(end - start) / 1e6;
  
  turnTimers[phase].end = end;
  turnTimers[phase].durationMs = durationMs;
  
  return durationMs;
}

/**
 * Gets all metrics for a call
 * @param {string} callId 
 * @returns {Object}
 */
function getMetrics(callId) {
  const results = {};
  const prefix = callId + ':';
  for (const [key, phases] of timers.entries()) {
    if (key.startsWith(prefix)) {
      results[key] = {};
      for (const [phase, data] of Object.entries(phases)) {
        results[key][phase] = { durationMs: data.durationMs };
      }
    }
  }
  return results;
}

/**
 * Gets metrics for a specific turn
 * @param {string} callId 
 * @param {string|number} turnId 
 * @returns {Object}
 */
function getTurnMetrics(callId, turnId) {
  const key = callId + ':' + turnId;
  const turnData = timers.get(key);
  if (!turnData) return {};
  const result = {};
  for (const [phase, data] of Object.entries(turnData)) {
    result[phase] = { durationMs: data.durationMs };
  }
  return result;
}

/**
 * Clear all metrics for a call
 * @param {string} callId
 */
function clearMetrics(callId) {
  const prefix = callId + ':';
  for (const key of timers.keys()) {
    if (key.startsWith(prefix)) {
      timers.delete(key);
    }
  }
}

module.exports = {
  startTimer,
  endTimer,
  getMetrics,
  getTurnMetrics,
  clearMetrics
};
