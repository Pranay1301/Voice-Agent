const connectedClients = new Set();

function handleDashboardConnection(ws) {
  connectedClients.add(ws);
  
  ws.on('close', () => {
    connectedClients.delete(ws);
  });
  
  ws.on('error', (error) => {
    console.error('Dashboard websocket error:', error);
    connectedClients.delete(ws);
  });
}

function broadcast(event, data) {
  const message = JSON.stringify({
    event,
    data,
    timestamp: new Date().toISOString()
  });
  
  for (const client of connectedClients) {
    if (client.readyState === 1) { // 1 = OPEN
      try {
        client.send(message);
      } catch (err) {
        console.error('Error broadcasting to client:', err);
      }
    }
  }
}

module.exports = {
  handleDashboardConnection,
  broadcast
};
