class DecisionEngine {
  /**
   * Evaluates the lead based on the ConversationState and returns a structured, explainable classification.
   * @param {Object} state - ConversationState instance
   * @returns {Object} { temperature, score, reasoning, signals }
   */
  classify(state) {
    let score = 0;
    const reasoning = [];
    const signals = [];

    // Check if we have enough turns for meaningful evaluation
    if (!state.turns || state.turns.length < 1) {
      return {
        temperature: 'UNKNOWN',
        score: 0,
        reasoning: ['Insufficient turns to evaluate conversation'],
        signals: []
      };
    }

    const s = typeof state.getStructuredState === 'function' ? state.getStructuredState() : state;
    const transcript = typeof state.getTranscript === 'function' ? state.getTranscript().toLowerCase() : '';

    // ==========================================
    // 1. POSITIVE / BUYING SIGNALS (+ score)
    // ==========================================

    // General interest expressed (e.g. interested in property, looking for 2bhk, etc.)
    if (transcript.includes('interested') || transcript.includes('looking for') || transcript.includes('want') || transcript.includes('need') || transcript.includes('chahiye') || s.property_interest) {
      score += 0.18;
      reasoning.push('General purchase interest expressed');
      signals.push('interest_expressed');
    }
    
    // Explicit budget shared
    if (s.budget || (state.budget && state.budget.value)) {
      score += 0.15;
      reasoning.push('Explicit budget range provided');
      signals.push('budget_mentioned');
    }

    // Defined timeline (e.g. this month, immediate, soon)
    if (s.timeline || (state.timeline && state.timeline.value)) {
      score += 0.15;
      reasoning.push('Clear purchase timeline defined');
      signals.push('timeline_defined');
    }

    // Meeting / Site visit interest
    if (s.meeting_interest || state.meeting_interest || transcript.includes('meet') || transcript.includes('site visit') || transcript.includes('appointment')) {
      score += 0.20;
      reasoning.push('Expressed interest in meeting / site visit');
      signals.push('requesting_meeting');
    }

    // Pricing / Quotation inquiries
    if (transcript.includes('price') || transcript.includes('cost') || transcript.includes('how much') || transcript.includes('rate') || transcript.includes('quote')) {
      score += 0.15;
      reasoning.push('Actively inquiring about pricing and costs');
      signals.push('asking_price');
    }

    // Availability / Start timeline inquiries
    if (transcript.includes('availability') || transcript.includes('available') || transcript.includes('how soon') || transcript.includes('possession')) {
      score += 0.12;
      reasoning.push('Inquiring about project availability and timelines');
      signals.push('asking_availability');
    }

    // Next steps / Process inquiries
    if (transcript.includes('next step') || transcript.includes('how to proceed') || transcript.includes('how can we start') || transcript.includes('process')) {
      score += 0.15;
      reasoning.push('Inquiring about booking process / next steps');
      signals.push('asking_next_steps');
    }

    // Specific property requirements (location, 2BHK, amenities, etc.)
    if (s.property_type || s.location || s.requirements || s.features) {
      score += 0.10;
      reasoning.push('Specific requirements identified (location/property type)');
      signals.push('specific_requirements');
    }

    // Decision maker present
    if (s.decision_maker === true || (state.decision_maker && state.decision_maker.value === true)) {
      score += 0.10;
      reasoning.push('Primary decision maker confirmed');
      signals.push('decision_maker_present');
    }

    // High conversation engagement
    if (state.turns && state.turns.length >= 4) {
      score += 0.10;
      reasoning.push('High conversation engagement across multiple turns');
      signals.push('engagement_high');
    }

    // ==========================================
    // 2. NEGATIVE / BARRIER SIGNALS (- score)
    // ==========================================

    // Just browsing / curiosity only
    if (transcript.includes('just looking') || transcript.includes('just checking') || transcript.includes('just browsing') || transcript.includes('curious')) {
      score -= 0.25;
      reasoning.push('Prospect is just browsing with no active need');
      signals.push('just_browsing');
    }

    // Decision maker absent / needs approval from partner/family
    if (s.decision_maker === false || transcript.includes('discuss with my wife') || transcript.includes('discuss with my husband') || transcript.includes('brother handles') || transcript.includes('partner handles')) {
      score -= 0.08;
      reasoning.push('Decision maker absent (needs third-party approval)');
      signals.push('decision_maker_absent');
    }

    // No budget or budget objection
    if (transcript.includes('no budget') || transcript.includes('budget is not much') || transcript.includes('budget issue') || transcript.includes('tight budget')) {
      score -= 0.10;
      reasoning.push('Budget constraints / financial barrier identified');
      signals.push('budget_barrier');
    }

    // Unresolved objections
    if (s.objections && Array.isArray(s.objections) && s.objections.length > 0) {
      const reduction = s.objections.length * 0.08;
      score -= reduction;
      reasoning.push(`Unresolved objections present (${s.objections.length})`);
      signals.push('objection_unresolved');
    }

    // Explicitly disengaged / not interested
    if (transcript.includes('not interested') || transcript.includes('stop calling') || transcript.includes('dont call') || transcript.includes("don't call")) {
      score -= 0.40;
      reasoning.push('Explicitly stated lack of interest');
      signals.push('explicitly_not_interested');
    }

    // ==========================================
    // 3. CLASSIFICATION THRESHOLDS
    // ==========================================
    let temperature = 'UNKNOWN';
    if (score >= 0.50) {
      temperature = 'HOT';
    } else if (score >= 0.18) {
      temperature = 'WARM';
    } else {
      temperature = 'COLD';
    }

    // Safety guard: if explicitly not interested, force COLD
    if (signals.includes('explicitly_not_interested')) {
      temperature = 'COLD';
    }

    return {
      temperature,
      score: Math.max(0, Math.min(1.0, parseFloat(score.toFixed(2)))),
      reasoning,
      signals
    };
  }
}

module.exports = new DecisionEngine();
