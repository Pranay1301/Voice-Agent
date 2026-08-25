const nodemailer = require('nodemailer');
const EmailProvider = require('./base');
const { createLogger } = require('../../utils/logger');
const logger = createLogger('smtp-email');

class SMTPEmail extends EmailProvider {
  constructor({ host, port, user, pass, from }) {
    super({ host, port, user, pass, from });
    this.from = from;
    
    if (host && port && user && pass) {
      this.transporter = nodemailer.createTransport({
        host,
        port,
        secure: port === 465, // true for 465, false for other ports
        auth: {
          user,
          pass
        }
      });
    } else {
      this.transporter = null;
    }
  }

  async sendEmail({ to, subject, html, text }) {
    if (!this.transporter) {
      logger.warn('SMTP credentials not configured');
      return { status: 'NOT_CONFIGURED' };
    }

    try {
      const info = await this.transporter.sendMail({
        from: this.from,
        to,
        subject,
        text,
        html
      });
      
      logger.info(`Sent email to ${to}, messageId: ${info.messageId}`);
      return { messageId: info.messageId, status: 'sent' };
    } catch (err) {
      logger.error('SMTP send error', err);
      return { status: 'failed', error: err.message };
    }
  }
}

module.exports = SMTPEmail;
