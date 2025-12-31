import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import { ProgressMessage } from "../types";

type Props = {
  apiBase: string;
  userId: string;
  messages: ProgressMessage[];
  setMessages: (messages: ProgressMessage[]) => void;
  openaiKey?: string;
  memoriKey?: string;
};

function ProgressTab({
  apiBase,
  userId,
  messages,
  setMessages,
  openaiKey,
  memoriKey
}: Props) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendQuestion = async (e: React.FormEvent) => {
    e.preventDefault();
    const question = input.trim();
    if (!question || !userId) return;

    setError(null);
    setLoading(true);
    setMessages([...messages, { role: "user", content: question }]);
    setInput("");

    try {
      const res = await fetch(`${apiBase}/progress`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId, question, openaiKey, memoriKey })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Failed to query Memori");
      }
      const data = await res.json();
      const answer = data.answer ?? "";
      setMessages((prev) => [...prev, { role: "assistant", content: answer }]);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `❌ Failed to query Memori: ${msg}` }
      ]);
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="tab-panel">
      <h2>📈 Progress &amp; Memory (Memori-powered)</h2>
      <p>
        Ask questions about your interview performance, weak patterns, or trends.
      </p>
      <ul className="examples">
        <li>Which algorithm patterns am I weakest at right now?</li>
        <li>How have I improved over my last 10 attempts?</li>
        <li>What difficulty should I focus on this week?</li>
      </ul>

      <section className="chat-window">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={m.role === "user" ? "chat-bubble user" : "chat-bubble assistant"}
          >
            <div className="chat-role">
              {m.role === "user" ? "You" : "Assistant"}
            </div>
            <ReactMarkdown className="markdown">{m.content}</ReactMarkdown>
          </div>
        ))}
        {messages.length === 0 && (
          <div className="empty-chat">
            Start the conversation by asking how you are doing in your interview prep.
          </div>
        )}
      </section>

      <form className="chat-input-row" onSubmit={sendQuestion}>
        <input
          type="text"
          value={input}
          placeholder="Ask about your interview progress…"
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          {loading ? "Thinking…" : "Send"}
        </button>
      </form>

      {error && <div className="banner error">{error}</div>}
    </div>
  );
}

export default ProgressTab;
