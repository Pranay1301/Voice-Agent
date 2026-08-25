import React, { useState } from 'react';

function DebugPanel({ wsData }) {
  const [expandedSection, setExpandedSection] = useState('state');
  
  const toggleSection = (section) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="debug-panel">
      <div className="debug-header">
        <h3>🔧 Debug Panel</h3>
      </div>
      
      <div className="debug-section">
        <div className="debug-section-header" onClick={() => toggleSection('state')}>
          <h4>Current Conversation State</h4>
          <span>{expandedSection === 'state' ? '▼' : '▶'}</span>
        </div>
        {expandedSection === 'state' && (
          <div className="debug-section-content">
            <button 
              className="btn btn-sm btn-secondary copy-btn"
              onClick={() => copyToClipboard(JSON.stringify(wsData.rawState, null, 2))}
            >
              Copy JSON
            </button>
            <pre>{JSON.stringify(wsData.rawState, null, 2)}</pre>
          </div>
        )}
      </div>

      <div className="debug-section">
        <div className="debug-section-header" onClick={() => toggleSection('metrics')}>
          <h4>Latency Metrics</h4>
          <span>{expandedSection === 'metrics' ? '▼' : '▶'}</span>
        </div>
        {expandedSection === 'metrics' && (
          <div className="debug-section-content">
            {wsData.metrics ? (
              <table className="metrics-table">
                <tbody>
                  <tr><td>ASR:</td><td>{wsData.metrics.asr || '-'} ms</td></tr>
                  <tr><td>LLM:</td><td>{wsData.metrics.llm || '-'} ms</td></tr>
                  <tr><td>TTS:</td><td>{wsData.metrics.tts || '-'} ms</td></tr>
                  <tr><td>Total Turn:</td><td>{wsData.metrics.total || '-'} ms</td></tr>
                </tbody>
              </table>
            ) : (
              <div>No metrics available</div>
            )}
            
            <div className="provider-info mt-2">
              <strong>Providers:</strong>
              <pre>{JSON.stringify(wsData.rawState?.providers || {}, null, 2)}</pre>
            </div>
          </div>
        )}
      </div>

      <div className="debug-section">
        <div className="debug-section-header" onClick={() => toggleSection('intent')}>
          <h4>Intent Score + Signals</h4>
          <span>{expandedSection === 'intent' ? '▼' : '▶'}</span>
        </div>
        {expandedSection === 'intent' && (
          <div className="debug-section-content">
             <pre>{JSON.stringify(wsData.rawState?.lead?.intentSignals || {}, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  );
}

export default DebugPanel;
