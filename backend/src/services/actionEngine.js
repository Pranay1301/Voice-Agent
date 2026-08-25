const crypto = require('crypto');
const database = require('../config/database');
const { generateKey, checkAndCreate } = require('../utils/idempotency');
const { createLogger } = require('../utils/logger');
const logger = createLogger('actionEngine');

class ActionEngine {
  constructor({ messagingProvider, emailProvider } = {}) {
    this.messagingProvider = messagingProvider;
    this.emailProvider = emailProvider;
    this.MAX_ACTION_RETRIES = 3;
  }

  async enqueueAction({ callId, type, payload }) {
    const idempotencyKey = generateKey(callId, type, 'v1');
    
    // Check idempotency in database
    const existing = database.getAction(idempotencyKey);
    if (existing) {
      logger.warn('Duplicate action suppressed by idempotency key', { idempotencyKey, callId, type });
      return { actionId: existing.id, status: existing.status, duplicated: true };
    }

    const actionId = 'action_' + crypto.randomUUID();
    const action = {
      id: actionId,
      call_id: callId,
      type,
      payload,
      idempotency_key: idempotencyKey,
      status: 'pending'
    };

    try {
      database.insertAction(action);
    } catch (err) {
      if (err.code === 'SQLITE_CONSTRAINT_UNIQUE') {
        logger.warn('Suppressed race-condition duplicate action', { idempotencyKey });
        return { actionId, status: 'duplicate_suppressed' };
      }
      logger.error('Failed to insert action into DB', err);
    }

    // Execute asynchronously - NEVER block the voice loop
    setImmediate(() => {
      this.processAction(action).catch(err => logger.error('Error processing background action', err));
    });

    return { actionId, status: 'enqueued' };
  }

  async processAction(action) {
    logger.info(`Processing async action: ${action.type}`, { actionId: action.id, callId: action.call_id });
    const payload = typeof action.payload === 'string' ? JSON.parse(action.payload) : action.payload;

    try {
      if (action.type === 'whatsapp') {
        if (this.messagingProvider && typeof this.messagingProvider.sendMessage === 'function') {
          const result = await this.messagingProvider.sendMessage({
            to: payload.to,
            body: payload.message || payload.body
          });
          database.updateAction(action.id, { status: result.status || 'sent', executed_at: new Date().toISOString() });
        } else {
          logger.warn('WhatsApp messaging provider not configured');
          database.updateAction(action.id, { status: 'NOT_CONFIGURED', executed_at: new Date().toISOString() });
        }
      } else if (action.type === 'email') {
        if (this.emailProvider && typeof this.emailProvider.sendEmail === 'function') {
          const result = await this.emailProvider.sendEmail({
            to: payload.to,
            subject: payload.subject,
            html: payload.body || payload.html
          });
          database.updateAction(action.id, { status: result.status || 'sent', executed_at: new Date().toISOString() });
        } else {
          logger.warn('Email provider not configured');
          database.updateAction(action.id, { status: 'NOT_CONFIGURED', executed_at: new Date().toISOString() });
        }
      } else if (action.type === 'callback') {
        database.insertFollowup({
          id: 'followup_' + crypto.randomUUID(),
          lead_id: payload.leadId || null,
          channel: 'phone',
          content: JSON.stringify({ callback_time: payload.time, reason: payload.reason }),
          scheduled_at: payload.time || new Date().toISOString(),
          status: 'scheduled'
        });
        database.updateAction(action.id, { status: 'scheduled', executed_at: new Date().toISOString() });
      } else if (action.type === 'meeting') {
        database.insertFollowup({
          id: 'followup_' + crypto.randomUUID(),
          lead_id: payload.leadId || null,
          channel: 'calendar',
          content: JSON.stringify({ meeting_date: payload.date, meeting_time: payload.time, type: payload.meeting_type }),
          scheduled_at: payload.date || new Date().toISOString(),
          status: 'booked'
        });
        database.updateAction(action.id, { status: 'booked', executed_at: new Date().toISOString() });
      }
    } catch (error) {
      logger.error(`Action ${action.id} failed:`, error);
      database.updateAction(action.id, {
        status: 'failed',
        error: error.message,
        executed_at: new Date().toISOString()
      });
    }
  }

  async getCallActions(callId) {
    return database.getActionsByCallId(callId);
  }
}

module.exports = ActionEngine;
