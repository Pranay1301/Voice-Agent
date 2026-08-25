import React from 'react';

function LeadPanel({ leadInfo }) {
  const formatCurrency = (val) => {
    if (!val) return '—';
    if (typeof val === 'number') return `₹${val.toLocaleString('en-IN')}`;
    return val;
  };

  const getTemperatureColor = (temp) => {
    switch (temp?.toUpperCase()) {
      case 'HOT': return '🔴';
      case 'WARM': return '🟠';
      case 'COLD': return '🔵';
      default: return '⚪';
    }
  };

  return (
    <div className="card lead-panel">
      <h2>📋 Lead Information</h2>
      
      <div className="lead-header">
        <span className="temperature-badge">
          {getTemperatureColor(leadInfo.temperature)} {leadInfo.temperature || 'UNKNOWN'}
        </span>
        {leadInfo.intentScore !== undefined && (
          <div className="intent-score-container">
            <span className="intent-label">Intent Score:</span>
            <div className="progress-bar-bg">
              <div 
                className="progress-bar-fill" 
                style={{ width: `${Math.min(100, Math.max(0, leadInfo.intentScore * 100))}%` }}
              ></div>
            </div>
          </div>
        )}
      </div>

      <div className="lead-grid">
        <div className="field-group">
          <label>Name</label>
          <div>{leadInfo.name || '—'}</div>
        </div>
        <div className="field-group">
          <label>Phone</label>
          <div>{leadInfo.phone || '—'}</div>
        </div>
        <div className="field-group">
          <label>Email</label>
          <div>{leadInfo.email || '—'}</div>
        </div>
        <div className="field-group">
          <label>Language</label>
          <div>{leadInfo.language || '—'}</div>
        </div>
        <div className="field-group">
          <label>Budget</label>
          <div>{formatCurrency(leadInfo.budget)}</div>
        </div>
        <div className="field-group">
          <label>Location</label>
          <div>{leadInfo.location || '—'}</div>
        </div>
        <div className="field-group">
          <label>Property Type</label>
          <div>{leadInfo.propertyType || '—'}</div>
        </div>
        <div className="field-group">
          <label>Timeline</label>
          <div>{leadInfo.timeline || '—'}</div>
        </div>
        <div className="field-group">
          <label>Decision Maker</label>
          <div>{leadInfo.decisionMaker ? 'Yes' : (leadInfo.decisionMaker === false ? 'No' : '—')}</div>
        </div>
      </div>
      <div className="field-group full-width">
        <label>Requirements</label>
        <div>{leadInfo.requirements || '—'}</div>
      </div>
    </div>
  );
}

export default LeadPanel;
