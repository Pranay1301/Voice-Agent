const WebSocket = require('ws');
const TTSProvider = require('./base');
const { createLogger } = require('../../utils/logger');
const logger = createLogger('elevenlabs-tts');

class ElevenLabsTTS extends TTSProvider {
  constructor({ apiKey, voiceId, model = 'eleven_flash_v2_5' }) {
    super({ apiKey, voiceId, model });
    this.apiKey = apiKey;
    this.voiceId = voiceId;
    this.model = model;
    this.ws = null;
  }

  async connect() {
    return this.streamStart();
  }

  async streamStart() {
    return new Promise((resolve, reject) => {
      try {
        const url = `wss://api.elevenlabs.io/v1/text-to-speech/${this.voiceId}/stream-input?model_id=${this.model}`;
        this.ws = new WebSocket(url);

        this.ws.on('open', () => {
          logger.info('ElevenLabs WebSocket connected');
          // Send initial configuration message
          this.ws.send(JSON.stringify({
            text: ' ',
            voice_settings: { stability: 0.5, similarity_boost: 0.75, style: 0.3 },
            generation_config: { chunk_length_schedule: [120, 160, 250, 290] },
            xi_api_key: this.apiKey,
            output_format: 'pcm_16000'
          }));
          resolve();
        });

        this.ws.on('message', (data) => {
          try {
            const msg = JSON.parse(data);
            if (msg.audio) {
              this.emit('audio', Buffer.from(msg.audio, 'base64'));
            }
            if (msg.isFinal) {
              this.emit('done');
            }
          } catch (err) {
            logger.error('Error parsing ElevenLabs message', err);
          }
        });

        this.ws.on('error', (err) => {
          logger.error('ElevenLabs WebSocket error', err);
          this.emit('error', err);
          reject(err);
        });

        this.ws.on('close', () => {
          logger.info('ElevenLabs WebSocket closed');
        });
      } catch (err) {
        logger.error('ElevenLabs connection error', err);
        reject(err);
      }
    });
  }

  sendText(textChunk) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ text: textChunk }));
    }
  }

  async streamEnd() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ text: '' }));
    }
  }

  abort() {
    logger.info('Aborting current ElevenLabs stream (barge-in)');
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    // Reopen for the next generation
    this.streamStart().catch(err => logger.error('Error reopening ElevenLabs stream after abort', err));
  }

  async disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

module.exports = ElevenLabsTTS;
