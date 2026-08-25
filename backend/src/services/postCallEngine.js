const crypto = require('crypto');
const decisionEngine = require('./decisionEngine');
const database = require('../config/database');
const config = require('../config/env');
const { createLogger } = require('../utils/logger');
const logger = createLogger('postCallEngine');

class PostCallEngine {
  constructor({ llmProvider, actionEngine } = {}) {
    this.llmProvider = llmProvider;
    this.actionEngine = actionEngine;
  }

  async process(callId, conversationState) {
    logger.info(`Starting post-call processing for call: ${callId}`);
    
    // 1. Finalize transcript
    const transcript = typeof conversationState.getTranscript === 'function' 
      ? conversationState.getTranscript() 
      : JSON.stringify(conversationState.turns || []);

    // 2. Generate summary
    const summary = await this.generateSummary(transcript, conversationState);

    // 3. Extract/finalize lead data
    const structuredState = typeof conversationState.getStructuredState === 'function' 
      ? conversationState.getStructuredState() 
      : conversationState;

    // 4. Run DecisionEngine
    const classification = decisionEngine.classify(conversationState);
    logger.info(`Final lead classification for ${callId}:`, classification);

    // 5. Update/create lead in DB
    const leadId = 'lead_' + (structuredState.phone ? crypto.createHash('md5').update(structuredState.phone).digest('hex').substring(0, 12) : crypto.randomUUID());
    
    try {
      database.insertLead({
        id: leadId,
        name: structuredState.name || 'Anonymous Prospect',
        phone: structuredState.phone || null,
        email: structuredState.email || null,
        language: structuredState.language || 'en',
        lead_temperature: classification.temperature,
        budget: structuredState.budget || null,
        budget_numeric: structuredState.budget_numeric || null,
        location: structuredState.location || null,
        requirements: structuredState.requirements || null,
        timeline: structuredState.timeline || null,
        decision_maker: structuredState.decision_maker !== undefined ? String(structuredState.decision_maker) : null,
        intent_score: classification.score,
        status: 'qualified'
      });
    } catch (err) {
      logger.error('Failed to upsert lead', err);
    }

    // 6. Update call record in DB
    try {
      database.updateCall(callId, {
        lead_id: leadId,
        summary,
        transcript,
        language: structuredState.language || 'en',
        status: 'completed',
        ended_at: new Date().toISOString()
      });
    } catch (err) {
      logger.error('Failed to update call in DB', err);
    }

    const actions = [];

    // 7. Meeting interest / qualified email
    if ((classification.temperature === 'HOT' || classification.temperature === 'WARM') && (structuredState.email || config.EMAIL_FROM)) {
      const emailHtml = await this.generateEmail(structuredState, summary);
      if (this.actionEngine && structuredState.email) {
        const emailAction = await this.actionEngine.enqueueAction({
          callId,
          type: 'email',
          payload: {
            to: structuredState.email,
            subject: `Your Property Search with ${config.COMPANY_NAME || 'ElevateBox Properties'}`,
            body: emailHtml,
            leadId
          }
        });
        actions.push(emailAction);
      }
    }

    // 8. WhatsApp message for HOT leads
    if (classification.temperature === 'HOT' && structuredState.phone && this.actionEngine) {
      const waText = await this.generateWhatsAppMessage(structuredState, summary);
      const waAction = await this.actionEngine.enqueueAction({
        callId,
        type: 'whatsapp',
        payload: {
          to: structuredState.phone,
          message: waText,
          leadId
        }
      });
      actions.push(waAction);
    }

    return {
      summary,
      leadTemperature: classification.temperature,
      classification,
      actions
    };
  }

  async generateSummary(transcript, state) {
    if (!this.llmProvider || typeof this.llmProvider.generate !== 'function') {
      return `Real estate sales call summary: Discussion covered property requirements, budget, and timeline. Lead qualified by decision engine.`;
    }
    
    try {
      const prompt = `Summarize the following real estate sales call transcript concisely. Focus on the prospect's needs, budget, timeline, and agreed next steps.\n\nTranscript:\n${transcript}`;
      const response = await this.llmProvider.generate({
        messages: [{ role: 'user', content: prompt }],
        maxTokens: 250,
        temperature: 0.2
      });
      return response.content || 'Discussion on property options and next steps.';
    } catch (err) {
      logger.error('Error generating LLM summary, using fallback', err);
      return 'Summary generation fallback: conversation completed.';
    }
  }

  async generateEmail(state, summary) {
    const MEETING_LINK = config.MEETING_LINK || 'https://calendly.com/elevatebox/meeting';
    const budget = state.budget || 'your discussed budget';
    const reqs = state.requirements || state.property_type || 'your preferred specifications';
    const location = state.location || 'your preferred location';
    const name = state.name || 'Valued Client';
    
    return `
      <!DOCTYPE html>
      <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
          <h2>Thank you for speaking with ${config.COMPANY_NAME || 'ElevateBox Properties'}</h2>
          <p>Hi ${name},</p>
          <p>It was a pleasure speaking with you today. As discussed during our call, you are looking for property in <strong>${location}</strong> around <strong>${budget}</strong> matching <strong>${reqs}</strong>.</p>
          <p>We have shortlisted prime projects matching your criteria and would love to schedule a dedicated site visit or brief consultation.</p>
          <p><strong>Next Step:</strong> You can book a convenient time slot directly using this link:</p>
          <p><a href="${MEETING_LINK}" style="background-color: #00b894; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Schedule Site Visit / Discussion</a></p>
          <br/>
          <p>Warm regards,<br/>
          <strong>${config.AGENT_NAME || 'Priya'}</strong><br/>
          ${config.COMPANY_NAME || 'ElevateBox Properties'}<br/>
          Email: sales@elevatebox.in
          </p>
        </body>
      </html>
    `;
  }

  async generateWhatsAppMessage(state, summary) {
    const budget = state.budget || 'your budget';
    const location = state.location || 'your preferred location';
    const name = state.name || 'there';
    const MEETING_LINK = config.MEETING_LINK || 'https://calendly.com/elevatebox/meeting';
    
    return `Hi ${name}! This is ${config.AGENT_NAME || 'Priya'} from ${config.COMPANY_NAME || 'ElevateBox Properties'}. As discussed, you're exploring options in ${location} within ${budget}. I've curated options matching your requirements. Feel free to book a site visit here: ${MEETING_LINK} or reply to this message!`;
  }
}

module.exports = PostCallEngine;
