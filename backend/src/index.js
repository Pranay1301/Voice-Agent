require('dotenv').config();
const envConfig = require('./config/env');
const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const cors = require('cors');
const database = require('./config/database');

const callRoutes = require('./routes/calls');
const leadRoutes = require('./routes/leads');
const webhookRoutes = require('./routes/webhooks');
const dashboardRoutes = require('./routes/dashboard');

const { handleTwilioStream } = require('./websocket/twilioStream');
const { handleDashboardConnection } = require('./websocket/dashboardStream');

const app = express();

app.use(cors({ origin: envConfig.FRONTEND_URL }));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.use('/api/calls', callRoutes);
app.use('/api/leads', leadRoutes);
app.use('/api/twilio', webhookRoutes);
app.use('/api/dashboard', dashboardRoutes);

if (envConfig.TEST_MODE) {
  const testRoutes = require('./routes/test');
  app.use('/api/test', testRoutes);
}

const server = http.createServer(app);

const wss = new WebSocket.Server({ noServer: true });

server.on('upgrade', (request, socket, head) => {
  const pathname = request.url;
  
  if (pathname === '/media-stream') {
    wss.handleUpgrade(request, socket, head, (ws) => {
      handleTwilioStream(ws, request);
    });
  } else if (pathname === '/dashboard-ws') {
    wss.handleUpgrade(request, socket, head, (ws) => {
      handleDashboardConnection(ws);
    });
  } else {
    socket.destroy();
  }
});

server.listen(envConfig.PORT || 3000, () => {
  console.log('🎙️ AI Voice Sales Agent Backend');
  console.log(`Port: ${envConfig.PORT || 3000}`);
  console.log(`Test Mode: ${envConfig.TEST_MODE}`);
  console.log(`Outbound Calls Allowed: ${envConfig.ALLOW_OUTBOUND_CALLS}`);
  console.log(`Manual Trigger Required: ${envConfig.REQUIRE_MANUAL_CALL_TRIGGER}`);
  console.log('⚠️ NO AUTOMATIC CALLS WILL BE PLACED');
  console.log('Provider Status: ASR/LLM/TTS are subject to configuration in env.');
});
