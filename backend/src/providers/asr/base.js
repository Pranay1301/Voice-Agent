const EventEmitter = require('events');

/**
 * Base ASR provider interface
 */
class ASRProvider extends EventEmitter {
  constructor(config) { 
    super(); 
    this.config = config; 
  }
  
  async connect(options) { 
    throw new Error('Not implemented'); 
  } // options: { encoding, sampleRate, language }
  
  send(audioBuffer) { 
    throw new Error('Not implemented'); 
  }
  
  async disconnect() { 
    throw new Error('Not implemented'); 
  }
  // Events emitted: 'transcript_partial', 'transcript_final', 'speech_started', 'speech_ended', 'utterance_end', 'error'
}

module.exports = ASRProvider;
