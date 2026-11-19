/**
 * Synaptix — Frontend Application Script (Milestone 3 — Multi-Agent System)
 * Handles navigation, telemetry polling, agent status chips, and real-time agent delegation.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const navItems = document.querySelectorAll('.nav-item');
  const tabPanes = document.querySelectorAll('.tab-pane');
  const currentTabTitle = document.getElementById('currentTabTitle');
  const currentTabDesc = document.getElementById('currentTabDesc');
  const statusText = document.getElementById('statusText');
  const serverStatusBadge = document.getElementById('serverStatusBadge');

  // Agent chips
  const agentChips = {
    Coordinator: document.querySelector('.agent-chip[title*="Coordinator"]'),
    TaskAgent: document.querySelector('.agent-chip[title*="Task Agent"]'),
    NotesAgent: document.querySelector('.agent-chip[title*="Notes Agent"]'),
    CalendarAgent: document.querySelector('.agent-chip[title*="Calendar Agent"]'),
    SmartDayPlannerAgent: document.querySelector('.agent-chip[title*="Planner Agent"]'),
  };

  // Telemetry elements
  const telStatus = document.getElementById('telStatus');
  const telUptime = document.getElementById('telUptime');
  const telPython = document.getElementById('telPython');
  const telEnv = document.getElementById('telEnv');
  const telDailyLimit = document.getElementById('telDailyLimit');
  const telRequestsMade = document.getElementById('telRequestsMade');
  const telRemaining = document.getElementById('telRemaining');
  const telTokens = document.getElementById('telTokens');
  const telGemini = document.getElementById('telGemini');
  const telFirestore = document.getElementById('telFirestore');
  const telCalendar = document.getElementById('telCalendar');
  const telWeather = document.getElementById('telWeather');

  // Chat elements
  const chatMessages = document.getElementById('chatMessages');
  const chatForm = document.getElementById('chatForm');
  const userInput = document.getElementById('userInput');
  const chips = document.querySelectorAll('.chip');
  const sendBtn = document.getElementById('sendBtn');

  // Session state
  let currentSessionId = null;
  const conversationHistory = [];

  const tabMetadata = {
    chat: {
      title: 'AI Multi-Agent Coordinator',
      desc: 'Orchestrating TaskAgent, NotesAgent, CalendarAgent, and SmartDayPlannerAgent.',
    },
    tasks: {
      title: 'Tasks Management (TaskAgent)',
      desc: 'View, track, and manage priorities, due dates, and pending items.',
    },
    notes: {
      title: 'Personal & Project Notes (NotesAgent)',
      desc: 'Contextual notes, ideas, and meeting summaries with semantic search.',
    },
    calendar: {
      title: 'Google Calendar Schedule (CalendarAgent)',
      desc: 'Real-time calendar events, meeting detection, and conflict prevention via MCP.',
    },
    planner: {
      title: 'Smart Day Planner (PlannerAgent)',
      desc: 'AI-generated daily schedules balancing your tasks, calendar events, and weather.',
    },
    telemetry: {
      title: '₹0 Budget & System Telemetry',
      desc: 'Live backend telemetry, uptime monitor, and strict zero-cost safety limits.',
    },
  };

  // 1. Navigation Tab Switching
  navItems.forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');

      navItems.forEach((item) => item.classList.remove('active'));
      tabPanes.forEach((pane) => pane.classList.remove('active'));

      btn.classList.add('active');
      const targetPane = document.getElementById(`tab-${targetTab}`);
      if (targetPane) targetPane.classList.add('active');

      if (tabMetadata[targetTab]) {
        currentTabTitle.textContent = tabMetadata[targetTab].title;
        currentTabDesc.textContent = tabMetadata[targetTab].desc;
      }
    });
  });

  // 2. Health & Telemetry Polling
  async function fetchHealthTelemetry() {
    try {
      const response = await fetch('/api/health');
      if (!response.ok) throw new Error('Backend returned non-200');

      const data = await response.json();

      // Update sidebar status
      statusText.textContent = 'Server Online (200 OK)';
      const indicator = serverStatusBadge.querySelector('.status-indicator');
      indicator.className = 'status-indicator online';

      // Update telemetry panel
      if (telStatus) telStatus.textContent = data.status.toUpperCase();
      if (telUptime) telUptime.textContent = `${data.uptime_seconds}s`;
      if (telPython) telPython.textContent = data.runtime.python_version;
      if (telEnv) telEnv.textContent = data.environment;

      if (data.budget_telemetry) {
        const b = data.budget_telemetry;
        if (telDailyLimit) telDailyLimit.textContent = b.daily_request_limit;
        if (telRequestsMade) telRequestsMade.textContent = b.total_llm_requests;
        if (telRemaining) telRemaining.textContent = b.remaining_daily_requests;
        if (telTokens) telTokens.textContent = b.total_tokens_consumed;
      }

      if (data.integrations_status) {
        const i = data.integrations_status;
        if (telGemini) telGemini.textContent = i.gemini_configured ? 'Google ADK + Gemini 2.5 Flash ✅' : 'Google ADK Active (₹0 Local Mode) ✅';
        if (telFirestore) telFirestore.textContent = i.firebase_configured ? 'Connected ✅' : 'Milestone 4 (Pending)';
        if (telCalendar) telCalendar.textContent = i.google_calendar_configured ? 'Active ✅' : 'Milestone 5 (Pending)';
        if (telWeather) telWeather.textContent = i.weather_configured ? 'Active ✅' : 'Milestone 6 (Pending)';
      }
    } catch (err) {
      statusText.textContent = 'Backend Offline';
      const indicator = serverStatusBadge.querySelector('.status-indicator');
      indicator.className = 'status-indicator offline';
      if (telStatus) {
        telStatus.textContent = 'OFFLINE';
        telStatus.className = '';
        telStatus.style.color = '#ef4444';
      }
    }
  }

  // Poll health immediately and every 10 seconds
  fetchHealthTelemetry();
  setInterval(fetchHealthTelemetry, 10000);

  // 3. Highlight active agent chip in UI
  function highlightAgent(agentName) {
    // Reset all chips to standby
    Object.values(agentChips).forEach(chip => {
      if (chip) {
        chip.className = 'agent-chip standby';
      }
    });

    // Always keep Coordinator visible
    if (agentChips.Coordinator) {
      agentChips.Coordinator.className = 'agent-chip active';
    }

    // Highlight specialized agent
    if (agentName && agentChips[agentName]) {
      agentChips[agentName].className = 'agent-chip active';
    }
  }

  // 4. Formatting helper for Markdown
  function formatMarkdown(text) {
    if (!text) return '';
    let html = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Code blocks ```code```
    html = html.replace(/```([a-z]*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    // Inline code `code`
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Bold **text**
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    // Italic *text*
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    // Markdown links [title](url)
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    // Line breaks to <p> and <br>
    return html.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
  }

  // 5. Chat UI Helper Functions
  function appendMessage(sender, text, isUser = false, agentBadge = null) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${isUser ? 'user' : 'assistant'}`;

    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const formattedContent = formatMarkdown(text);
    const badgeHtml = agentBadge ? `<span style="display:inline-block; margin-left:8px; font-size:0.72rem; padding:2px 8px; border-radius:12px; background:rgba(99,102,241,0.25); color:#a5b4fc;">⚡ Delegated to: ${agentBadge}</span>` : '';

    msgDiv.innerHTML = `
      <div class="message-avatar">${isUser ? '👤' : '🧠'}</div>
      <div class="message-body">
        <div class="message-sender">${isUser ? 'You' : sender} ${badgeHtml}</div>
        <div class="message-text"><p>${formattedContent}</p></div>
        <div class="message-time">${now}</div>
      </div>
    `;

    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msgDiv;
  }

  function appendLoadingMessage() {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message assistant loading-msg';
    msgDiv.innerHTML = `
      <div class="message-avatar">🧠</div>
      <div class="message-body">
        <div class="message-sender">Synaptix Coordinator</div>
        <div class="message-text"><p><em>Analyzing intent & delegating to specialist agent...</em> ⚡</p></div>
      </div>
    `;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msgDiv;
  }

  // 6. Handle Chat Submission to /api/chat
  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = userInput.value.trim();
    if (!query) return;

    // Append user message
    appendMessage('You', query, true);
    userInput.value = '';
    userInput.disabled = true;
    sendBtn.disabled = true;

    // Append loading placeholder
    const loadingElem = appendLoadingMessage();

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: query,
          session_id: currentSessionId,
          conversation_history: conversationHistory.slice(-6),
        }),
      });

      // Remove loading indicator
      loadingElem.remove();

      if (response.status === 429) {
        const errData = await response.json();
        const errDetail = errData.detail || {};
        appendMessage(
          'Synaptix Guard',
          `⛔ **₹0 Budget Protection Triggered (HTTP 429)**\n\n${errDetail.message || 'Daily limit reached.'}`,
          false
        );
        return;
      }

      if (!response.ok) {
        const errData = await response.json();
        appendMessage(
          'Synaptix Error',
          `⚠️ Server responded with error (${response.status}): ${JSON.stringify(errData.detail || errData)}`,
          false
        );
        return;
      }

      const data = await response.json();
      currentSessionId = data.session_id || currentSessionId;

      const orch = data.orchestration || {};
      const targetAgent = orch.activated_agent || (orch.activated_agents && orch.activated_agents[orch.activated_agents.length - 1]) || "Coordinator";

      // Dynamically highlight active agent in header
      highlightAgent(targetAgent);

      // Append assistant reply with agent badge
      appendMessage('Synaptix AI', data.reply, false, targetAgent);

      // Save to conversation history
      conversationHistory.push({ role: 'user', content: query });
      conversationHistory.push({ role: 'model', content: data.reply });

      // Refresh telemetry
      fetchHealthTelemetry();

    } catch (err) {
      loadingElem.remove();
      appendMessage('Synaptix Error', `⚠️ Network error: Could not reach backend server (${err.message})`, false);
    } finally {
      userInput.disabled = false;
      sendBtn.disabled = false;
      userInput.focus();
    }
  });

  // Handle quick chip clicks
  chips.forEach((chip) => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      userInput.value = prompt;
      chatForm.dispatchEvent(new Event('submit'));
    });
  });

  // Auto-resize textarea
  userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event('submit'));
    }
  });
});
