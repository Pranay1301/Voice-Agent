import React, { useState } from 'react';
import CallControls from './CallControls.jsx';
import LiveTranscript from './LiveTranscript.jsx';
import LeadPanel from './LeadPanel.jsx';
import ActionStatus from './ActionStatus.jsx';
import CallSummary from './CallSummary.jsx';
import DebugPanel from './DebugPanel.jsx';
import { useWebSocket } from '../hooks/useWebSocket.js';

function Dashboard() {
  const wsData = useWebSocket();
  const [showDebug, setShowDebug] = useState(false);

  return (
    <div className="dashboard-layout">
      <header className="dashboard-header">
        <h1>🎙️ AI Voice Sales Agent</h1>
        <div className="header-badges">
          {wsData.testMode && <span className="badge badge-test">TEST MODE</span>}
          <span className={`status-indicator ${wsData.isConnected ? 'connected' : 'disconnected'}`}>
            {wsData.isConnected ? '● Connected' : '○ Disconnected'}
          </span>
          <button className="btn btn-secondary btn-sm ml-2" onClick={() => setShowDebug(!showDebug)}>
            🔧 Debug
          </button>
        </div>
      </header>

      <div className="dashboard-grid">
        <div className="left-column">
          <CallControls wsData={wsData} />
          <LiveTranscript transcript={wsData.transcript} callStatus={wsData.callStatus} />
        </div>
        <div className="right-column">
          <LeadPanel leadInfo={wsData.leadInfo} />
          <ActionStatus actionStatus={wsData.actionStatus} />
          {wsData.callStatus === 'Ended' && wsData.summary && (
            <CallSummary summary={wsData.summary} />
          )}
        </div>
      </div>

      {showDebug && <DebugPanel wsData={wsData} />}
    </div>
  );
}

export default Dashboard;
