import React, { useEffect } from 'react';

function ConfirmationDialog({ number, onConfirm, onCancel }) {
  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') onCancel();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onCancel]);

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h3>⚠️ Confirm Outbound Call</h3>
        <p>Are you sure you want to place an outbound call to <strong>{number}</strong>?</p>
        <p className="warning-text">This will use Twilio credits and place a real phone call.</p>
        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onCancel}>Cancel</button>
          <button className="btn btn-success" onClick={onConfirm}>Yes, Place Call</button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmationDialog;
