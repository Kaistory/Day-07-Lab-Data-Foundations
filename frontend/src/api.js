export const API_URL = 'http://localhost:8000/api';

export const uploadDocument = async (file, strategy) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('chunking_strategy', strategy);

  const res = await fetch(`${API_URL}/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error('Upload failed');
  return res.json();
};

export const getDocumentsStats = async () => {
  const response = await fetch(`${API_URL}/documents`);
  return response.json();
};

export const getAllChunks = async () => {
  const response = await fetch(`${API_URL}/chunks`);
  return response.json();
};

export const getStats = async () => {
  const res = await fetch(`${API_URL}/documents`);
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
};

export const searchDocuments = async (query) => {
  const res = await fetch(`${API_URL}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: 3 }),
  });
  if (!res.ok) throw new Error('Search failed');
  return res.json();
};

export const chatWithAgent = async (query) => {
  const res = await fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error('Chat failed');
  return res.json();
};
