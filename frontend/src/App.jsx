import { useState, useEffect } from 'react';
import { Dashboard } from './components/Dashboard';
import { Chatbot } from './components/Chatbot';
import { apiClient } from './services/apiClient';
import './App.css';

function App() {
  const [selectedChapter, setSelectedChapter] = useState(null);
  const [selectedBackend, setSelectedBackend] = useState('mock');
  const [selectedChunking, setSelectedChunking] = useState('recursive');
  const [selectedThreshold, setSelectedThreshold] = useState(0.35);
  const [history, setHistory] = useState([]);
  const [selectedHistoryEntry, setSelectedHistoryEntry] = useState(null);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const data = await apiClient.getHistory(20);
      setHistory(data.reverse());
    } catch (err) {
      console.error('Failed to load history:', err);
    }
  };

  const handleNewMessage = (askResponse) => {
    setHistory(prev => [{
      question: askResponse.question,
      time: new Date().toISOString(),
      answer: askResponse.answer,
      top_score: askResponse.topScore,
      backend: askResponse.backend,
      chunking: askResponse.chunking,
      grounded: askResponse.grounded,
      citations: askResponse.citations.map(c => ({
        rank: c.rank,
        source: c.source,
        chuong: c.chuong,
        dieu: c.dieu,
        score: c.score,
        label: c.label
      })),
      sources: askResponse.sources.map(s => ({
        rank: s.rank,
        score: s.score,
        source: s.source,
        chuong: s.chuong,
        dieu: s.dieu,
        content: s.content
      }))
    }, ...prev]);
  };

  const handleHistorySelect = (entry) => {
    setSelectedHistoryEntry(entry);
  };

  return (
    <div className="app-container">
      <Dashboard
        selectedChapter={selectedChapter}
        onChapterChange={setSelectedChapter}
        selectedBackend={selectedBackend}
        onBackendChange={setSelectedBackend}
        selectedChunking={selectedChunking}
        onChunkingChange={setSelectedChunking}
        selectedThreshold={selectedThreshold}
        onThresholdChange={setSelectedThreshold}
        history={history}
        onHistorySelect={handleHistorySelect}
      />

      <Chatbot
        selectedChapter={selectedChapter}
        selectedBackend={selectedBackend}
        selectedChunking={selectedChunking}
        selectedThreshold={selectedThreshold}
        onNewMessage={handleNewMessage}
        initialData={selectedHistoryEntry}
      />
    </div>
  );
}

export default App;
