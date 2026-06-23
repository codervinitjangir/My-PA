export const api = {
  async getHealth() {
    const res = await fetch(`/health`);
    return res.json();
  },
  
  async getWakeWordStatus() {
    const res = await fetch(`/api/wake-word/status`);
    return res.json();
  },

  async getDashboard() {
    const res = await fetch(`/dashboard`);
    return res.json();
  },

  async getBriefing() {
    const res = await fetch(`/briefing`);
    return res.json();
  },

  async performOperatorAction(action: string, payload?: any) {
    const res = await fetch(`/operator/action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, payload })
    });
    return res.json();
  },

  async getFrictions() {
    const res = await fetch(`/frictions`);
    return res.json();
  },

  async addFriction(text: string) {
    const res = await fetch(`/frictions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    return res.json();
  },

  async resolveFriction(id: string) {
    const res = await fetch(`/frictions/${id}`, {
      method: 'PATCH'
    });
    return res.json();
  },

  async deleteFriction(id: string) {
    const res = await fetch(`/frictions/${id}`, {
      method: 'DELETE'
    });
    return res.json();
  },

  async getUsage() {
    const res = await fetch(`/usage`);
    return res.json();
  },

  async sendMessage(message: string, sessionId?: string) {
    const res = await fetch(`/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, session_id: sessionId })
    });
    return res.json();
  }
};

