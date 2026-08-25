const BASE_URL = '';

export const api = {
  async request(endpoint, options = {}) {
    try {
      const response = await fetch(`${BASE_URL}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        return { error: data.error || data.message || `Error ${response.status}`, data: null };
      }
      return { data, error: null };
    } catch (error) {
      return { error: error.message, data: null };
    }
  },

  startCall(targetNumber, confirmationToken) {
    return this.request('/api/calls/start', {
      method: 'POST',
      body: JSON.stringify({ targetNumber, confirmationToken }),
    });
  },

  endCall(callId) {
    return this.request(`/api/calls/${callId}/end`, {
      method: 'POST',
    });
  },

  getCallStatus(callId) {
    return this.request(`/api/calls/${callId}`);
  },

  getLeads() {
    return this.request('/api/leads');
  },

  getDashboardState() {
    return this.request('/api/dashboard/state');
  },

  getConfirmationToken() {
    return this.request('/api/calls/confirmation-token');
  },

  sendTestMessage(text) {
    return this.request('/api/test/message', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
  }
};
