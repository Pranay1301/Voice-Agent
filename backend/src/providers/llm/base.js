/**
 * Base LLM provider interface
 */
class LLMProvider {
  constructor(config) { 
    this.config = config; 
  }
  
  async *generateStream({ messages, tools, maxTokens, temperature }) { 
    throw new Error('Not implemented'); 
  }
  // Returns an async iterator/stream yielding { type: 'text'|'tool_call', content, toolCall }
  
  async generate({ messages, tools, maxTokens, temperature }) { 
    throw new Error('Not implemented'); 
  }
  // Returns { content, toolCalls, usage }
}

module.exports = LLMProvider;
