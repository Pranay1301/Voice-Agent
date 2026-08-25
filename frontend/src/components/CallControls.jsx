import React, { useState, useEffect } from 'react';
import ConfirmationDialog from './ConfirmationDialog.jsx';
import { api } from '../services/api.js';

function CallControls({ wsData }) {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [showConfirm, setShowConfirm] = useState(false);
  const [error, setError] = useState(null);
  const [callId, setCallId] = useState(null);
  const [duration, setDuration] = useState(0);
  const [testInput, setTestInput] = useState('');

  const { callStatus, testMode } = wsData;

  useEffect(() => {
    let timer;
    if (callStatus === 'Connected') {
      timer = setInterval(() => setDuration((d) => d + 1), 1000);
    } else if (callStatus === 'Idle' || callStatus === 'Ended') {
      setDuration(0);
    }
    return () => clearInterval(timer);
  }, [callStatus]);

  const formatDuration = (seconds) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const handleStartCall = async () => {
    setError(null);
    const { data: tokenData, error: tokenError } = await api.getConfirmationToken();
    if (tokenError) {
      setError(tokenError);
      return;
    }
    
    const { data, error: callError } = await api.startCall(phoneNumber, tokenData?.token);
    if (callError) {
      setError(callError);
    } else {
      setCallId(data?.callId);
    }
    setShowConfirm(false);
  };

  const handleEndCall = async () => {
    if (callId) {
      await api.endCall(callId);
    }
  };

  const handleSendTest = async () => {
    if (!testInput) return;
    await api.sendTestMessage(testInput);
    setTestInput('');
  };

  const getStatusColor = () => {
    switch(callStatus) {
      case 'Idle': return '🔴';
      case 'Connecting': return '🟡';
      case 'Connected': return '🟢';
      case 'Ended': return '⚫';
      default: return '⚪';
    }
  };

  return (
    <div className="card call-controls">
      <h2>📞 Call Controls</h2>
      <div className="status-row">
        <span className="call-status">{getStatusColor()} {callStatus}</span>
        {callStatus === 'Connected' && <span className="timer">{formatDuration(duration)}</span>}
      </div>

      {error && <div className="error-message">{error}</div>}

      {testMode ? (
        <div className="test-mode-controls">
          <input
            type="text"
            value={testInput}
            onChange={(e) => setTestInput(e.target.value)}
            placeholder="Type a test message..."
            className="input-field"
            disabled={callStatus !== 'Connected'}
          />
          <button 
            className="btn btn-primary" 
            onClick={handleSendTest}
            disabled={!testInput || callStatus !== 'Connected'}
          >
            Send Test
          </button>
        </div>
      ) : (
        <div className="phone-controls">
          <input
            type="text"
            value={phoneNumber}
            onChange={(e) => setPhoneNumber(e.target.value)}
            placeholder="+91XXXXXXXXXX"
            className="input-field phone-input"
            disabled={callStatus !== 'Idle' && callStatus !== 'Ended'}
          />
          
          {(callStatus === 'Idle' || callStatus === 'Ended') ? (
            <button
              className="btn btn-success btn-lg"
              disabled={!phoneNumber}
              onClick={() => setShowConfirm(true)}
            >
              🟢 START OUTBOUND TEST CALL
            </button>
          ) : (
            <button
              className="btn btn-danger btn-lg"
              onClick={handleEndCall}
            >
              🔴 END CALL
            </button>
          )}
        </div>
      )}

      {showConfirm && (
        <ConfirmationDialog
          number={phoneNumber}
          onConfirm={handleStartCall}
          onCancel={() => setShowConfirm(false)}
        />
      )}
    </div>
  );
}

export default CallControls;
