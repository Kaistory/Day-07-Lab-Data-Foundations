import { useState, useRef, useEffect } from 'react';
import { apiClient } from '../services/apiClient';
import { AskResponse } from '../models/types';
import { ScoreRing } from './ScoreRing';
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
  }, [messages, loading]);

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

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chatbot">
      <div className="chatbot-header">
        <h2>
          <span>💬</span> Hỏi về Luật An ninh Mạng
        </h2>
      </div>

      <div className="messages-container">
        {messages.length === 0 && (
          <div className="empty-chat">
            <p>👋 Xin chào! Hãy hỏi tôi bất kỳ câu hỏi nào về Luật An ninh Mạng 116/2025.</p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`message message-${msg.type}`}>
            {msg.type === 'question' && (
              <div className="message-content">
                <p>{msg.content}</p>
                <span className="message-time">
                  {msg.timestamp.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            )}

            {msg.type === 'answer' && (
              <div className="message-content">
                <div className="answer-box">
                  <div className="answer-meta">
                    <span className="meta-badge">🤖 {msg.backend || 'mock'}</span>
                    <span className="meta-badge">✂️ {msg.chunking || 'recursive'}</span>
                  </div>
                  <p>{msg.content}</p>

                  {msg.citations && msg.citations.length > 0 && (
                    <div className="citations">
                      <p className="citations-title">📌 Nguồn tham khảo</p>
                      <div className="citations-grid">
                        {msg.citations.map((cite, i) => (
                          <div key={i} className="citation-item">
                            <ScoreRing score={cite.score} />
                            <span className="citation-label">{cite.label}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {!msg.grounded && msg.topScore !== undefined && (
                    <div className="warning">
                      <span>⚠️</span> Câu trả lời có độ tin cậy thấp (Score: {msg.topScore.toFixed(4)}). Có thể thông tin không nằm trong ngữ cảnh.
                    </div>
                  )}
                </div>

                <span className="message-time">
                  {msg.timestamp.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
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
            <div className="message-content">
              <div className="loading-spinner">
                <div className="typing-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                Đang tìm câu trả lời...
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="input-container">
        <form onSubmit={handleSubmit} className="input-form">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Hỏi câu hỏi của bạn..."
            disabled={loading}
            className="input-field"
            rows="1"
          />
          <button type="submit" disabled={loading || !input.trim()} className="send-button" title="Gửi">
            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}
