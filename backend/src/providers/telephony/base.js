const EventEmitter = require('events');

/**
 * Base telephony provider
 */
class TelephonyProvider extends EventEmitter {
  constructor(config) { 
    super(); 
    this.config = config; 
  }
  
  async createOutboundCall({ to, from, webhookUrl, statusCallbackUrl }) { 
    throw new Error('Not implemented'); 
  }
  
  async endCall(callSid) { 
    throw new Error('Not implemented'); 
  }
  
  generateConnectTwiml(streamUrl) { 
    throw new Error('Not implemented'); 
  }
  // Events: 'call_started', 'call_ended', 'call_failed'
}

module.exports = TelephonyProvider;
