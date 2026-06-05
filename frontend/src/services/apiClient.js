const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = {
  async getSystemInfo() {
    const res = await fetch(`${API_BASE}/`);
    return res.json();
  },

  async getChapters() {
    const res = await fetch(`${API_BASE}/chapters`);
    return res.json();
  },

  async search(query, topK = 3, chuong = null, backend = null, chunking = null) {
    const res = await fetch(`${API_BASE}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, top_k: topK, chuong, backend, chunking })
    });
    return res.json();
  },

  async ask(question, topK = 3, chuong = null, backend = null, chunking = null, threshold = null) {
    const res = await fetch(`${API_BASE}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, top_k: topK, chuong, backend, chunking, threshold })
    });
    return res.json();
  },

  async getHistory(limit = 20) {
    const res = await fetch(`${API_BASE}/history?limit=${limit}`);
    return res.json();
  }
};
