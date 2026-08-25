const fs = require('fs');
const path = require('path');

class KnowledgeBase {
  constructor() {
    this.data = null;
    this.loadData();
  }

  loadData() {
    try {
      const filePath = path.join(__dirname, '../../knowledge/realEstate.json');
      const fileContent = fs.readFileSync(filePath, 'utf8');
      this.data = JSON.parse(fileContent);
    } catch (err) {
      console.error('Failed to load knowledge base', err);
      this.data = {};
    }
  }

  getRelevantKnowledge(query, context = {}) {
    if (!this.data) return '';
    
    const q = query ? query.toLowerCase() : '';
    let relevantSections = [];

    if (q.includes('property') || q.includes('bhk') || q.includes('villa') || q.includes('plot')) {
      relevantSections.push('Property Types: ' + JSON.stringify(this.data.property_types));
    }
    
    if (q.includes('price') || q.includes('cost') || q.includes('budget') || q.includes('how much')) {
      relevantSections.push('Property Types (Prices): ' + JSON.stringify(this.data.property_types));
      relevantSections.push('Locations (Starting Prices): ' + JSON.stringify(this.data.locations));
    }

    if (q.includes('location') || q.includes('where') || q.includes('city') || q.includes('area')) {
      relevantSections.push('Locations: ' + JSON.stringify(this.data.locations));
    }

    if (q.includes('amenit') || q.includes('facilit') || q.includes('gym') || q.includes('pool')) {
      relevantSections.push('Amenities: ' + JSON.stringify(this.data.amenities));
    }

    if (q.includes('company') || q.includes('elevatebox') || q.includes('who are you')) {
      relevantSections.push('Company Info: ' + JSON.stringify(this.data.company));
    }

    // Checking FAQs
    if (this.data.faqs) {
      for (const faq of this.data.faqs) {
        if (q.includes(faq.q.toLowerCase().split(' ')[0])) {
          relevantSections.push(`FAQ: Q: ${faq.q} A: ${faq.a}`);
        }
      }
    }

    // Default if nothing matched
    if (relevantSections.length === 0) {
      relevantSections.push('Company Info: ' + JSON.stringify(this.data.company));
      relevantSections.push('Locations: ' + JSON.stringify(this.data.locations.map(l => l.city).join(', ')));
    }

    return relevantSections.join('\n');
  }

  getAllKnowledge() {
    return JSON.stringify(this.data, null, 2);
  }

  hasAnswer(question) {
    const knowledge = this.getRelevantKnowledge(question);
    return knowledge.length > 0;
  }
}

module.exports = new KnowledgeBase();
