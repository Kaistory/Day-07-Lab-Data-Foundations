const { useEffect, useRef, useState } = React;
const html = htm.bind(React.createElement);

const EXAMPLES = [
  "Luật An ninh mạng có hiệu lực từ ngày nào?",
  "Cha mẹ có trách nhiệm gì khi trẻ em sử dụng dịch vụ trên không gian mạng?",
  "Thời điểm COT được quy định vào lúc mấy giờ?",
];

function renderAnswer(answer) {
  return answer.split(/(\*\*[^*]+\*\*)/g).map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return html`<strong key=${index}>${part.slice(2, -2)}</strong>`;
    }
    return part;
  });
}

function App() {
  const [config, setConfig] = useState(null);
  const [question, setQuestion] = useState("");
  const [strategy, setStrategy] = useState("document");
  const [topK, setTopK] = useState(3);
  const [threshold, setThreshold] = useState(0.55);
  const [documentNumber, setDocumentNumber] = useState("");
  const [citation, setCitation] = useState("");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [configError, setConfigError] = useState("");
  const threadRef = useRef(null);

  useEffect(() => {
    fetch("/api/config")
      .then((result) => {
        if (!result.ok) throw new Error("Không tải được cấu hình");
        return result.json();
      })
      .then((data) => {
        setConfig(data);
        setStrategy(data.default_strategy);
        setTopK(data.default_top_k);
        setThreshold(data.default_threshold);
      })
      .catch((reason) => setConfigError(reason.message));
  }, []);

  useEffect(() => {
    const thread = threadRef.current;
    if (thread) {
      thread.scrollTo({ top: thread.scrollHeight, behavior: "smooth" });
    }
  }, [messages, loading]);

  async function sendQuestion(rawQuestion) {
    const cleanQuestion = rawQuestion.trim();
    if (!cleanQuestion || loading) return;

    const userMessage = {
      id: `${Date.now()}-user`,
      role: "user",
      content: cleanQuestion,
    };
    setMessages((current) => [...current, userMessage]);
    setQuestion("");
    setLoading(true);

    try {
      const result = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: cleanQuestion,
          strategy,
          top_k: Number(topK),
          threshold: Number(threshold),
          document_number: documentNumber.trim(),
          citation: citation.trim(),
        }),
      });
      const data = await result.json();
      if (!result.ok) throw new Error(data.error || "Yêu cầu thất bại");
      setMessages((current) => [
        ...current,
        {
          id: `${Date.now()}-assistant`,
          role: "assistant",
          content: data.answer,
          response: data,
        },
      ]);
    } catch (reason) {
      setMessages((current) => [
        ...current,
        {
          id: `${Date.now()}-error`,
          role: "error",
          content: reason.message || "Không thể kết nối backend",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function submit(event) {
    event.preventDefault();
    sendQuestion(question);
  }

  function handleComposerKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendQuestion(question);
    }
  }

  function resetConversation() {
    setMessages([]);
    setQuestion("");
  }

  return html`
    <main className="chat-app">
      <header className="chat-header">
        <a className="brand" href="/" aria-label="Điều Luật, trang chủ">
          <span className="brand-mark">ĐL</span>
          <span>
            <strong>Điều Luật</strong>
            <small>Trợ lý pháp luật có dẫn nguồn</small>
          </span>
        </a>

        <div className="header-actions">
          <span className="model-chip">
            <i></i>
            ${config?.chat_model || "ChatGPT"}
          </span>
          <button className="text-button" type="button" onClick=${resetConversation}>
            Cuộc trò chuyện mới
          </button>
          <button
            className="settings-button"
            type="button"
            onClick=${() => setSettingsOpen(!settingsOpen)}
            aria-expanded=${settingsOpen}
          >
            Cấu hình
          </button>
        </div>
      </header>

      <div className="chat-layout">
        <aside className=${`retrieval-sidebar ${settingsOpen ? "open" : ""}`}>
          <div className="sidebar-heading">
            <div>
              <span>Retrieval setup</span>
              <h2>Cấu hình truy xuất</h2>
            </div>
            <button
              className="close-settings"
              type="button"
              onClick=${() => setSettingsOpen(false)}
              aria-label="Đóng cấu hình"
            >
              Đóng
            </button>
          </div>

          <label>
            <span>Chunking strategy</span>
            <select
              value=${strategy}
              onChange=${(event) => setStrategy(event.target.value)}
            >
              ${(config?.strategies || [
                "fixed",
                "sentence",
                "recursive",
                "semantic",
                "document",
              ]).map(
                (item) => html`<option key=${item} value=${item}>${item}</option>`,
              )}
            </select>
          </label>

          <div className="paired-controls">
            <label>
              <span>Top K</span>
              <input
                type="number"
                min="1"
                max="8"
                value=${topK}
                onChange=${(event) => setTopK(event.target.value)}
              />
            </label>
            <label>
              <span>Threshold <b>${Number(threshold).toFixed(2)}</b></span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value=${threshold}
                onChange=${(event) => setThreshold(event.target.value)}
              />
            </label>
          </div>

          <button
            type="button"
            className="advanced-toggle"
            onClick=${() => setAdvancedOpen(!advancedOpen)}
            aria-expanded=${advancedOpen}
          >
            ${advancedOpen ? "Ẩn bộ lọc metadata" : "Thêm bộ lọc metadata"}
          </button>

          ${advancedOpen &&
          html`
            <div className="advanced-controls">
              <label>
                <span>Số văn bản</span>
                <input
                  value=${documentNumber}
                  onChange=${(event) => setDocumentNumber(event.target.value)}
                  placeholder="81/2025/TT-BTC"
                />
              </label>
              <label>
                <span>Citation</span>
                <input
                  value=${citation}
                  onChange=${(event) => setCitation(event.target.value)}
                  placeholder="116/2025/QH15:44"
                />
              </label>
            </div>
          `}

          <div className="retrieval-status">
            <div>
              <span>Embedding</span>
              <strong>${config?.embedding_model || "text-embedding-3-small"}</strong>
            </div>
            <div>
              <span>Vector store</span>
              <strong>ChromaDB</strong>
            </div>
            <p>Top K và score vẫn được in đầy đủ trong terminal backend.</p>
          </div>
        </aside>

        <section className="conversation-panel">
          <div className="message-thread" ref=${threadRef} aria-live="polite">
            ${messages.length === 0 &&
            html`
              <div className="welcome-state">
                <span className="welcome-mark">ĐL</span>
                <p>Tra cứu pháp luật Việt Nam</p>
                <h1>Bạn cần tìm quy định nào?</h1>
                <span className="welcome-copy">
                  Câu trả lời được tổng hợp từ các chunk vượt threshold và luôn
                  đi kèm nguồn retrieval.
                </span>
                <div className="prompt-grid">
                  ${EXAMPLES.map(
                    (example) => html`
                      <button
                        key=${example}
                        type="button"
                        onClick=${() => sendQuestion(example)}
                      >
                        ${example}
                      </button>
                    `,
                  )}
                </div>
              </div>
            `}

            ${messages.map(
              (message) => html`
                <${ChatMessage} key=${message.id} message=${message} />
              `,
            )}

            ${loading &&
            html`
              <div className="message-row assistant-row">
                <span className="avatar">ĐL</span>
                <div className="assistant-bubble loading-bubble">
                  <span></span><span></span><span></span>
                  <p>Đang truy xuất và tổng hợp nguồn...</p>
                </div>
              </div>
            `}
          </div>

          <form className="composer-area" onSubmit=${submit}>
            ${configError &&
            html`<div className="config-error" role="alert">${configError}</div>`}
            <div className="composer">
              <textarea
                aria-label="Nhập câu hỏi pháp luật"
                value=${question}
                onChange=${(event) => setQuestion(event.target.value)}
                onKeyDown=${handleComposerKeyDown}
                placeholder="Nhập câu hỏi pháp luật..."
                rows="1"
              ></textarea>
              <button
                className="send-button"
                type="submit"
                disabled=${loading || !question.trim()}
              >
                Gửi
              </button>
            </div>
            <p>
              Enter để gửi, Shift + Enter để xuống dòng. Nội dung chỉ mang tính
              hỗ trợ tra cứu.
            </p>
          </form>
        </section>
      </div>

      ${settingsOpen &&
      html`
        <button
          className="settings-backdrop"
          type="button"
          aria-label="Đóng cấu hình"
          onClick=${() => setSettingsOpen(false)}
        ></button>
      `}
    </main>
  `;
}

function ChatMessage({ message }) {
  if (message.role === "user") {
    return html`
      <div className="message-row user-row">
        <div className="user-bubble">${message.content}</div>
        <span className="avatar user-avatar">B</span>
      </div>
    `;
  }

  if (message.role === "error") {
    return html`
      <div className="message-row assistant-row">
        <span className="avatar">ĐL</span>
        <div className="assistant-bubble error-bubble">
          <strong>Không thể hoàn tất tra cứu</strong>
          <p>${message.content}</p>
        </div>
      </div>
    `;
  }

  return html`
    <div className="message-row assistant-row">
      <span className="avatar">ĐL</span>
      <div className="assistant-bubble">
        <div className="answer-copy">${renderAnswer(message.content)}</div>
        <div className="answer-context">
          <span>
            ${message.response.used_count}/${message.response.retrieved_count}
            chunk vượt ngưỡng
          </span>
          <span>
            ${message.response.strategy} · ${Number(
              message.response.threshold,
            ).toFixed(2)}
          </span>
        </div>
        <${EvidencePanel} response=${message.response} />
      </div>
    </div>
  `;
}

function EvidencePanel({ response }) {
  const [open, setOpen] = useState(false);
  const acceptedCount = response.results.filter((item) => item.accepted).length;
  return html`
    <div className="evidence-panel">
      <button
        type="button"
        className="evidence-toggle"
        onClick=${() => setOpen(!open)}
        aria-expanded=${open}
      >
        <span>Xem ${response.retrieved_count} nguồn retrieval</span>
        <small>${acceptedCount} nguồn được dùng · ${open ? "Thu gọn" : "Mở"}</small>
      </button>
      ${open &&
      html`
        <div className="evidence-list">
          ${response.results.map(
            (item) => html`<${EvidenceItem} key=${item.rank} item=${item} />`,
          )}
        </div>
      `}
    </div>
  `;
}

function EvidenceItem({ item }) {
  const [open, setOpen] = useState(false);
  return html`
    <article className=${`evidence-item ${item.accepted ? "accepted" : "rejected"}`}>
      <button
        type="button"
        className="evidence-summary"
        onClick=${() => setOpen(!open)}
        aria-expanded=${open}
      >
        <span className="rank">${item.rank}</span>
        <span className="evidence-title">
          <strong>${item.article !== "-" ? item.article : item.source}</strong>
          <small>${item.citation} · ${item.source}</small>
        </span>
        <span className="score">
          ${item.score.toFixed(4)}
          <small>${item.accepted ? "PASS" : "REJECT"}</small>
        </span>
      </button>
      ${open && html`<div className="evidence-content">${item.content}</div>`}
    </article>
  `;
}

ReactDOM.createRoot(document.getElementById("root")).render(html`<${App} />`);
