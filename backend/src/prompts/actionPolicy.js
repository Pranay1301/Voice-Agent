function buildActionPolicy(config, callState) {
  let policy = "Available Actions based on current state:\n";
  
  if (config.whatsappEnabled) {
    policy += "- trigger_whatsapp: ONLY if lead temperature is HOT and prospect agreed to receive messages.\n";
  } else {
    policy += "- trigger_whatsapp: UNAVAILABLE (Not configured).\n";
  }

  policy += "- book_meeting: When prospect expresses clear interest in a site visit or detailed discussion.\n";
  policy += "- schedule_callback: When prospect requests to be called back later.\n";

  return policy;
}

module.exports = { buildActionPolicy };
