import { useState, useRef, useEffect } from 'react';
import { apiClient } from '../services/apiClient';
import { AskResponse } from '../models/types';
import '../styles/chatbot.css';

export function Chatbot({
  selectedChapter,
  selectedBackend,
  selectedChunking,
  selectedThreshold,
  onNewMessage,
  initialData = null
}) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (initialData) {
      setMessages([
        {
          type: 'question',
          content: initialData.question,
          timestamp: new Date()
        },
        {
          type: 'answer',
          content: initialData.answer,
          backend: initialData.backend,
          chunking: initialData.chunking,
          citations: initialData.citations || [],
          topScore: initialData.topScore,
          grounded: initialData.grounded,
          timestamp: new Date()
        }
      ]);
      setInput('');
    }
  }, [initialData]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = input.trim();
    setMessages(prev => [...prev, {
      type: 'question',
      content: userMessage,
      timestamp: new Date()
    }]);
    setInput('');
    setLoading(true);

    try {
      const response = await apiClient.ask(
        userMessage,
        3,
        selectedChapter || null,
        selectedBackend,
        selectedChunking,
        selectedThreshold
      );

      const askRes = new AskResponse(response);
      setMessages(prev => [...prev, {
        type: 'answer',
        content: askRes.answer,
        backend: askRes.backend,
        chunking: askRes.chunking,
        citations: askRes.citations,
        topScore: askRes.topScore,
        grounded: askRes.grounded,
        timestamp: new Date()
      }]);

      onNewMessage?.(askRes);
    } catch (err) {
      console.error('Failed to send message:', err);
      setMessages(prev => [...prev, {
        type: 'error',
        content: 'Lỗi: ' + err.message,
        timestamp: new Date()
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chatbot">
      <div className="chatbot-header">
        <h2>💬 Hỏi về Luật An ninh Mạng</h2>
      </div>

      <div className="messages-container">
        {messages.length === 0 && (
          <div className="empty-chat">
            <p>👋 Xin chào! Hãy hỏi tôi về Luật An ninh Mạng 116/2025</p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`message message-${msg.type}`}>
            {msg.type === 'question' && (
              <div className="message-content">
                <p>{msg.content}</p>
                <span className="message-time">
                  {msg.timestamp.toLocaleTimeString('vi-VN')}
                </span>
              </div>
            )}

            {msg.type === 'answer' && (
              <div className="message-content">
                <div className="answer-box">
                  <div className="answer-meta">
                    <span className="meta-badge">🤖 {msg.backend || 'mock'}</span>
                    <span className="meta-badge">🔪 {msg.chunking || 'recursive'}</span>
                  </div>
                  <p>{msg.content}</p>

                  {msg.citations && msg.citations.length > 0 && (
                    <div className="citations">
                      <p className="citations-title">📌 Nguồn:</p>
                      {msg.citations.map((cite, i) => (
                        <div key={i} className="citation-item">
                          <span className="citation-label">{cite.label}</span>
                          <span className="citation-score">
                            Score: {cite.score.toFixed(4)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {!msg.grounded && msg.topScore !== undefined && (
                    <div className="warning">
                      ⚠️ Độ tin cậy thấp (Score: {msg.topScore.toFixed(4)})
                    </div>
                  )}
                </div>

                <span className="message-time">
                  {msg.timestamp.toLocaleTimeString('vi-VN')}
                </span>
              </div>
            )}

            {msg.type === 'error' && (
              <div className="message-content error-box">
                <p>{msg.content}</p>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="message message-loading">
            <div className="loading-spinner">⌛ Đang xử lý...</div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Hỏi câu hỏi của bạn..."
          disabled={loading}
          className="input-field"
        />
        <button type="submit" disabled={loading} className="send-button">
          {loading ? 'Đang gửi...' : '➤ Gửi'}
        </button>
      </form>
    </div>
  );
}
