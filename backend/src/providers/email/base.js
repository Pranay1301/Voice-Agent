/**
 * Base email provider
 */
class EmailProvider {
  constructor(config) { 
    this.config = config; 
  }
  
  async sendEmail({ to, subject, html, text }) { 
    throw new Error('Not implemented'); 
  }
}

module.exports = EmailProvider;
