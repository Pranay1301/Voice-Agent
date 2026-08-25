// Dummy env config
module.exports = {
  FRONTEND_URL: process.env.FRONTEND_URL || '*',
  PORT: process.env.PORT || 3000,
  TEST_MODE: process.env.TEST_MODE === 'true',
  ALLOW_OUTBOUND_CALLS: process.env.ALLOW_OUTBOUND_CALLS === 'true',
  REQUIRE_MANUAL_CALL_TRIGGER: process.env.REQUIRE_MANUAL_CALL_TRIGGER !== 'false',
  TWILIO_WEBHOOK_BASE_URL: process.env.TWILIO_WEBHOOK_BASE_URL
};
