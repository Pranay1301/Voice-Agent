import React from 'react';

function CallSummary({ summary }) {
  if (!summary) return null;

  return (
    <div className="card call-summary">
      <h2>📊 Call Summary</h2>
      <div className="summary-content">
        <div className="summary-field">
          <strong>Lead Classification:</strong>
          <span className="pill ml-2">{summary.classification || 'Unknown'}</span>
        </div>
        
        {summary.classificationReasoning && summary.classificationReasoning.length > 0 && (
          <div className="summary-field">
            <strong>Classification Reasoning:</strong>
            <ul>
              {summary.classificationReasoning.map((r, i) => <li key={i}>{r}</li>)}
            </ul>
          </div>
        )}

        {summary.keyPoints && summary.keyPoints.length > 0 && (
          <div className="summary-field">
            <strong>Key Points:</strong>
            <ul>
              {summary.keyPoints.map((p, i) => <li key={i}>{p}</li>)}
            </ul>
          </div>
        )}

        {summary.objections && summary.objections.length > 0 && (
          <div className="summary-field">
            <strong>Objections:</strong>
            <ul>
              {summary.objections.map((o, i) => <li key={i}>{o}</li>)}
            </ul>
          </div>
        )}

        <div className="summary-field">
          <strong>Next Action:</strong>
          <div>{summary.nextAction || 'None'}</div>
        </div>

        <div className="summary-field">
          <strong>Duration:</strong>
          <div>{summary.duration ? `${summary.duration}s` : 'Unknown'}</div>
        </div>
      </div>
    </div>
  );
}

export default CallSummary;
