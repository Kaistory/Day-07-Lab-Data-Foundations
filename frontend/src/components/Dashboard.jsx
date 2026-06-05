import { useState, useEffect } from 'react';
import { apiClient } from '../services/apiClient';
import '../styles/dashboard.css';

export function Dashboard({
  selectedChapter,
  onChapterChange,
  selectedBackend,
  onBackendChange,
  selectedChunking,
  onChunkingChange,
  selectedThreshold,
  onThresholdChange,
  history,
  onHistorySelect
}) {
  const [chapters, setChapters] = useState([]);
  const [backends, setBackends] = useState([]);
  const [chunkings, setChunkings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const info = await apiClient.getSystemInfo();
        setBackends(info.available_backends || []);
        setChunkings(info.available_chunkings || []);

        const chaptersRes = await apiClient.getChapters();
        setChapters(chaptersRes.chapters || []);
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>📚 Luật An ninh Mạng</h2>
        <p className="subtitle">116/2025</p>
      </div>

      <div className="dashboard-section">
        <h3>Chương</h3>
        <div className="selector">
          <select
            value={selectedChapter || ''}
            onChange={(e) => onChapterChange(e.target.value || null)}
            className="dashboard-select"
          >
            <option value="">Tất cả chương</option>
            {chapters.map(ch => (
              <option key={ch.doc_id} value={ch.chuong}>
                Chương {ch.chuong}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="dashboard-section">
        <h3>Backend</h3>
        <div className="selector">
          <select
            value={selectedBackend}
            onChange={(e) => onBackendChange(e.target.value)}
            className="dashboard-select"
          >
            {backends.map(b => (
              <option key={b} value={b}>{b}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="dashboard-section">
        <h3>Chunking</h3>
        <div className="selector">
          <select
            value={selectedChunking}
            onChange={(e) => onChunkingChange(e.target.value)}
            className="dashboard-select"
          >
            {chunkings.map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="dashboard-section">
        <h3>Ngưỡng Tin Cậy</h3>
        <div className="threshold-control">
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={selectedThreshold}
            onChange={(e) => onThresholdChange(parseFloat(e.target.value))}
            className="threshold-slider"
          />
          <div className="threshold-value">{selectedThreshold.toFixed(2)}</div>
        </div>
      </div>

      <div className="dashboard-section history">
        <h3>📋 Lịch sử</h3>
        <div className="history-list">
          {history.length === 0 ? (
            <p className="empty-state">Chưa có lịch sử</p>
          ) : (
            history.map((entry, idx) => (
              <button
                key={idx}
                className="history-item"
                onClick={() => onHistorySelect(entry)}
                title={entry.question}
              >
                <span className="history-question">
                  {entry.question.substring(0, 30)}...
                </span>
                <span className="history-time">
                  {new Date(entry.time).toLocaleTimeString('vi-VN')}
                </span>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
