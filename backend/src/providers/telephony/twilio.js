const twilio = require('twilio');
const TelephonyProvider = require('./base');
const { createLogger } = require('../../utils/logger');
const logger = createLogger('twilio-telephony');

class TwilioTelephony extends TelephonyProvider {
  constructor({ accountSid, authToken, phoneNumber }) {
    super({ accountSid, authToken, phoneNumber });
    this.client = twilio(accountSid, authToken);
    this.phoneNumber = phoneNumber;
  }

  async createOutboundCall({ to, from, webhookUrl, statusCallbackUrl }) {
    try {
      if (!to) {
        throw new Error("Missing 'to' number");
      }
      const call = await this.client.calls.create({
        to,
        from: from || this.phoneNumber,
        url: webhookUrl,
        statusCallback: statusCallbackUrl,
        statusCallbackEvent: ['initiated', 'ringing', 'answered', 'completed']
      });
      logger.info(`Initiated outbound call to ${to}, SID: ${call.sid}`);
      return { callSid: call.sid, status: call.status };
    } catch (err) {
      logger.error('Error creating outbound call', err);
      throw err;
    }
  }

  async endCall(callSid) {
    try {
      const call = await this.client.calls(callSid).update({ status: 'completed' });
      logger.info(`Ended call SID: ${callSid}`);
      return call;
    } catch (err) {
      logger.error(`Error ending call SID: ${callSid}`, err);
      throw err;
    }
  }

  generateConnectTwiml(streamUrl) {
    const VoiceResponse = twilio.twiml.VoiceResponse;
    const response = new VoiceResponse();
    const connect = response.connect();
    connect.stream({ url: streamUrl });
    return response.toString();
  }
}

module.exports = TwilioTelephony;
