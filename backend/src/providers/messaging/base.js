/**
 * Base messaging provider
 */
class MessagingProvider {
  constructor(config) { 
    this.config = config; 
  }
  
  async sendMessage({ to, body, mediaUrl }) { 
    throw new Error('Not implemented'); 
  }
  
  async getStatus(messageId) { 
    throw new Error('Not implemented'); 
  }
}

module.exports = MessagingProvider;
