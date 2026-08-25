const EventEmitter = require('events');

/**
 * Base TTS provider interface
 */
class TTSProvider extends EventEmitter {
  constructor(config) { 
    super(); 
    this.config = config; 
  }
  
  async connect() { 
    throw new Error('Not implemented'); 
  }
  
  async synthesize(text) { 
    throw new Error('Not implemented'); 
  }
  
  // For streaming: send text chunks, receive audio chunks
  async streamStart() { 
    throw new Error('Not implemented'); 
  }
  
  sendText(textChunk) { 
    throw new Error('Not implemented'); 
  }
  
  async streamEnd() { 
    throw new Error('Not implemented'); 
  }
  
  async disconnect() { 
    throw new Error('Not implemented'); 
  }
  
  abort() { 
    throw new Error('Not implemented'); 
  } // For barge-in
  
  // Events: 'audio', 'done', 'error'
}

module.exports = TTSProvider;
