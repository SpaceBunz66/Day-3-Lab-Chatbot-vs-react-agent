// ----- Trang thai -----
let conversations = JSON.parse(localStorage.getItem("convos") || "[]");
let currentId = null;

const $ = (id) => document.getElementById(id);
const welcome = $("welcome");
const messagesEl = $("messages");
const input = $("questionInput");
const sendBtn = $("sendBtn");

// ----- Tien ich luu tru -----
function save() {
  localStorage.setItem("convos", JSON.stringify(conversations));
  renderConvoList();
}
function currentConvo() {
  return conversations.find((c) => c.id === currentId);
}

// ----- Hien thi danh sach hoi thoai (sidebar) -----
function renderConvoList() {
  const list = $("convoList");
  const q = ($("searchInput").value || "").toLowerCase();
  const items = conversations.filter((c) => c.title.toLowerCase().includes(q));
  $("convoCount").textContent = `${items.length} cuộc hội thoại`;
  list.innerHTML = "";
  items.forEach((c) => {
    const div = document.createElement("div");
    div.className = "convo-item" + (c.id === currentId ? " active" : "");
    div.textContent = c.title;
    div.onclick = () => openConvo(c.id);
    list.appendChild(div);
  });
}

// ----- Hien thi tin nhan cua hoi thoai hien tai -----
function renderMessages() {
  const convo = currentConvo();
  if (!convo || convo.messages.length === 0) {
    welcome.style.display = "block";
    messagesEl.style.display = "none";
    return;
  }
  welcome.style.display = "none";
  messagesEl.style.display = "flex";
  messagesEl.innerHTML = "";
  convo.messages.forEach((m) => addBubble(m.role, m.content, m.meta));
  messagesEl.scrollIntoView(false);
}

function addBubble(role, content, meta) {
  const wrap = document.createElement("div");
  wrap.className = "msg " + (role === "user" ? "user" : "bot");
  const bubble = document.createElement("div");
  bubble.innerHTML = `<div class="bubble">${escapeHtml(content)}</div>` +
    (meta ? `<div class="meta">${meta}</div>` : "");
  wrap.appendChild(bubble);
  messagesEl.appendChild(wrap);
  wrap.scrollIntoView({ behavior: "smooth", block: "end" });
  return bubble.querySelector(".bubble");
}

function escapeHtml(s) {
  return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ----- Mo / tao hoi thoai -----
function openConvo(id) {
  currentId = id;
  renderConvoList();
  renderMessages();
}
function newConvo() {
  const convo = { id: Date.now().toString(), title: "Hội thoại mới", messages: [] };
  conversations.unshift(convo);
  currentId = convo.id;
  save();
  renderMessages();
}

// ----- Gui cau hoi -> goi API -----
async function send(text) {
  const question = (text || input.value).trim();
  if (!question) return;

  if (!currentConvo()) newConvo();
  const convo = currentConvo();
  if (convo.messages.length === 0) convo.title = question.slice(0, 40);

  // Lấy lịch sử TRƯỚC khi push câu hỏi mới để tránh bị trùng
  const historyMessages = (currentConvo()?.messages || []).slice(-10);
  const history = historyMessages
    .filter((m) => m.role === "user" || m.role === "bot")
    .map((m) => ({ role: m.role, content: m.content }));

  convo.messages.push({ role: "user", content: question });
  input.value = "";
  input.style.height = "auto";
  save();
  renderMessages();

  // bong bong "dang tra loi..."
  welcome.style.display = "none";
  messagesEl.style.display = "flex";
  const botBubble = addBubble("bot", "Đang trả lời...", "");
  botBubble.classList.add("typing");
  sendBtn.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, history }),
    });
    const data = await res.json();

    if (!data.ok) {
      botBubble.classList.remove("typing");
      botBubble.textContent = "❌ Lỗi: " + (data.error || "khong xac dinh");
      sendBtn.disabled = false;
      return;
    }

    const usage = data.usage || {};
    const meta = `⏱ ${data.latency_ms ?? "?"} ms · 🔢 ${usage.total_tokens ?? "?"} tokens · 🤖 ${data.provider ?? ""}`;
    convo.messages.push({ role: "bot", content: data.content, meta });
    save();
    renderMessages();
  } catch (e) {
    botBubble.classList.remove("typing");
    botBubble.textContent = "❌ Không kết nối được server: " + e.message;
  } finally {
    sendBtn.disabled = false;
  }
}

// ----- Su kien -----
sendBtn.onclick = () => send();
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
});
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = input.scrollHeight + "px";
});
$("newChatBtn").onclick = newConvo;
$("searchInput").addEventListener("input", renderConvoList);
document.querySelectorAll(".suggest-card").forEach((c) => {
  c.onclick = () => send(c.textContent);
});
document.querySelectorAll(".tab").forEach((t) => {
  t.onclick = () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
  };
});

// Doi giao dien sang/toi
$("themeBtn").onclick = () => {
  const dark = document.documentElement.getAttribute("data-theme") === "dark";
  document.documentElement.setAttribute("data-theme", dark ? "light" : "dark");
  $("themeBtn").textContent = dark ? "🌙" : "☀️";
};

// ----- Khoi tao -----
renderConvoList();
renderMessages();
