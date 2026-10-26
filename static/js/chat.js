// static/js/chat.js
// Advanced Generative AI Copilot Client for FinBuddy

const form = document.getElementById('chatForm');
const input = document.getElementById('messageInput');
const messages = document.getElementById('chatMessages');
const typingIndicator = document.getElementById('typingIndicator');
const sendBtn = document.getElementById('sendBtn');
const promptChips = document.getElementById('promptChips');
const receiptFileInput = document.getElementById('receiptFileInput');
const btnAttachReceipt = document.getElementById('btnAttachReceipt');
const btnVoiceInput = document.getElementById('btnVoiceInput');
const attachmentPreview = document.getElementById('attachmentPreview');
const previewImg = document.getElementById('previewImg');
const previewName = document.getElementById('previewName');
const btnRemoveAttach = document.getElementById('btnRemoveAttach');
const btnClearChat = document.getElementById('btnClearChat');
const btnExportChat = document.getElementById('btnExportChat');
const mobileMenuBtn = document.getElementById('mobileMenuBtn');
const sidebar = document.getElementById('sidebar');

let pendingFile = null;
let isRecording = false;
let recognition = null;

// ─────────────────────────────────────────
// Toast Notification Utility
// ─────────────────────────────────────────

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

// ─────────────────────────────────────────
// UI Helpers
// ─────────────────────────────────────────

function scrollToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function renderMarkdown(rawText) {
  if (!rawText) return '';
  let html = rawText
    .replace(/^### (.*$)/gim, '<h4 style="color:#fff;margin:10px 0 4px;font-size:14px;">$1</h4>')
    .replace(/^## (.*$)/gim, '<h3 style="color:#fff;margin:12px 0 6px;font-size:15px;">$1</h3>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/^\s*-\s+(.*$)/gim, '<li>$1</li>')
    .replace(/^\s*\d+\.\s+(.*$)/gim, '<li>$1</li>')
    .replace(/\n\n/g, '<p></p>')
    .replace(/\n/g, '<br>');

  // Wrap loose <li> tags into <ul>
  if (html.includes('<li>')) {
    html = html.replace(/(<li>[\s\S]*?<\/li>)/gi, '<ul>$1</ul>');
  }
  return html;
}

function appendMessage(role, text, options = {}) {
  const { reasoningSteps = [], transactionSaved = false, transaction = null } = options;

  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${role}`;

  // Avatar
  const avatar = document.createElement('div');
  avatar.className = 'message-avatar';
  avatar.textContent = role === 'bot' ? '₹' : 'U';
  msgDiv.appendChild(avatar);

  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-content';

  // Agent Reasoning Accordion
  if (role === 'bot' && reasoningSteps && reasoningSteps.length > 0) {
    const reasonBox = document.createElement('div');
    reasonBox.className = 'reasoning-box';

    const header = document.createElement('div');
    header.className = 'reasoning-header';
    header.innerHTML = `<span>🧠 Agent Reasoning (${reasoningSteps.length} tools executed)</span><span class="chevron">▼</span>`;

    const details = document.createElement('div');
    details.className = 'reasoning-details';
    details.style.display = 'none';

    reasoningSteps.forEach(step => {
      const stepItem = document.createElement('div');
      stepItem.className = 'reasoning-step-item';
      stepItem.innerHTML = `
        <div><span class="step-badge">${step.action}</span></div>
        <div style="color:#94a3b8;font-size:11px;">Args: ${JSON.stringify(step.args || {})}</div>
        <div style="color:#38bdf8;font-size:11px;">Result: ${JSON.stringify(step.result || step.error || 'ok')}</div>
      `;
      details.appendChild(stepItem);
    });

    header.addEventListener('click', () => {
      const isVisible = details.style.display !== 'none';
      details.style.display = isVisible ? 'none' : 'flex';
      header.querySelector('.chevron').textContent = isVisible ? '▼' : '▲';
    });

    reasonBox.appendChild(header);
    reasonBox.appendChild(details);
    contentDiv.appendChild(reasonBox);
  }

  // Text bubble
  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';
  bubble.innerHTML = renderMarkdown(text);
  contentDiv.appendChild(bubble);

  // Transaction Saved Action Card
  if (role === 'bot' && transactionSaved && transaction) {
    const card = document.createElement('div');
    card.className = 'txn-card';
    card.innerHTML = `
      <div class="txn-card-left">
        <div class="txn-card-icon">✓</div>
        <div>
          <div class="txn-card-title">₹${parseFloat(transaction.amount).toLocaleString('en-IN')} ${transaction.type}</div>
          <div class="txn-card-sub">${transaction.category.toUpperCase()} · ${transaction.date || 'Today'}</div>
        </div>
      </div>
      <div style="display:flex;gap:6px;align-items:center;">
        <a href="/dashboard" class="btn-undo-txn" style="color:var(--accent);">Dashboard →</a>
        ${transaction.id ? `<button type="button" class="btn-undo-txn btn-undo-action" data-id="${transaction.id}">Undo</button>` : ''}
      </div>
    `;

    const undoBtn = card.querySelector('.btn-undo-action');
    if (undoBtn) {
      undoBtn.addEventListener('click', async () => {
        try {
          const res = await fetch(`/api/transactions/${transaction.id}`, { method: 'DELETE' });
          if (res.ok) {
            card.innerHTML = `<span style="color:var(--text-muted);font-size:12px;">✓ Transaction cancelled</span>`;
            showToast('Transaction undone.', 'success');
          }
        } catch (e) {
          showToast('Could not undo transaction.', 'error');
        }
      });
    }

    contentDiv.appendChild(card);
  }

  // Message Footer Tools (Copy + Speak)
  if (role === 'bot') {
    const tools = document.createElement('div');
    tools.className = 'message-tools';

    const copyBtn = document.createElement('button');
    copyBtn.className = 'btn-msg-tool';
    copyBtn.title = 'Copy response';
    copyBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`;
    copyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(text);
      showToast('Copied to clipboard!', 'info');
    });

    const speakBtn = document.createElement('button');
    speakBtn.className = 'btn-msg-tool';
    speakBtn.title = 'Read aloud';
    speakBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>`;
    speakBtn.addEventListener('click', () => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const clean = text.replace(/[*#`_]/g, '');
        const utter = new SpeechSynthesisUtterance(clean);
        utter.rate = 1.05;
        window.speechSynthesis.speak(utter);
      } else {
        showToast('Text-to-speech not supported in this browser.', 'error');
      }
    });

    tools.appendChild(copyBtn);
    tools.appendChild(speakBtn);
    contentDiv.appendChild(tools);
  }

  msgDiv.appendChild(contentDiv);
  messages.appendChild(msgDiv);
  scrollToBottom();
}

function setLoading(loading) {
  sendBtn.disabled = loading;
  input.disabled = loading;
  typingIndicator.classList.toggle('hidden', !loading);
  if (loading) scrollToBottom();
}

// ─────────────────────────────────────────
// Form Submit & Receipt Upload Handling
// ─────────────────────────────────────────

async function handleSendMessage(text) {
  if (!text && !pendingFile) return;

  // If receipt file is attached, run Vision OCR first
  if (pendingFile) {
    const file = pendingFile;
    clearAttachment();

    appendMessage('user', `Uploaded receipt: ${file.name}`);
    setLoading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/scan-receipt', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error('Receipt scanning failed');
      const data = await res.json();
      const ext = data.extracted;

      appendMessage('bot', `🧾 Scanned **${ext.merchant}**\n\n- **Amount:** ₹${ext.total_amount.toLocaleString('en-IN')}\n- **Category:** ${ext.category}\n- **Date:** ${ext.date}\n- **Items:** ${ext.line_items.join(', ') || 'N/A'}\n\n*${ext.summary}*`, {
        transactionSaved: true,
        transaction: {
          id: data.transaction_id,
          amount: ext.total_amount,
          type: ext.type,
          category: ext.category,
          date: ext.date,
        }
      });
      showToast('Receipt logged automatically!', 'success');
    } catch (err) {
      appendMessage('bot', '⚠ Failed to extract receipt details. Please verify the image is sharp.');
      showToast('Receipt scan failed', 'error');
    } finally {
      setLoading(false);
      input.focus();
    }
    return;
  }

  // Regular Agentic Chat
  appendMessage('user', text);
  input.value = '';
  setLoading(true);

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });

    if (response.status === 401) {
      window.location.href = '/login';
      return;
    }

    const data = await response.json();
    appendMessage('bot', data.reply, {
      reasoningSteps: data.reasoning_steps,
      transactionSaved: data.transaction_saved,
      transaction: data.transaction,
    });

    if (data.transaction_saved) {
      showToast('Transaction logged!', 'success');
    }
    if (data.budget_updated) {
      showToast(`Budget for ${data.budget.category} updated!`, 'info');
    }

  } catch (err) {
    appendMessage('bot', '⚠ Connection error with AI agent. Please try again.');
    showToast('Failed to connect to agent', 'error');
  } finally {
    setLoading(false);
    input.focus();
  }
}

form.addEventListener('submit', (e) => {
  e.preventDefault();
  handleSendMessage(input.value.trim());
});

// ─────────────────────────────────────────
// Prompt Chips
// ─────────────────────────────────────────

if (promptChips) {
  promptChips.addEventListener('click', (e) => {
    const chip = e.target.closest('.chip');
    if (chip) {
      const prompt = chip.getAttribute('data-prompt');
      if (prompt) {
        input.value = prompt;
        form.dispatchEvent(new Event('submit'));
      }
    }
  });
}

// ─────────────────────────────────────────
// Receipt Upload Attachment
// ─────────────────────────────────────────

btnAttachReceipt.addEventListener('click', () => {
  receiptFileInput.click();
});

receiptFileInput.addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (!file) return;

  pendingFile = file;
  previewName.textContent = file.name;

  const reader = new FileReader();
  reader.onload = (ev) => {
    previewImg.src = ev.target.result;
    attachmentPreview.classList.add('active');
    input.placeholder = `Press Send to scan "${file.name}" with Gemini Vision...`;
  };
  reader.readAsDataURL(file);
});

function clearAttachment() {
  pendingFile = null;
  receiptFileInput.value = '';
  previewImg.src = '';
  attachmentPreview.classList.remove('active');
  input.placeholder = 'Tell FinBuddy an expense, ask for budget insights, or simulate wealth...';
}

btnRemoveAttach.addEventListener('click', clearAttachment);

// ─────────────────────────────────────────
// Voice Recognition (Speech to Text)
// ─────────────────────────────────────────

if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRec();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = 'en-IN';

  recognition.onstart = () => {
    isRecording = true;
    btnVoiceInput.classList.add('recording');
    showToast('Listening... Speak now', 'info');
  };

  recognition.onresult = (evt) => {
    const transcript = evt.results[0][0].transcript;
    input.value = transcript;
    showToast(`Heard: "${transcript}"`, 'info');
  };

  recognition.onerror = () => {
    isRecording = false;
    btnVoiceInput.classList.remove('recording');
    showToast('Voice input error. Please try again.', 'error');
  };

  recognition.onend = () => {
    isRecording = false;
    btnVoiceInput.classList.remove('recording');
  };

  btnVoiceInput.addEventListener('click', () => {
    if (isRecording) {
      recognition.stop();
    } else {
      recognition.start();
    }
  });
} else {
  btnVoiceInput.style.display = 'none';
}

// ─────────────────────────────────────────
// Clear & Export Chat History
// ─────────────────────────────────────────

btnClearChat.addEventListener('click', async () => {
  if (!confirm('Clear recent conversation memory with FinBuddy?')) return;
  try {
    const res = await fetch('/api/chat/clear', { method: 'DELETE' });
    if (res.ok) {
      messages.innerHTML = `
        <div class="message bot">
          <div class="message-avatar">₹</div>
          <div class="message-content">
            <div class="message-bubble">
              Session memory cleared! What would you like to review or track next?
            </div>
          </div>
        </div>
      `;
      showToast('Conversation memory reset.', 'info');
    }
  } catch (err) {
    showToast('Failed to clear memory.', 'error');
  }
});

btnExportChat.addEventListener('click', () => {
  const bubbles = messages.querySelectorAll('.message');
  let md = `# FinBuddy Conversation Export - ${new Date().toLocaleDateString()}\n\n`;

  bubbles.forEach(b => {
    const isBot = b.classList.contains('bot');
    const text = b.querySelector('.message-bubble')?.innerText || '';
    md += `### ${isBot ? 'FinBuddy AI' : 'User'}\n${text}\n\n`;
  });

  const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `finbuddy_chat_${new Date().toISOString().slice(0, 10)}.md`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('Chat exported!', 'success');
});

// ─────────────────────────────────────────
// Mobile Sidebar Toggle
// ─────────────────────────────────────────

if (mobileMenuBtn && sidebar) {
  mobileMenuBtn.addEventListener('click', () => {
    sidebar.classList.toggle('open');
  });

  // Close sidebar when clicking outside on mobile
  document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768 && !sidebar.contains(e.target) && !mobileMenuBtn.contains(e.target)) {
      sidebar.classList.remove('open');
    }
  });
}

// Auto-focus input on load
input.focus();
