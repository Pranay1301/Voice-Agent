import React from 'react';

function ActionStatus({ actionStatus }) {
  const actions = [
    { id: 'whatsapp', name: 'WhatsApp', icon: '📱' },
    { id: 'email', name: 'Email', icon: '✉️' },
    { id: 'meeting', name: 'Meeting', icon: '📅' },
    { id: 'callback', name: 'Callback', icon: '📞' }
  ];

  const getStatusDisplay = (statusObj) => {
    if (!statusObj) return { text: 'Not Triggered', class: 'status-gray' };
    const s = typeof statusObj === 'string' ? statusObj : statusObj.status;
    const time = statusObj.time ? ` (${statusObj.time})` : '';
    
    switch (s?.toLowerCase()) {
      case 'sent':
      case 'scheduled':
      case 'success':
        return { text: `${s}${time}`, class: 'status-green' };
      case 'sending':
      case 'pending':
        return { text: `${s}${time}`, class: 'status-yellow' };
      case 'failed':
      case 'error':
        return { text: `${s}${time}`, class: 'status-red' };
      case 'not configured':
        return { text: 'Not Configured', class: 'status-gray' };
      default:
        return { text: s || 'Not Triggered', class: 'status-gray' };
    }
  };

  return (
    <div className="card action-status">
      <h2>⚡ Actions</h2>
      <div className="action-list">
        {actions.map(action => {
          const display = getStatusDisplay(actionStatus[action.id]);
          return (
            <div key={action.id} className="action-row">
              <span className="action-icon">{action.icon}</span>
              <span className="action-name">{action.name}</span>
              <span className={`action-badge ${display.class}`}>{display.text}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default ActionStatus;
