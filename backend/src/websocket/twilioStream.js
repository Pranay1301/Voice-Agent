const { broadcast } = require('./dashboardStream');
const DeepgramASR = require('../providers/asr/deepgram');
const ElevenLabsTTS = require('../providers/tts/elevenlabs');
const GroqLLM = require('../providers/llm/groq');
const TwilioTelephony = require('../providers/telephony/twilio');
const WhatsAppProvider = require('../providers/messaging/whatsapp');
const SMTPEmailProvider = require('../providers/email/smtp');
const ConversationEngine = require('../services/conversationEngine');
const ActionEngine = require('../services/actionEngine');
const PostCallEngine = require('../services/postCallEngine');
const { pcm16kToMulaw8k } = require('../utils/audioUtils');
const config = require('../config/env');
const { createLogger } = require('../utils/logger');
const logger = createLogger('twilioStream');

const activeSessions = new Map();

// Shared providers
const llmProvider = config.GROQ_API_KEY ? new GroqLLM({
  apiKey: config.GROQ_API_KEY,
  model: config.GROQ_MODEL,
  fallbackModel: config.GROQ_FALLBACK_MODEL
}) : null;

const messagingProvider = config.WHATSAPP_ACCESS_TOKEN ? new WhatsAppProvider({
  accessToken: config.WHATSAPP_ACCESS_TOKEN,
  phoneNumberId: config.WHATSAPP_PHONE_NUMBER_ID
}) : null;

const emailProvider = config.EMAIL_USER ? new SMTPEmailProvider({
  host: config.EMAIL_HOST,
  port: config.EMAIL_PORT,
  user: config.EMAIL_USER,
  pass: config.EMAIL_PASS,
  from: config.EMAIL_FROM
}) : null;

const actionEngine = new ActionEngine({ messagingProvider, emailProvider });
const postCallEngine = new PostCallEngine({ llmProvider, actionEngine });

function handleTwilioStream(ws, req) {
  logger.info('New Twilio WebSocket media stream connection established');

  const sessionState = {
    streamSid: null,
    callSid: null,
    phoneNumber: null,
    asrProvider: null,
    ttsProvider: null,
    conversationEngine: null,
    isSpeaking: false,
    isClosing: false
  };

  ws.on('message', async (message) => {
    try {
      const msg = JSON.parse(message);

      switch (msg.event) {
        case 'connected':
          logger.info('Twilio media stream connected handshake');
          break;

        case 'start': {
          sessionState.streamSid = msg.start.streamSid;
          sessionState.callSid = msg.start.callSid;
          sessionState.phoneNumber = msg.start.customParameters?.phoneNumber || 'Unknown Caller';

          logger.info(`Call started: CallSid=${sessionState.callSid}, StreamSid=${sessionState.streamSid}`);
          activeSessions.set(sessionState.callSid, sessionState);

          broadcast('call_status', {
            status: 'connected',
            callSid: sessionState.callSid,
            streamSid: sessionState.streamSid,
            phoneNumber: sessionState.phoneNumber
          });

          // Initialize Deepgram ASR
          if (config.DEEPGRAM_API_KEY) {
            sessionState.asrProvider = new DeepgramASR({ apiKey: config.DEEPGRAM_API_KEY });
            await sessionState.asrProvider.connect({
              encoding: 'mulaw',
              sampleRate: 8000,
              language: 'multi'
            }).catch(err => logger.error('Deepgram connect error', err));
          }

          // Initialize ElevenLabs TTS
          if (config.ELEVENLABS_API_KEY && config.ELEVENLABS_VOICE_ID) {
            sessionState.ttsProvider = new ElevenLabsTTS({
              apiKey: config.ELEVENLABS_API_KEY,
              voiceId: config.ELEVENLABS_VOICE_ID,
              model: config.ELEVENLABS_MODEL
            });
            await sessionState.ttsProvider.connect().catch(err => logger.error('ElevenLabs connect error', err));
          }

          // Initialize Conversation Engine
          sessionState.conversationEngine = new ConversationEngine({
            callId: sessionState.callSid,
            callSid: sessionState.callSid,
            phone: sessionState.phoneNumber,
            asrProvider: sessionState.asrProvider,
            ttsProvider: sessionState.ttsProvider,
            llmProvider: llmProvider,
            actionEngine: actionEngine,
            dashboardBroadcast: broadcast
          });

          // Setup ASR Event Handlers
          if (sessionState.asrProvider) {
            sessionState.asrProvider.on('transcript_partial', (data) => {
              broadcast('transcript', {
                type: 'partial',
                text: data.transcript,
                confidence: data.confidence,
                speaker: 'User'
              });
            });

            sessionState.asrProvider.on('transcript_final', async (data) => {
              // BARGE-IN: If user speaks while agent is speaking, stop TTS immediately
              if (sessionState.isSpeaking && data.transcript.trim().length > 0) {
                logger.info('Barge-in detected: stopping agent playback');
                sessionState.isSpeaking = false;
                if (sessionState.ttsProvider) {
                  sessionState.ttsProvider.abort();
                }
                // Send clear buffer command to Twilio
                if (ws.readyState === ws.OPEN) {
                  ws.send(JSON.stringify({
                    event: 'clear',
                    streamSid: sessionState.streamSid
                  }));
                }
              }

              // Process user input through conversation engine
              await sessionState.conversationEngine.processUserInput(data.transcript, {
                language: data.language,
                confidence: data.confidence
              });
            });

            sessionState.asrProvider.on('error', (err) => {
              logger.error('ASR Provider error', err);
            });
          }

          // Setup TTS Event Handlers
          if (sessionState.ttsProvider) {
            sessionState.ttsProvider.on('audio', (pcmBuffer) => {
              try {
                // Convert 16kHz PCM from ElevenLabs to 8kHz μ-law for Twilio
                const mulawBuffer = pcm16kToMulaw8k(pcmBuffer);
                
                if (ws.readyState === ws.OPEN) {
                  ws.send(JSON.stringify({
                    event: 'media',
                    streamSid: sessionState.streamSid,
                    media: {
                      payload: mulawBuffer.toString('base64')
                    }
                  }));

                  ws.send(JSON.stringify({
                    event: 'mark',
                    streamSid: sessionState.streamSid,
                    mark: { name: 'chunk-' + Date.now() }
                  }));
                }
              } catch (audioErr) {
                logger.error('Audio conversion / send error', audioErr);
              }
            });

            sessionState.ttsProvider.on('done', () => {
              sessionState.isSpeaking = false;
            });

            sessionState.ttsProvider.on('error', (err) => {
              logger.error('TTS Provider error', err);
              sessionState.isSpeaking = false;
            });
          }

          // Connect LLM output stream to TTS input
          sessionState.conversationEngine.onAgentResponse = (textChunk, isFinal) => {
            sessionState.isSpeaking = true;
            if (sessionState.ttsProvider) {
              if (textChunk) {
                sessionState.ttsProvider.sendText(textChunk);
              }
              if (isFinal) {
                sessionState.ttsProvider.streamEnd();
              }
            }
          };

          break;
        }

        case 'media': {
          // Forward caller audio stream to Deepgram ASR
          if (sessionState.asrProvider && msg.media?.payload) {
            const audioBuffer = Buffer.from(msg.media.payload, 'base64');
            sessionState.asrProvider.send(audioBuffer);
          }
          break;
        }

        case 'mark': {
          // Confirmation that Twilio played the audio mark
          break;
        }

        case 'stop': {
          logger.info(`Twilio stream stopped for call: ${sessionState.callSid}`);
          cleanupSession(sessionState);
          break;
        }
      }
    } catch (err) {
      logger.error('Error handling Twilio stream message', err);
    }
  });

  ws.on('close', () => {
    logger.info(`WebSocket closed for call: ${sessionState.callSid}`);
    cleanupSession(sessionState);
  });

  ws.on('error', (err) => {
    logger.error('Twilio WebSocket error', err);
    cleanupSession(sessionState);
  });

  async function cleanupSession(session) {
    if (session.isClosing) return;
    session.isClosing = true;

    if (session.asrProvider) {
      session.asrProvider.disconnect().catch(() => {});
    }
    if (session.ttsProvider) {
      session.ttsProvider.disconnect().catch(() => {});
    }
    if (session.conversationEngine) {
      session.conversationEngine.cleanup();
      
      // Asynchronously trigger post-call analysis and followups
      if (session.callSid) {
        postCallEngine.process(session.callSid, session.conversationEngine.state)
          .then((result) => {
            broadcast('call_summary', {
              callSid: session.callSid,
              summary: result.summary,
              leadTemperature: result.leadTemperature,
              actions: result.actions
            });
          })
          .catch(err => logger.error('Error in post-call pipeline', err));
      }
    }

    if (session.callSid) {
      activeSessions.delete(session.callSid);
      broadcast('call_status', { status: 'ended', callSid: session.callSid });
    }
  }
}

module.exports = {
  handleTwilioStream,
  activeSessions,
  postCallEngine,
  actionEngine
};
