import React, { useState, useEffect } from 'react';
import { Upload, Database, Search, Bot, FileText, Activity, Sun, Moon } from 'lucide-react';
import { uploadDocument, getStats, searchDocuments, chatWithAgent, getAllChunks } from './api';

function App() {
  const [file, setFile] = useState(null);
  const [strategy, setStrategy] = useState('recursive');
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({ count: 0, message: '' });
  
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [chatResponse, setChatResponse] = useState('');
  const [toast, setToast] = useState('');
  
  const [showModal, setShowModal] = useState(false);
  const [allChunks, setAllChunks] = useState([]);
  const [isLight, setIsLight] = useState(false);

  useEffect(() => {
    if (isLight) {
      document.body.classList.add('light-theme');
    } else {
      document.body.classList.remove('light-theme');
    }
  }, [isLight]);

  const fetchAllChunks = async () => {
    try {
      const data = await getAllChunks();
      setAllChunks(data.chunks || []);
      setShowModal(true);
    } catch (e) {
      showToast('Error loading chunks');
    }
  };

  const fetchStats = async () => {
    try {
      const data = await getStats();
      setStats(data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(''), 3000);
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const data = await uploadDocument(file, strategy);
      if (data.error) {
        showToast(`❌ Lỗi: ${data.message}`);
      } else {
        showToast(`✅ Thành công: ${data.message}`);
        fetchStats();
      }
      setFile(null);
    } catch (e) {
      showToast('❌ Lỗi hệ thống khi tải file lên');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!query) return;
    setLoading(true);
    setChatResponse('');
    try {
      const data = await searchDocuments(query);
      if (data.error) {
        showToast(data.message);
        setResults([]);
      } else {
        setResults(data.results || []);
      }
    } catch (e) {
      showToast('Error searching');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleChat = async () => {
    if (!query) return;
    setLoading(true);
    setResults([]);
    try {
      const data = await chatWithAgent(query);
      setChatResponse(data.answer);
    } catch (e) {
      showToast('Error getting answer');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <button className="theme-toggle" onClick={() => setIsLight(!isLight)}>
        {isLight ? <Moon size={24} /> : <Sun size={24} />}
      </button>

      {/* Sidebar */}
      <div className="sidebar">
        <div className="card glass-panel" style={{ flex: 1 }}>
          <div className="card-header">
            <Database size={24} />
            <h2>Data Ingestion</h2>
          </div>
          
          <div className="form-group">
            <label>Upload Document (PDF, MD, TXT)</label>
            <div className="upload-zone" onClick={() => document.getElementById('file-upload').click()}>
              <Upload size={32} style={{ color: '#818cf8', marginBottom: '12px' }} />
              <p>{file ? file.name : 'Click or Drag to Upload'}</p>
              <input 
                id="file-upload" 
                type="file" 
                style={{ display: 'none' }}
                onChange={(e) => setFile(e.target.files[0])}
              />
            </div>
          </div>

          <div className="form-group">
            <label>Chunking Strategy</label>
            <select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
              <option value="llm">LLM Semantic Chunking (Gemini)</option>
              <option value="recursive">Recursive Character</option>
              <option value="fixed">Fixed Size</option>
              <option value="sentence">Sentence Based</option>
            </select>
          </div>

          <button onClick={handleUpload} disabled={!file || loading}>
            {loading ? <Activity className="spinner" size={18} /> : <Upload size={18} />}
            Process & Store
          </button>
        </div>

        <div className="card glass-panel">
          <div className="card-header">
            <Activity size={24} />
            <h2>System Stats</h2>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ padding: '12px', background: 'rgba(99, 102, 241, 0.1)', borderRadius: '8px', color: '#818cf8' }}>
              <FileText size={24} />
            </div>
            <div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Total Vector Chunks</p>
              <h3 style={{ fontSize: '1.5rem', margin: 0 }}>{stats.count}</h3>
            </div>
          </div>
          <button style={{ marginTop: '16px', background: 'rgba(129, 140, 248, 0.1)', color: '#818cf8' }} onClick={fetchAllChunks}>
            <Search size={18} /> View All Chunks
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        <div className="card glass-panel" style={{ flex: 'none' }}>
          <div className="card-header">
            <Search size={24} />
            <h2><span className="gradient-text">RAG Intelligence</span></h2>
          </div>
          <div style={{ display: 'flex', gap: '12px' }}>
            <input 
              type="text" 
              placeholder="Ask anything about your documents..." 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
            <button onClick={handleSearch} disabled={loading || !query}>
              Vector Search
            </button>
            <button onClick={handleChat} disabled={loading || !query} style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#10b981' }}>
              <Bot size={18} /> Ask LLM
            </button>
          </div>
        </div>

        <div className="card glass-panel result-box">
          {loading && <div style={{ textAlign: 'center', padding: '40px' }}><Activity className="spinner" size={32} color="#818cf8" /></div>}
          
          {!loading && results.length > 0 && (
            <div>
              <h3 style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>Top Vector Matches</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {results.map((r, i) => (
                  <div key={i} className="chunk-card">
                    <div className="chunk-header">
                      <span className="badge">Rank #{i + 1}</span>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        {r.metadata?.topic && <span className="badge" style={{background: 'rgba(192, 132, 252, 0.1)', color: '#c084fc'}}>{r.metadata.topic}</span>}
                        <span className="score-badge">Cosine: {r.cosine_similarity.toFixed(4)}</span>
                      </div>
                    </div>
                    <p className="chunk-text">{r.content}</p>
                    <div style={{ marginTop: '12px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      Source ID: {r.id} | Chroma Distance Score: {r.score?.toFixed(4)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {!loading && chatResponse && (
            <div>
              <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Bot size={20} color="#10b981" /> AI Response
              </h3>
              <div className="chat-bubble">
                {chatResponse.split('\n').map((line, i) => <p key={i}>{line}</p>)}
              </div>
            </div>
          )}

          {!loading && results.length === 0 && !chatResponse && (
            <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '60px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
              <Search size={48} opacity={0.2} />
              <p>Type a query to search vectors or ask the AI agent</p>
            </div>
          )}
        </div>
      </div>

      {toast && <div className="toast">{toast}</div>}

      {/* Modal View Chunks */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-content glass-panel" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Database Chunks ({allChunks.length})</h2>
              <button className="close-btn" onClick={() => setShowModal(false)}>×</button>
            </div>
            <div className="modal-body">
              {allChunks.length === 0 ? (
                <p style={{textAlign: 'center', color: 'var(--text-secondary)'}}>No chunks found in database.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {allChunks.map((c, i) => (
                    <div key={i} className="chunk-card">
                      <div className="chunk-header">
                        <span className="badge">ID: {c.id}</span>
                        {c.metadata?.source && <span className="badge" style={{background: 'rgba(16, 185, 129, 0.1)', color: '#10b981'}}>Source: {c.metadata.source}</span>}
                      </div>
                      <p className="chunk-text">{c.content}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
