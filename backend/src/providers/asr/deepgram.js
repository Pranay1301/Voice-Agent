const WebSocket = require('ws');
const ASRProvider = require('./base');
const { createLogger } = require('../../utils/logger');
const logger = createLogger('deepgram-asr');

class DeepgramASR extends ASRProvider {
  constructor({ apiKey }) {
    super({ apiKey });
    this.apiKey = apiKey;
    this.ws = null;
    this.retryCount = 0;
    this.maxRetries = 3;
    this.options = null;
  }

  async connect(options = {}) {
    this.options = options;
    return new Promise((resolve, reject) => {
      this._connectWs(resolve, reject);
    });
  }

  _connectWs(resolve, reject) {
    try {
      const qs = new URLSearchParams({
        model: 'nova-3',
        language: 'multi',
        interim_results: 'true',
        endpointing: '300',
        utterance_end_ms: '1200',
        smart_format: 'true',
        encoding: 'mulaw',
        sample_rate: '8000',
        channels: '1',
        punctuate: 'true'
      }).toString();

      const url = `wss://api.deepgram.com/v1/listen?${qs}`;
      
      this.ws = new WebSocket(url, {
        headers: {
          Authorization: `Token ${this.apiKey}`
        }
      });

      this.ws.on('open', () => {
        logger.info('Deepgram WebSocket connected');
        this.retryCount = 0;
        if (resolve) resolve();
      });

      this.ws.on('message', (data) => {
        try {
          const msg = JSON.parse(data);
          
          if (msg.type === 'Results') {
            const transcript = msg.channel?.alternatives?.[0]?.transcript || '';
            const confidence = msg.channel?.alternatives?.[0]?.confidence || 0;
            const words = msg.channel?.alternatives?.[0]?.words || [];
            const duration = msg.duration || 0;
            const language = msg.channel?.alternatives?.[0]?.languages?.[0] || 'en';

            if (msg.is_final) {
              if (transcript.trim().length > 0) {
                this.emit('transcript_final', { transcript, confidence, language, words, duration });
              }
            } else {
              if (transcript.trim().length > 0) {
                this.emit('transcript_partial', { transcript, confidence, language });
              }
            }
          } else if (msg.type === 'SpeechStarted') {
            this.emit('speech_started');
          } else if (msg.type === 'UtteranceEnd') {
            this.emit('utterance_end');
          }
        } catch (err) {
          logger.error('Error parsing Deepgram message', err);
        }
      });

      this.ws.on('error', (err) => {
        logger.error('Deepgram WebSocket error', err);
        this.emit('error', err);
      });

      this.ws.on('close', () => {
        logger.info('Deepgram WebSocket closed');
        if (this.retryCount < this.maxRetries) {
          this.retryCount++;
          logger.info(`Reconnecting Deepgram (Attempt ${this.retryCount}/${this.maxRetries})...`);
          setTimeout(() => this._connectWs(), 1000 * this.retryCount);
        }
      });
    } catch (error) {
      logger.error('Deepgram connection error', error);
      if (reject) reject(error);
    }
  }

  send(audioBuffer) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(audioBuffer);
    }
  }

  async disconnect() {
    this.maxRetries = 0; // Prevent reconnection
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

module.exports = DeepgramASR;
