/**
 * GourmetAI - Interactive Frontend Application Logic
 */

// Food dish emoji map
const DISH_ICONS = {
  burger: '🍔',
  cheeseburger: '🧀',
  pizza: '🍕',
  pasta: '🍝',
  sandwich: '🥪',
  fries: '🍟',
  salad: '🥗',
  sushi: '🍣',
  taco: '🌮',
};

// Global state
let currentThreadId = null;
let currentAgentState = null;

// DOM Elements
const menuListEl = document.getElementById('menuList');
const menuCountBadge = document.getElementById('menuCountBadge');
const chatFeedEl = document.getElementById('chatFeed');
const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const displayThreadId = document.getElementById('displayThreadId');
const resetSessionBtn = document.getElementById('resetSessionBtn');
const contextActionsEl = document.getElementById('contextActions');
const agentStatusPill = document.getElementById('agentStatusPill');
const agentStatusText = document.getElementById('agentStatusText');

// Stepper Elements
const stepIntake = document.getElementById('stepIntake');
const stepMenu = document.getElementById('stepMenu');
const stepCook = document.getElementById('stepCook');
const stepServe = document.getElementById('stepServe');
const stepComplete = document.getElementById('stepComplete');
const nodeStageBadge = document.getElementById('nodeStageBadge');

// Retry counters
const orderRetryVal = document.getElementById('orderRetryVal');
const orderRetryBar = document.getElementById('orderRetryBar');
const cookRetryVal = document.getElementById('cookRetryVal');
const cookRetryBar = document.getElementById('cookRetryBar');
const serveRetryVal = document.getElementById('serveRetryVal');
const serveRetryBar = document.getElementById('serveRetryBar');

// State inspector
const stateStatusCode = document.getElementById('stateStatusCode');
const stateDish = document.getElementById('stateDish');
const stateReqQty = document.getElementById('stateReqQty');
const stateAvailQty = document.getElementById('stateAvailQty');
const stateFinalResult = document.getElementById('stateFinalResult');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  initSession();
  loadMenu();
  setupEventListeners();
});

function initSession() {
  currentThreadId = 'session_' + Math.random().toString(36).substring(2, 9);
  displayThreadId.textContent = currentThreadId;
  chatFeedEl.innerHTML = '';
  resetStepper();

  // Welcome greeting
  appendMessage(
    'assistant',
    '👋 Welcome to GourmetAI! What would you like to order today? (e.g. "I want 2 burgers" or "1 pizza").'
  );
}

function setupEventListeners() {
  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = userInput.value.trim();
    if (!text) return;
    sendMessage(text);
    userInput.value = '';
  });

  resetSessionBtn.addEventListener('click', () => {
    initSession();
  });

  // Quick sample chips
  document.querySelectorAll('.sample-chips .chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      if (prompt) {
        sendMessage(prompt);
      }
    });
  });
}

// Fetch and render menu
async function loadMenu() {
  try {
    const res = await fetch('/api/menu');
    const data = await res.json();
    const items = data.menu || [];

    menuCountBadge.textContent = `${items.length} Items`;
    menuListEl.innerHTML = '';

    items.forEach((item) => {
      const card = document.createElement('div');
      card.className = 'menu-card';

      const icon = DISH_ICONS[item.dish.toLowerCase()] || '🍲';
      let tagClass = 'in-stock';
      let tagText = `${item.stock} in stock`;

      if (item.status === 'out_of_stock') {
        tagClass = 'out-of-stock';
        tagText = 'Out of Stock';
      } else if (item.status === 'low_stock') {
        tagClass = 'low-stock';
        tagText = `Only ${item.stock} left`;
      }

      card.innerHTML = `
        <div class="menu-item-info">
          <span class="dish-icon">${icon}</span>
          <div>
            <div class="dish-name">${item.dish}</div>
          </div>
        </div>
        <span class="stock-tag ${tagClass}">${tagText}</span>
      `;

      card.addEventListener('click', () => {
        userInput.value = `I want 2 ${item.dish}s`;
        userInput.focus();
      });

      menuListEl.appendChild(card);
    });
  } catch (err) {
    console.error('Failed to load menu:', err);
    menuListEl.innerHTML = '<div class="loading-spinner">Could not load menu</div>';
  }
}

// Send message to backend LangGraph agent
async function sendMessage(text) {
  appendMessage('user', text);
  hideContextActions();
  showTypingIndicator();
  setAgentBusy(true);

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        thread_id: currentThreadId,
      }),
    });

    const data = await res.json();
    removeTypingIndicator();
    setAgentBusy(false);

    if (data.messages && data.messages.length > 0) {
      // Find the last assistant message
      for (let i = data.messages.length - 1; i >= 0; i--) {
        if (data.messages[i].role === 'assistant') {
          appendMessage('assistant', data.messages[i].content);
          break;
        }
      }
    }

    updateUIState(data);
  } catch (err) {
    removeTypingIndicator();
    setAgentBusy(false);
    appendMessage('assistant', '⚠️ Connection error with the LangGraph agent.');
    console.error(err);
  }
}

// Append message bubble
function appendMessage(role, text) {
  const bubble = document.createElement('div');
  bubble.className = `message-bubble ${role}`;

  const avatar = role === 'user' ? '👤' : '🤖';

  bubble.innerHTML = `
    <div class="msg-avatar">${avatar}</div>
    <div class="msg-content">${escapeHTML(text)}</div>
  `;

  chatFeedEl.appendChild(bubble);
  chatFeedEl.scrollTop = chatFeedEl.scrollHeight;
}

function showTypingIndicator() {
  const typing = document.createElement('div');
  typing.id = 'typingIndicator';
  typing.className = 'message-bubble assistant';
  typing.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-content" style="font-style: italic; color: var(--text-dim);">
      Agent processing with LangGraph...
    </div>
  `;
  chatFeedEl.appendChild(typing);
  chatFeedEl.scrollTop = chatFeedEl.scrollHeight;
}

function removeTypingIndicator() {
  const typing = document.getElementById('typingIndicator');
  if (typing) typing.remove();
}

function setAgentBusy(busy) {
  if (busy) {
    agentStatusText.textContent = 'Processing...';
    sendBtn.disabled = true;
    agentStatusPill.style.borderColor = 'var(--accent-gold)';
  } else {
    agentStatusText.textContent = 'Agent Ready';
    sendBtn.disabled = false;
    agentStatusPill.style.borderColor = 'rgba(16, 185, 129, 0.3)';
  }
}

// Update workflow stepper, retry bars, and state inspector
function updateUIState(data) {
  currentAgentState = data;
  const status = data.status;

  // State Inspector
  stateStatusCode.textContent = (status || 'UNKNOWN').toUpperCase();
  stateDish.textContent = data.dish_name || '-';
  stateReqQty.textContent = data.required_quantity != null ? data.required_quantity : '-';
  stateAvailQty.textContent = data.available_quantity != null ? data.available_quantity : '-';
  stateFinalResult.textContent = data.final_result || 'In progress';

  // Retry Counters
  const oCount = data.order_retry_count != null ? data.order_retry_count : 3;
  const cCount = data.cook_retry_count != null ? data.cook_retry_count : 2;
  const sCount = data.serve_retry_count != null ? data.serve_retry_count : 2;

  orderRetryVal.textContent = `${oCount} / 3`;
  orderRetryBar.style.width = `${(oCount / 3) * 100}%`;

  cookRetryVal.textContent = `${cCount} / 2`;
  cookRetryBar.style.width = `${(cCount / 2) * 100}%`;

  serveRetryVal.textContent = `${sCount} / 2`;
  serveRetryBar.style.width = `${(sCount / 2) * 100}%`;

  // Update Stepper highlighting
  resetStepper();

  if (status === 'order_extracted' || status === 'pending') {
    setStepActive(stepIntake, 'Intake');
  } else if (status === 'confirmed') {
    setStepCompleted(stepIntake);
    setStepCompleted(stepMenu);
    setStepActive(stepCook, 'Cooking');
  } else if (status === 'partial' || status === 'unavailable') {
    setStepCompleted(stepIntake);
    setStepActive(stepMenu, status.toUpperCase());
    showContextualOptions(status, data);
  } else if (status === 'ready') {
    setStepCompleted(stepIntake);
    setStepCompleted(stepMenu);
    setStepCompleted(stepCook);
    setStepActive(stepServe, 'Serving');
  } else if (status === 'completed') {
    setStepCompleted(stepIntake);
    setStepCompleted(stepMenu);
    setStepCompleted(stepCook);
    setStepCompleted(stepServe);
    setStepCompleted(stepComplete);
    nodeStageBadge.textContent = 'Completed 🎉';
    nodeStageBadge.style.color = 'var(--accent-emerald)';
  } else if (status === 'cancelled' || status === 'failed' || status === 'rejected_unrelated') {
    setStepActive(stepComplete, 'Ended');
    nodeStageBadge.textContent = status === 'rejected_unrelated' ? 'Rejected' : 'Cancelled/Failed ❌';
    nodeStageBadge.style.color = 'var(--accent-crimson)';
  }
}

function resetStepper() {
  [stepIntake, stepMenu, stepCook, stepServe, stepComplete].forEach((s) => {
    s.classList.remove('active', 'completed');
  });
  nodeStageBadge.textContent = 'Idle';
  nodeStageBadge.style.color = 'var(--accent-gold)';
}

function setStepActive(stepEl, label) {
  stepEl.classList.add('active');
  nodeStageBadge.textContent = label;
}

function setStepCompleted(stepEl) {
  stepEl.classList.add('completed');
}

// Show dynamic context action chips based on state
function showContextualOptions(status, data) {
  contextActionsEl.innerHTML = '';
  contextActionsEl.style.display = 'flex';

  if (status === 'partial') {
    const avail = data.available_quantity || 1;
    const dish = data.dish_name || 'dish';

    const btnAccept = document.createElement('button');
    btnAccept.className = 'btn-action';
    btnAccept.textContent = `✅ Proceed with ${avail} ${dish}`;
    btnAccept.addEventListener('click', () => sendMessage(`Yes, proceed with ${avail}`));

    const btnNew = document.createElement('button');
    btnNew.className = 'btn-action';
    btnNew.textContent = '🔄 Order Pizza instead';
    btnNew.addEventListener('click', () => sendMessage('I want 2 pizzas'));

    const btnCancel = document.createElement('button');
    btnCancel.className = 'btn-action';
    btnCancel.textContent = '❌ Cancel Order';
    btnCancel.addEventListener('click', () => sendMessage('cancel'));

    contextActionsEl.appendChild(btnAccept);
    contextActionsEl.appendChild(btnNew);
    contextActionsEl.appendChild(btnCancel);
  } else if (status === 'unavailable') {
    const btnNew = document.createElement('button');
    btnNew.className = 'btn-action';
    btnNew.textContent = '🔄 Order 2 Burgers instead';
    btnNew.addEventListener('click', () => sendMessage('I want 2 burgers'));

    const btnCancel = document.createElement('button');
    btnCancel.className = 'btn-action';
    btnCancel.textContent = '❌ Cancel Order';
    btnCancel.addEventListener('click', () => sendMessage('cancel'));

    contextActionsEl.appendChild(btnNew);
    contextActionsEl.appendChild(btnCancel);
  }
}

function hideContextActions() {
  contextActionsEl.style.display = 'none';
  contextActionsEl.innerHTML = '';
}

function escapeHTML(str) {
  return str.replace(/[&<>'"]/g, 
    tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag)
  );
}
