const config = require('../config/env');

const SENSITIVE_FIELDS = ['apiKey', 'token', 'password', 'secret', 'authorization', 'TWILIO_AUTH_TOKEN'];

function redact(obj) {
  if (!obj || typeof obj !== 'object') return obj;
  if (Array.isArray(obj)) return obj.map(redact);
  
  const redacted = {};
  for (const [key, value] of Object.entries(obj)) {
    if (SENSITIVE_FIELDS.some(field => key.toLowerCase().includes(field.toLowerCase()))) {
      redacted[key] = '[REDACTED]';
    } else if (typeof value === 'object') {
      redacted[key] = redact(value);
    } else {
      redacted[key] = value;
    }
  }
  return redacted;
}

function createLogger(component) {
  const isProd = process.env.NODE_ENV === 'production';

  function logMessage(level, message, data = {}) {
    const logEntry = {
      timestamp: new Date().toISOString(),
      level,
      component,
      message,
      data: Object.keys(data).length ? redact(data) : undefined
    };

    if (isProd) {
      console[level === 'error' ? 'error' : 'log'](JSON.stringify(logEntry));
    } else {
      const dataStr = logEntry.data ? '\n' + JSON.stringify(logEntry.data, null, 2) : '';
      const prefix = '[' + logEntry.timestamp + '] [' + level.toUpperCase() + '] [' + component + '] ';
      console[level === 'error' ? 'error' : 'log'](prefix + message + dataStr);
    }
  }

  return {
    debug: (msg, data) => logMessage('debug', msg, data),
    info: (msg, data) => logMessage('info', msg, data),
    warn: (msg, data) => logMessage('warn', msg, data),
    error: (msg, data) => logMessage('error', msg, data)
  };
}

module.exports = {
  createLogger,
  log: createLogger('global')
};
