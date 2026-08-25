const knowledgeBase = require('../services/knowledgeBase');

function buildKnowledgeContext(kbData, conversationContext) {
  // If we had a specific question extracted from context, we could query:
  // return knowledgeBase.getRelevantKnowledge(conversationContext.lastUserTurn);
  
  // For now, return a concise representation of the full KB
  return knowledgeBase.getAllKnowledge();
}

module.exports = { buildKnowledgeContext };
