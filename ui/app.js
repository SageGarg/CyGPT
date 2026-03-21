const chatLog = document.getElementById("chat-log");
const form = document.getElementById("composer");
const promptInput = document.getElementById("prompt");
const clearBtn = document.getElementById("clear-chat");

// Detect API base: if UI is on 8001 and API on 8000, rewrite host.
const current = window.location;
const inferredApiBase =
  current.port === "8001"
    ? `${current.protocol}//${current.hostname}:8000`
    : `${current.protocol}//${current.host}`;
const API_BASE = inferredApiBase;

let messages = [
  {
    role: "bot",
    content:
      "Hey! I’m Cy. Ask me about programs, deadlines, advising, or campus resources and I’ll answer with citations.",
    sources: [{ label: "catalog.iastate.edu", href: "https://catalog.iastate.edu" }],
  },
];
renderMessages();

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = promptInput.value.trim();
  if (!text) return;

  messages.push({ role: "user", content: text });
  renderMessages();
  promptInput.value = "";
  promptInput.focus();

  addTyping();
  const reply = await getReply(text);
  removeTyping();
  messages.push(reply);
  renderMessages();
});

let typingNode = null;
function addTyping() {
  typingNode = document.createElement("div");
  typingNode.className = "message";
  typingNode.innerHTML = `
    <div class="avatar">Cy</div>
    <div class="content">
      <div class="bubble bot" style="display:inline-flex;gap:6px;">
        <span class="dot"></span><span class="dot"></span><span class="dot"></span>
      </div>
    </div>`;
  chatLog.appendChild(typingNode);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function removeTyping() {
  if (typingNode) {
    typingNode.remove();
    typingNode = null;
  }
}

async function getReply(prompt) {
  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: prompt }),
    });

    if (!res.ok) throw new Error("fallback");
    const data = await res.json();
    return {
      role: "bot",
      content: data.answer || "No response received.",
      sources: data.sources?.map((s) => ({
        label: s.label || s.url,
        href: s.url,
      })),
    };
  } catch {
    // graceful fallback demo
    const canned = [
      "Iowa State’s priority FAFSA deadline for 2026–27 is March 1. Submitting after that date may reduce eligibility for need‑based aid.",
      "The Applied AI major requires MATH 165/166, COM S 227/228, and COM S 311 before upper‑division ML courses.",
      "You can schedule tutoring via the Academic Success Center; appointments and drop‑in hours are posted weekly.",
    ];
    const choice = canned[Math.floor(Math.random() * canned.length)];
    return {
      role: "bot",
      content: choice,
      sources: [
        { label: "Catalog", href: "#" },
        { label: "ASC", href: "#" },
      ],
    };
  }
}

function renderMessages() {
  chatLog.innerHTML = "";
  messages.forEach(({ role, content, sources }) => {
    const message = document.createElement("div");
    message.className = "message";
    message.classList.add(role);

    const avatar = document.createElement("div");
    avatar.className = `avatar ${role}`;
    avatar.textContent = role === "user" ? "You" : "Cy";

    const bubble = document.createElement("div");
    bubble.className = `bubble ${role}`;
    bubble.innerHTML = escapeHtml(content).replace(/\n/g, "<br>");

    const wrap = document.createElement("div");
    wrap.className = "content";
    wrap.appendChild(bubble);

    if (sources?.length) {
      const meta = document.createElement("div");
      meta.className = "meta";
      sources.forEach((s) => {
        const chip = document.createElement("a");
        chip.className = "source";
        chip.href = s.href || "#";
        chip.target = "_blank";
        chip.rel = "noreferrer noopener";
        chip.textContent = s.label;
        meta.appendChild(chip);
      });
      wrap.appendChild(meta);
    }

    if (role === "user") {
      message.appendChild(wrap);
      message.appendChild(avatar);
    } else {
      message.appendChild(avatar);
      message.appendChild(wrap);
    }
    chatLog.appendChild(message);
  });

  chatLog.scrollTop = chatLog.scrollHeight;
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

clearBtn?.addEventListener("click", () => {
  messages = [
    {
      role: "bot",
      content:
        "Chat cleared. Ask me anything about Iowa State programs, deadlines, or campus life.",
      sources: [{ label: "catalog.iastate.edu", href: "https://catalog.iastate.edu" }],
    },
  ];
  renderMessages();
  promptInput.focus();
});

// Allow Enter to send, Shift+Enter for newline (for multiline future)
promptInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});
