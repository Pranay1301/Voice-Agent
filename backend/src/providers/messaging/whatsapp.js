const MessagingProvider = require('./base');
const { createLogger } = require('../../utils/logger');
const logger = createLogger('whatsapp-messaging');

class WhatsAppMessaging extends MessagingProvider {
  constructor({ accessToken, phoneNumberId }) {
    super({ accessToken, phoneNumberId });
    this.accessToken = accessToken;
    this.phoneNumberId = phoneNumberId;
  }

  async sendMessage({ to, body, mediaUrl }) {
    if (!this.accessToken || !this.phoneNumberId) {
      logger.warn('WhatsApp credentials not configured');
      return { status: 'NOT_CONFIGURED' };
    }

    try {
      const url = `https://graph.facebook.com/v18.0/${this.phoneNumberId}/messages`;
      
      const payload = {
        messaging_product: 'whatsapp',
        to,
        type: 'text',
        text: { body }
      };

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.accessToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error?.message || 'Failed to send WhatsApp message');
      }

      logger.info(`Sent WhatsApp message to ${to}`);
      return {
        messageId: data.messages?.[0]?.id,
        status: 'sent'
      };
    } catch (err) {
      logger.error('WhatsApp send error', err);
      return { status: 'failed', error: err.message };
    }
  }

  async getStatus(messageId) {
    // Basic implementation since webhook handles real status updates
    return { status: 'unknown' };
  }
}

module.exports = WhatsAppMessaging;
