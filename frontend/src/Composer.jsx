import { useRef, useState } from "react";

const ACCEPT =
  ".pdf,.docx,.txt,.py,.java,.js,.cpp,.c,.html,.css,.png,.jpg,.jpeg,.webp,.gif";
const MAX_FILES = 5;
const MAX_BYTES = 10 * 1024 * 1024;

export default function Composer({ onSubmit, loading }) {
  const [text, setText] = useState("");
  const [files, setFiles] = useState([]);
  const [problem, setProblem] = useState("");
  const inputRef = useRef(null);

  function addFiles(list) {
    const incoming = Array.from(list);
    const next = files.slice();
    let msg = "";
    incoming.forEach((f) => {
      if (f.size > MAX_BYTES) msg = f.name + " is larger than 10 MB";
      else if (next.length >= MAX_FILES)
        msg = "You can attach up to " + MAX_FILES + " files";
      else next.push(f);
    });
    setFiles(next);
    setProblem(msg);
  }

  async function send() {
    if (loading) return;
    if (!text.trim() && files.length === 0) {
      setProblem("Type a prompt or attach a file first");
      return;
    }
    setProblem("");
    const ok = await onSubmit(text, files);
    if (ok) {
      setText("");
      setFiles([]);
    }
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div
      className="composer-wrap"
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        addFiles(e.dataTransfer.files);
      }}
    >
      {problem && <div className="composer-problem">{problem}</div>}
      <div className="composer">
        {files.length > 0 && (
          <div className="chips">
            {files.map((f, i) => (
              <span className="chip" key={f.name + i}>
                {f.name}
                <button
                  aria-label={"Remove " + f.name}
                  onClick={() => setFiles(files.filter((_, j) => j !== i))}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
        <div className="composer-row">
          <button
            className="icon-btn"
            aria-label="Attach files"
            onClick={() => inputRef.current.click()}
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
            </svg>
          </button>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={ACCEPT}
            hidden
            onChange={(e) => {
              addFiles(e.target.files);
              e.target.value = "";
            }}
          />
          <textarea
            rows={1}
            value={text}
            placeholder="Type a prompt or attach PDF, DOCX, code, or images"
            onChange={(e) => setText(e.target.value)}
            onKeyDown={onKeyDown}
          />
          <button
            className="send-btn"
            aria-label="Estimate"
            onClick={send}
            disabled={loading}
          >
            {loading ? <span className="spinner" /> : "↑"}
          </button>
        </div>
      </div>
      <p className="muted small center">
        Estimates use each provider's token rules. Output length is a guess.
      </p>
    </div>
  );
}
