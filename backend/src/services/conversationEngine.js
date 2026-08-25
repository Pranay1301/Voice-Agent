const ConversationState = require('./conversationState');
const decisionEngine = require('./decisionEngine');
const knowledgeBase = require('./knowledgeBase');
const { buildSystemPrompt } = require('../prompts/systemPrompt');
const { buildKnowledgeContext } = require('../prompts/knowledgeContext');
const { buildActionPolicy } = require('../prompts/actionPolicy');
const { parseCallbackTime } = require('./timeParser');
const database = require('../config/database');
const config = require('../config/env');
const { startTimer, endTimer } = require('../utils/latencyTracker');
const { createLogger } = require('../utils/logger');
const logger = createLogger('conversationEngine');

class ConversationEngine {
  constructor({ callId, callSid, phone, asrProvider, ttsProvider, llmProvider, actionEngine, dashboardBroadcast } = {}) {
    this.callId = callId || 'call_' + Date.now();
    this.callSid = callSid || this.callId;
    this.phone = phone || null;
    this.asrProvider = asrProvider;
    this.ttsProvider = ttsProvider;
    this.llmProvider = llmProvider;
    this.actionEngine = actionEngine;
    this.dashboardBroadcast = dashboardBroadcast || (() => {});
    
    this.state = new ConversationState();
    if (this.phone) {
      this.state.updateField('phone', this.phone, 1.0, 'telephony_metadata');
    }

    this.turnCounter = 0;
    this.onAgentResponse = null; // Callback: function(textChunk, isFinal)
  }

  async processUserInput(transcriptText, metadata = {}) {
    if (!transcriptText || transcriptText.trim().length === 0) return;
    
    this.turnCounter++;
    const turnId = this.turnCounter;
    
    startTimer(this.callId, turnId, 'total');
    startTimer(this.callId, turnId, 'llm');
    
    logger.info(`User [Turn ${turnId}]: "${transcriptText}"`, { callId: this.callId, metadata });

    // 1. Detect language & update turn history
    const detectedLang = metadata.language || (/[अ-ह]/.test(transcriptText) ? 'hi' : 'en');
    this.state.addTurn('user', transcriptText, { language: detectedLang, confidence: metadata.confidence || 0.9 });
    
    // Broadcast user transcript immediately to dashboard
    this.dashboardBroadcast('transcript', {
      speaker: 'User',
      text: transcriptText,
      language: detectedLang,
      confidence: metadata.confidence || 0.9,
      timestamp: new Date().toISOString()
    });

    // 2. Build modular prompt
    const relevantKnowledge = knowledgeBase.getRelevantKnowledge(transcriptText);
    const knowledgeContext = buildKnowledgeContext ? buildKnowledgeContext(relevantKnowledge) : relevantKnowledge;
    const actionPolicy = buildActionPolicy ? buildActionPolicy(config, this.state.getStructuredState()) : 'Trigger actions only on clear intent.';
    const systemPromptText = buildSystemPrompt(knowledgeContext, this.state, actionPolicy);

    const messages = [
      { role: 'system', content: systemPromptText },
      ...this.state.turns.slice(-10).map(t => ({ role: t.role, content: t.content }))
    ];

    const tools = this.getTools();
    let accumulatedText = '';
    let accumulatedToolCalls = [];

    try {
      if (this.llmProvider && typeof this.llmProvider.generateStream === 'function') {
        const stream = this.llmProvider.generateStream({
          messages,
          tools,
          maxTokens: config.MAX_LLM_TOKENS_PER_TURN || 300,
          temperature: 0.4
        });

        let firstChunk = true;
        for await (const chunk of stream) {
          if (chunk.type === 'text_delta') {
            accumulatedText += chunk.content;
            if (firstChunk) {
              endTimer(this.callId, turnId, 'llm');
              firstChunk = false;
            }
            if (this.onAgentResponse) {
              this.onAgentResponse(chunk.content, false);
            }
          } else if (chunk.type === 'tool_call') {
            accumulatedToolCalls.push(chunk.toolCall);
          }
        }
      } else {
        // Fallback default response
        accumulatedText = "Ji, bilkul. Main aapki requirement note kar leti hoon. Aapka budget aur preferred location kya rahegi?";
        if (this.onAgentResponse) {
          this.onAgentResponse(accumulatedText, false);
        }
      }

      if (this.onAgentResponse) {
        this.onAgentResponse('', true); // Signal end of response stream
      }

    } catch (err) {
      logger.error('Error during LLM streaming response', err);
      accumulatedText = "Ek second, let me verify that for you.";
      if (this.onAgentResponse) {
        this.onAgentResponse(accumulatedText, true);
      }
    }

    // 3. Record Agent response in state
    if (accumulatedText.trim().length > 0) {
      this.state.addTurn('assistant', accumulatedText);
      this.dashboardBroadcast('transcript', {
        speaker: 'Agent',
        text: accumulatedText,
        language: detectedLang,
        timestamp: new Date().toISOString()
      });
    }

    // 4. Process tool calls
    for (const tool of accumulatedToolCalls) {
      await this.handleToolCall(tool);
    }

    // 5. Evaluate classification
    const classification = decisionEngine.classify(this.state);
    this.state.lead_temperature = classification.temperature;

    // 6. Update database & dashboard
    try {
      database.saveConversationState(this.callId, this.state.getStructuredState(), classification.temperature, classification.score);
    } catch (dbErr) {
      logger.error('Failed to persist conversation state', dbErr);
    }

    this.dashboardBroadcast('lead_update', {
      callId: this.callId,
      lead: this.state.getStructuredState(),
      temperature: classification.temperature,
      intentScore: classification.score,
      reasoning: classification.reasoning
    });

    const totalDuration = endTimer(this.callId, turnId, 'total');
    logger.info(`Turn ${turnId} complete. Total latency: ${totalDuration}ms. Lead Temp: ${classification.temperature}`);
  }

  async handleToolCall(toolCall) {
    if (!toolCall || !toolCall.name) return;
    logger.info(`Executing LLM tool: ${toolCall.name}`, toolCall.arguments);
    
    let args = {};
    try {
      args = typeof toolCall.arguments === 'string' ? JSON.parse(toolCall.arguments) : toolCall.arguments;
    } catch (e) {
      logger.error('Failed to parse tool arguments', e);
      return;
    }

    switch (toolCall.name) {
      case 'update_lead_info':
        for (const [key, val] of Object.entries(args)) {
          if (val !== undefined && val !== null) {
            this.state.updateField(key, val, 0.9, 'llm_extraction');
          }
        }
        break;

      case 'classify_lead':
        if (args.buying_intent) {
          this.state.buying_intent = args.buying_intent;
        }
        if (Array.isArray(args.objections)) {
          args.objections.forEach(obj => this.state.addObjection(obj));
        }
        break;

      case 'schedule_callback':
        if (args.requested_time) {
          const parsed = parseCallbackTime(args.requested_time);
          this.state.callback_requested = true;
          this.state.preferred_callback_time = parsed.time || parsed.date || args.requested_time;
          
          if (this.actionEngine) {
            await this.actionEngine.enqueueAction({
              callId: this.callId,
              type: 'callback',
              payload: {
                time: this.state.preferred_callback_time,
                reason: args.reason || 'User requested callback'
              }
            });
          }
        }
        break;

      case 'book_meeting':
        this.state.meeting_interest = true;
        if (this.actionEngine) {
          await this.actionEngine.enqueueAction({
            callId: this.callId,
            type: 'meeting',
            payload: {
              date: args.preferred_date,
              time: args.preferred_time,
              meeting_type: args.meeting_type || 'site_visit'
            }
          });
        }
        break;

      case 'trigger_whatsapp':
        if (this.actionEngine && this.phone) {
          await this.actionEngine.enqueueAction({
            callId: this.callId,
            type: 'whatsapp',
            payload: {
              to: this.phone,
              message: args.message_context || 'Sharing property information as discussed.'
            }
          });
        }
        break;
    }
  }

  getTools() {
    return [
      {
        type: 'function',
        function: {
          name: 'update_lead_info',
          description: 'Update structured lead parameters (name, email, budget, location, property_type, timeline, requirements, purpose, decision_maker)',
          parameters: {
            type: 'object',
            properties: {
              name: { type: 'string' },
              email: { type: 'string' },
              budget: { type: 'string' },
              budget_numeric: { type: 'number', description: 'Budget in INR numeric' },
              location: { type: 'string' },
              property_type: { type: 'string' },
              timeline: { type: 'string' },
              requirements: { type: 'string' },
              purpose: { type: 'string', enum: ['self_use', 'investment', 'rental', 'unknown'] },
              decision_maker: { type: 'string' }
            }
          }
        }
      },
      {
        type: 'function',
        function: {
          name: 'classify_lead',
          description: 'Record intent signals, objections, and buying intent from user conversation',
          parameters: {
            type: 'object',
            properties: {
              signals: { type: 'array', items: { type: 'string' } },
              objections: { type: 'array', items: { type: 'string' } },
              buying_intent: { type: 'string', enum: ['high', 'medium', 'low', 'none'] }
            },
            required: ['signals', 'buying_intent']
          }
        }
      },
      {
        type: 'function',
        function: {
          name: 'schedule_callback',
          description: 'Record callback time requested in natural language (e.g. kal morning, tomorrow 4pm)',
          parameters: {
            type: 'object',
            properties: {
              requested_time: { type: 'string', description: 'Natural language time phrase' },
              reason: { type: 'string' }
            },
            required: ['requested_time']
          }
        }
      },
      {
        type: 'function',
        function: {
          name: 'book_meeting',
          description: 'Book site visit or consultation when prospect agrees',
          parameters: {
            type: 'object',
            properties: {
              preferred_date: { type: 'string' },
              preferred_time: { type: 'string' },
              meeting_type: { type: 'string', enum: ['site_visit', 'video_call', 'office_visit', 'phone_call'] }
            },
            required: ['preferred_date']
          }
        }
      },
      {
        type: 'function',
        function: {
          name: 'trigger_whatsapp',
          description: 'Trigger asynchronous WhatsApp message with properties when high buying intent is shown',
          parameters: {
            type: 'object',
            properties: {
              message_context: { type: 'string', description: 'Context summary for the message' }
            },
            required: ['message_context']
          }
        }
      }
    ];
  }

  cleanup() {
    logger.info(`Cleaning up ConversationEngine for call ${this.callId}`);
    try {
      database.saveConversationState(this.callId, this.state.getStructuredState(), this.state.lead_temperature, 0);
    } catch (e) {
      logger.error('Error saving state on cleanup', e);
    }
  }
}

module.exports = ConversationEngine;
