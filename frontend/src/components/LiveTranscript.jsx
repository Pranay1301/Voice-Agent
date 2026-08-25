import React, { useEffect, useRef } from 'react';

function LiveTranscript({ transcript, callStatus }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [transcript]);

  return (
    <div className="card live-transcript">
      <h2>💬 Live Transcript</h2>
      <div className="transcript-container" ref={containerRef}>
        {transcript.length === 0 ? (
          <div className="empty-state">Waiting for call to start...</div>
        ) : (
          transcript.map((msg, idx) => (
            <div key={idx} className={`message-bubble ${msg.speaker.toLowerCase()}`}>
              <div className="message-header">
                <span className="speaker">{msg.speaker}</span>
                {msg.language && <span className="pill lang-pill">{msg.language}</span>}
                {msg.confidence && msg.confidence < 0.8 && (
                  <span className="confidence-pill">{Math.round(msg.confidence * 100)}% conf</span>
                )}
                <span className="timestamp">{new Date(msg.timestamp || Date.now()).toLocaleTimeString()}</span>
              </div>
              <div className={`message-body ${msg.isPartial ? 'partial' : ''}`}>
                {msg.text}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default LiveTranscript;
