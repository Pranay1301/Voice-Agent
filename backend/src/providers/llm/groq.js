const LLMProvider = require('./base');
const Groq = require('groq-sdk');
const { createLogger } = require('../../utils/logger');
const logger = createLogger('groq-llm');

const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms));

class GroqLLM extends LLMProvider {
  constructor({ apiKey, model, fallbackModel, maxRetries = 3 }) {
    super({ apiKey, model, fallbackModel, maxRetries });
    this.groq = new Groq({ apiKey });
    this.model = model;
    this.fallbackModel = fallbackModel;
    this.maxRetries = maxRetries;
  }

  async *generateStream({ messages, tools, maxTokens, temperature }) {
    let attempt = 0;
    let currentModel = this.model;
    const backoffs = [1000, 2000, 4000];
    
    while (attempt <= this.maxRetries) {
      try {
        const startTime = Date.now();
        let firstToken = true;
        
        const stream = await this.groq.chat.completions.create({
          messages,
          model: currentModel,
          tools,
          max_tokens: maxTokens,
          temperature,
          stream: true
        });
        
        for await (const chunk of stream) {
          if (firstToken) {
            logger.info(`Latency to first token: ${Date.now() - startTime}ms`);
            firstToken = false;
          }
          
          const delta = chunk.choices[0]?.delta;
          if (!delta) continue;
          
          if (delta.content) {
            yield { type: 'text_delta', content: delta.content };
          }
          
          if (delta.tool_calls) {
            for (const toolCall of delta.tool_calls) {
              yield { 
                type: 'tool_call', 
                toolCall: { 
                  name: toolCall.function?.name, 
                  arguments: toolCall.function?.arguments 
                }
              };
            }
          }
        }
        
        yield { type: 'done', usage: { promptTokens: 0, completionTokens: 0 } };
        return; // Success, exit retry loop
      } catch (err) {
        if (err.status === 429) {
          logger.warn(`Groq 429 error (attempt ${attempt + 1}/${this.maxRetries + 1})`);
          if (attempt < this.maxRetries) {
            await wait(backoffs[attempt] || 4000);
            if (attempt === this.maxRetries - 1 && this.fallbackModel) {
              logger.warn(`Switching to fallback model: ${this.fallbackModel}`);
              currentModel = this.fallbackModel;
            }
            attempt++;
            continue;
          }
        }
        logger.error('Groq streaming error', err);
        throw err;
      }
    }
  }

  async generate({ messages, tools, maxTokens, temperature }) {
    let attempt = 0;
    let currentModel = this.model;
    const backoffs = [1000, 2000, 4000];

    while (attempt <= this.maxRetries) {
      try {
        const startTime = Date.now();
        const response = await this.groq.chat.completions.create({
          messages,
          model: currentModel,
          tools,
          max_tokens: maxTokens,
          temperature,
          stream: false
        });
        
        logger.info(`Request latency: ${Date.now() - startTime}ms`);
        
        const choice = response.choices[0];
        const toolCalls = (choice.message.tool_calls || []).map(tc => ({
          name: tc.function.name,
          arguments: tc.function.arguments
        }));

        return {
          content: choice.message.content,
          toolCalls,
          usage: response.usage
        };
      } catch (err) {
        if (err.status === 429) {
          if (attempt < this.maxRetries) {
            await wait(backoffs[attempt] || 4000);
            if (attempt === this.maxRetries - 1 && this.fallbackModel) {
              currentModel = this.fallbackModel;
            }
            attempt++;
            continue;
          }
        }
        logger.error('Groq generate error', err);
        throw err;
      }
    }
  }
}

module.exports = GroqLLM;
