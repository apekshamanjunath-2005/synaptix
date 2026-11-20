/**
 * Synaptix — Frontend Application Script
 * Minimalist Dark Aura Aesthetic & Multi-Agent Orchestration
 */

document.addEventListener('DOMContentLoaded', () => {
  // Navigation elements
  const navItems = document.querySelectorAll('.nav-item');
  const tabPanes = document.querySelectorAll('.tab-pane');
  const currentTabTitle = document.getElementById('currentTabTitle');
  const currentTabDesc = document.getElementById('currentTabDesc');
  const sidebar = document.getElementById('sidebar');
  const sidebarToggle = document.getElementById('sidebarToggle');
  const mobileSidebarToggle = document.getElementById('mobileSidebarToggle');

  // Agent chips
  const agentChips = {
    Coordinator: document.querySelector('.agent-chip[title*="Coordinator"]'),
    TaskAgent: document.querySelector('.agent-chip[title*="Task Agent"]'),
    NotesAgent: document.querySelector('.agent-chip[title*="Notes Agent"]'),
    CalendarAgent: document.querySelector('.agent-chip[title*="Calendar Agent"]'),
    GmailAgent: document.querySelector('.agent-chip[title*="Gmail Agent"]'),
    SmartDayPlannerAgent: document.querySelector('.agent-chip[title*="Planner Agent"]'),
  };

  // Telemetry elements (Background compatibility)
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
  const statusText = document.getElementById('statusText');
  const serverStatusBadge = document.getElementById('serverStatusBadge');

  // Chat elements
  const chatContainer = document.getElementById('chatContainer');
  const chatMessages = document.getElementById('chatMessages');
  const chatForm = document.getElementById('chatForm');
  const userInput = document.getElementById('userInput');
  const auraGlowWrapper = document.getElementById('auraGlowWrapper');
  const modeSelect = document.getElementById('modeSelect');
  const chips = document.querySelectorAll('.chip[data-prompt]');
  const sendBtn = document.getElementById('sendBtn');
  const clearChatBtn = document.getElementById('clearChatBtn');
  const copyPlanBtn = document.getElementById('copyPlanBtn');
  const toastContainer = document.getElementById('toastContainer');

  // Session state
  let currentSessionId = null;
  const conversationHistory = [];
  let latestPlanMarkdown = '';

  // ══════════════════════════════════════════════════════════════════════════
  // HELPER: HTML Escaping
  // ══════════════════════════════════════════════════════════════════════════
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 1. TOAST NOTIFICATION SYSTEM
  // ══════════════════════════════════════════════════════════════════════════
  function showToast(message, type = 'info', duration = 3500) {
    if (!toastContainer) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icons = {
      success: '✓',
      error: '✕',
      info: '✨',
      warning: '⚠️'
    };
    toast.innerHTML = `<span style="font-weight:700;">${icons[type] || '•'}</span> <span>${message}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('fade-out');
      setTimeout(() => toast.remove(), 320);
    }, duration);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 2. RECENT CHATS SLIDE-OVER DRAWER & NAVIGATION
  // ══════════════════════════════════════════════════════════════════════════
  const historyDrawerBtn = document.getElementById('historyDrawerBtn');
  const navbarHistoryBtn = document.getElementById('navbarHistoryBtn');
  const sessionsDrawerOverlay = document.getElementById('sessionsDrawerOverlay');
  const closeSessionsDrawer = document.getElementById('closeSessionsDrawer');

  function openSessionsDrawerFunc() {
    if (sidebar) sidebar.classList.add('drawer-open');
    if (sessionsDrawerOverlay) sessionsDrawerOverlay.classList.add('active');
  }

  function closeSessionsDrawerFunc() {
    if (sidebar) sidebar.classList.remove('drawer-open');
    if (sessionsDrawerOverlay) sessionsDrawerOverlay.classList.remove('active');
  }

  if (historyDrawerBtn) historyDrawerBtn.addEventListener('click', openSessionsDrawerFunc);
  if (navbarHistoryBtn) navbarHistoryBtn.addEventListener('click', openSessionsDrawerFunc);
  if (closeSessionsDrawer) closeSessionsDrawer.addEventListener('click', closeSessionsDrawerFunc);
  if (sessionsDrawerOverlay) sessionsDrawerOverlay.addEventListener('click', closeSessionsDrawerFunc);

  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', () => {
      if (sidebar.classList.contains('drawer-open')) {
        closeSessionsDrawerFunc();
      } else {
        openSessionsDrawerFunc();
      }
    });
  }

  if (mobileSidebarToggle && sidebar) {
    mobileSidebarToggle.addEventListener('click', () => {
      if (sidebar.classList.contains('drawer-open')) {
        closeSessionsDrawerFunc();
      } else {
        openSessionsDrawerFunc();
      }
    });
  }

  // Close drawer on escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeSessionsDrawerFunc();
    }
  });

  // ══════════════════════════════════════════════════════════════════════════
  // 3. TAB NAVIGATION
  // ══════════════════════════════════════════════════════════════════════════
  const tabMetadata = {
    chat: {
      title: 'AI Assistant',
      desc: 'Natural language coordinator orchestrating tasks, calendar, email, and planning.',
    },
    tasks: {
      title: 'Tasks',
      desc: 'Manage priorities, deadlines, and pending action items in Firestore.',
    },
    notes: {
      title: 'Notes',
      desc: 'Capture thoughts, meeting summaries, and search stored notes.',
    },
    calendar: {
      title: 'Calendar',
      desc: 'Schedule commitments and check timeslot availability via Google Calendar MCP.',
    },
    gmail: {
      title: 'Gmail Drafts',
      desc: 'Human-in-the-Loop email system: review and approve drafts before sending.',
    },
    planner: {
      title: 'Smart Planner',
      desc: 'Daily schedule synthesis balancing pending tasks, calendar events, and weather.',
    },
    telemetry: {
      title: 'Telemetry',
      desc: 'Backend health monitor.',
    },
  };

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

      if (window.innerWidth <= 768 && sidebar) {
        sidebar.classList.remove('mobile-open');
      }

      if (targetTab === 'tasks') loadTasks();
      if (targetTab === 'notes') loadNotes();
      if (targetTab === 'calendar') {
        switchCalendarView('upcoming');
        renderCalendarMonth(calCurrentYear, calCurrentMonth);
        fetchMonthIndicators(calCurrentYear, calCurrentMonth);
        loadAllCalendarData();
      }
      if (targetTab === 'gmail') loadDrafts();
      if (targetTab === 'planner') {
        loadWeather();
        loadTimetable();
        loadUserTimetable();
      }
    });
  });

  // ══════════════════════════════════════════════════════════════════════════
  // 4. HEALTH TELEMETRY POLLING (Silent Background Safeguard)
  // ══════════════════════════════════════════════════════════════════════════
  async function fetchHealthTelemetry() {
    try {
      const response = await fetch('/api/health');
      if (!response.ok) throw new Error('Backend returned non-200');

      const data = await response.json();

      if (statusText) statusText.textContent = 'Server Online (200 OK)';
      if (serverStatusBadge) {
        const ind = serverStatusBadge.querySelector('.status-indicator');
        if (ind) ind.className = 'status-indicator online';
      }

      if (telStatus) telStatus.textContent = data.status.toUpperCase();
      if (telUptime) telUptime.textContent = `${data.uptime_seconds}s`;
      if (telPython) telPython.textContent = data.runtime ? data.runtime.python_version : '-';
      if (telEnv) telEnv.textContent = data.environment || 'development';

      if (data.budget_telemetry) {
        const b = data.budget_telemetry;
        if (telDailyLimit) telDailyLimit.textContent = b.daily_request_limit;
        if (telRequestsMade) telRequestsMade.textContent = b.total_llm_requests;
        if (telRemaining) telRemaining.textContent = b.remaining_daily_requests;
        if (telTokens) telTokens.textContent = b.total_tokens_consumed;
      }
    } catch (err) {
      if (statusText) statusText.textContent = 'Backend Offline';
      if (serverStatusBadge) {
        const ind = serverStatusBadge.querySelector('.status-indicator');
        if (ind) ind.className = 'status-indicator offline';
      }
      if (telStatus) telStatus.textContent = 'OFFLINE';
    }
  }

  fetchHealthTelemetry();
  setInterval(fetchHealthTelemetry, 15000);

  // ══════════════════════════════════════════════════════════════════════════
  // 5. AGENT ROSTER HIGHLIGHTING
  // ══════════════════════════════════════════════════════════════════════════
  function highlightAgent(agentName) {
    Object.values(agentChips).forEach((chip) => {
      if (chip) chip.className = 'agent-chip standby';
    });
    if (agentChips.Coordinator) {
      agentChips.Coordinator.className = 'agent-chip active';
    }
    if (agentName && agentChips[agentName]) {
      agentChips[agentName].className = 'agent-chip active';
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 6. AGENT NAVIGATION PILLS & MODE SELECTOR
  // ══════════════════════════════════════════════════════════════════════════
  const modePlaceholders = {
    auto: 'Ask Synaptix to plan your day, set a reminder, or draft an email...',
    gmail: 'Ask Gmail Agent to draft or check emails...',
    tasks: 'Ask Tasks Agent to add, list, or complete tasks...',
    notes: 'Ask Notes Agent to capture, search, or summarize notes...',
    calendar: 'Ask Calendar Agent to schedule, check, or reschedule events...',
    planner: 'Ask Smart Planner to optimize your schedule, timetable, or day...',
  };

  const modeAgentMap = {
    auto: 'Coordinator',
    gmail: 'GmailAgent',
    tasks: 'TaskAgent',
    notes: 'NotesAgent',
    calendar: 'CalendarAgent',
    planner: 'SmartDayPlannerAgent',
  };

  let activeAgentMode = 'auto';

  const agentNavPills = document.querySelectorAll('.agent-nav-pill');
  if (agentNavPills.length > 0) {
    agentNavPills.forEach((pill) => {
      pill.addEventListener('click', () => {
        agentNavPills.forEach((p) => p.classList.remove('active'));
        pill.classList.add('active');
        const mode = pill.dataset.mode || 'auto';
        activeAgentMode = mode;
        if (modeSelect) modeSelect.value = mode;
        if (userInput) {
          userInput.placeholder = modePlaceholders[mode] || modePlaceholders.auto;
          userInput.focus();
        }
        highlightAgent(modeAgentMap[mode] || 'Coordinator');
      });
    });
  }

  if (modeSelect) {
    modeSelect.addEventListener('change', () => {
      const mode = modeSelect.value;
      activeAgentMode = mode;
      agentNavPills.forEach((p) => {
        p.classList.toggle('active', p.dataset.mode === mode);
      });
      if (userInput) {
        userInput.placeholder = modePlaceholders[mode] || modePlaceholders.auto;
        userInput.focus();
      }
      highlightAgent(modeAgentMap[mode] || 'Coordinator');
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 7. MARKDOWN FORMATTER
  // ══════════════════════════════════════════════════════════════════════════
  function formatMarkdown(text) {
    if (!text) return '';
    let html = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Fenced code blocks
    html = html.replace(/```([a-z]*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Bold
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    // Italic
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    // Line breaks
    return html.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 8. CHAT ENGINE & HERO-TO-DOCKED TRANSITION
  // ══════════════════════════════════════════════════════════════════════════
  function updateChatDockState() {
    if (!chatContainer) return;
    const hasMessages = chatMessages && chatMessages.children.length > 0;
    if (hasMessages) {
      chatContainer.classList.remove('is-hero');
      chatContainer.classList.add('is-docked');
    } else {
      chatContainer.classList.add('is-hero');
      chatContainer.classList.remove('is-docked');
    }
  }

  function appendMessage(sender, text, isUser = false, agentBadge = null) {
    if (!chatMessages) return null;
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${isUser ? 'user' : 'assistant'}`;

    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const formattedContent = formatMarkdown(text);
    const badgeHtml = agentBadge && !isUser
      ? `<span style="display:inline-block; margin-left:6px; font-size:0.7rem; padding:1px 7px; border-radius:10px; background:rgba(59,130,246,0.18); color:#93c5fd; border:1px solid rgba(59,130,246,0.3);">⚡ ${agentBadge}</span>`
      : '';

    msgDiv.innerHTML = `
      <div class="message-avatar">${isUser ? '👤' : '✨'}</div>
      <div class="message-body">
        <div class="message-sender">${isUser ? 'You' : sender} ${badgeHtml}</div>
        <div class="message-text"><p>${formattedContent}</p></div>
        <div class="message-time">${now}</div>
      </div>
    `;

    chatMessages.appendChild(msgDiv);
    updateChatDockState();
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msgDiv;
  }

  function appendLoadingMessage() {
    if (!chatMessages) return null;
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message assistant loading-msg';
    msgDiv.innerHTML = `
      <div class="message-avatar thinking-avatar">
        <div class="avatar-orbit-ring"></div>
        <span>✨</span>
      </div>
      <div class="message-body">
        <div class="message-sender thinking-sender">
          <span>Synaptix Coordinator</span>
          <span class="thinking-dots">
            <span class="dot dot-1"></span>
            <span class="dot dot-2"></span>
            <span class="dot dot-3"></span>
          </span>
        </div>
        <div class="message-text thinking-bubble">
          <span class="shimmer-text">Analyzing intent & delegating across agent swarm...</span>
        </div>
      </div>
    `;
    chatMessages.appendChild(msgDiv);
    updateChatDockState();
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msgDiv;
  }

  // Chat Submission
  if (chatForm) {
    chatForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const query = userInput.value.trim();
      if (!query) return;

      // Append user message & dock chat
      appendMessage('You', query, true);
      userInput.value = '';
      userInput.disabled = true;
      sendBtn.disabled = true;

      // Trigger Thinking Animation on Prompt Box Aura
      if (auraGlowWrapper) {
        auraGlowWrapper.classList.remove('is-focused');
        auraGlowWrapper.classList.add('is-thinking');
      }

      const loadingElem = appendLoadingMessage();

      const userTz = (typeof Intl !== 'undefined' && Intl.DateTimeFormat)
        ? Intl.DateTimeFormat().resolvedOptions().timeZone
        : 'Asia/Kolkata';

      try {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: query,
            session_id: currentSessionId,
            conversation_history: conversationHistory.slice(-6),
            timezone: userTz,
            target_agent: activeAgentMode !== 'auto' ? activeAgentMode : undefined,
          }),
        });

        if (loadingElem) loadingElem.remove();

        if (response.status === 429) {
          let limitMsg = 'Operation paused to guarantee zero costs.';
          try {
            const errData = await response.json();
            limitMsg = (errData.detail && errData.detail.message) || errData.detail || limitMsg;
          } catch {}
          appendMessage(
            'Synaptix Guard',
            `⛔ **Daily Free-Tier Quota Limit Reached (HTTP 429)**\n\n${limitMsg}`,
            false
          );
          return;
        }

        if (!response.ok) {
          let errMsg = 'An unexpected error occurred. Please try again.';
          try {
            const rawText = await response.text();
            try {
              const errJson = JSON.parse(rawText);
              errMsg = (errJson.detail && (errJson.detail.message || errJson.detail)) || errJson.message || errMsg;
            } catch {
              if (rawText && !rawText.includes('Traceback') && !rawText.includes('File ') && !rawText.includes('<html')) {
                errMsg = rawText.slice(0, 150);
              }
            }
          } catch {}

          if (typeof errMsg === 'string' && (errMsg.includes('Traceback') || errMsg.includes('SyntaxError') || errMsg.includes('UnboundLocalError') || errMsg.includes('Internal Server Error'))) {
            errMsg = 'An internal error occurred while processing your request. Please try again.';
          }

          appendMessage(
            'Synaptix AI',
            `⚠️ ${errMsg}`,
            false
          );
          return;
        }

        const data = await response.json();
        currentSessionId = data.session_id || currentSessionId;
        if (currentSessionId) {
          localStorage.setItem('synaptix_current_session_id', currentSessionId);
        }
        if (typeof loadSessions === 'function') {
          loadSessions();
        }

        const orch = data.orchestration || {};
        const targetAgent = orch.activated_agent || (orch.activated_agents && orch.activated_agents[orch.activated_agents.length - 1]) || 'Coordinator';

        highlightAgent(targetAgent);
        appendMessage('Synaptix AI', data.reply, false, targetAgent);

        conversationHistory.push({ role: 'user', content: query });
        conversationHistory.push({ role: 'model', content: data.reply });

        // Auto-refresh relevant views
        if (targetAgent === 'TaskAgent' || query.toLowerCase().includes('task')) loadTasks();
        if (targetAgent === 'NotesAgent' || query.toLowerCase().includes('note')) loadNotes();
        if (targetAgent === 'CalendarAgent' || query.toLowerCase().includes('calendar') || query.toLowerCase().includes('meeting')) loadCalendarEvents();
        if (targetAgent === 'GmailAgent' || query.toLowerCase().includes('email') || query.toLowerCase().includes('draft')) loadDrafts();
        if (targetAgent === 'SmartDayPlannerAgent' || query.toLowerCase().includes('plan')) loadTimetable();
        if (query.toLowerCase().includes('remind') || (orch.tools_executed && orch.tools_executed.includes('set_reminder'))) {
          if (typeof loadReminders === 'function') loadReminders();
          if (typeof pollDueReminders === 'function') pollDueReminders();
        }

      } catch (err) {
        if (loadingElem) loadingElem.remove();
        let displayErr = err.message || 'Could not reach server';
        if (displayErr.includes('Traceback') || displayErr.includes('Unexpected token') || displayErr.includes('JSON')) {
          displayErr = 'Unable to complete request right now. Please try again.';
        }
        appendMessage('Synaptix AI', `⚠️ ${displayErr}`, false);
      } finally {
        if (auraGlowWrapper) auraGlowWrapper.classList.remove('is-thinking');
        userInput.disabled = false;
        sendBtn.disabled = false;
        userInput.focus();
      }
    });
  }

  // Suggestion Chips
  chips.forEach((chip) => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      if (userInput) {
        userInput.value = prompt;
        userInput.focus();
        if (!prompt.endsWith(' ') && !prompt.endsWith(':')) {
          chatForm.dispatchEvent(new Event('submit'));
        }
      }
    });
  });

  // ══════════════════════════════════════════════════════════════════════════
  // 8. PERSISTENT MULTI-SESSION CHAT HISTORY & SESSION SWITCHER
  // ══════════════════════════════════════════════════════════════════════════
  const newChatBtn = document.getElementById('newChatBtn');
  const chatSessionsList = document.getElementById('chatSessionsList');

  async function loadSessions() {
    if (!chatSessionsList) return;
    try {
      const response = await fetch('/api/sessions');
      if (!response.ok) return;
      const data = await response.json();
      const sessions = data.sessions || [];

      if (sessions.length === 0) {
        chatSessionsList.innerHTML = '<div class="sessions-empty" id="sessionsEmpty">No past chats yet</div>';
        return;
      }

      chatSessionsList.innerHTML = '';
      sessions.forEach((s) => {
        const item = document.createElement('div');
        item.className = `session-item ${s.session_id === currentSessionId ? 'active' : ''}`;
        item.setAttribute('data-session-id', s.session_id);
        item.setAttribute('title', s.title || 'Conversation');

        item.innerHTML = `
          <div class="session-item-content">
            <svg class="session-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            <span class="session-title">${escapeHtml(s.title || 'New Chat')}</span>
          </div>
          <button class="session-delete-btn" type="button" title="Delete conversation" aria-label="Delete conversation">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        `;

        item.addEventListener('click', (e) => {
          if (e.target.closest('.session-delete-btn')) return;
          switchSession(s.session_id);
        });

        const delBtn = item.querySelector('.session-delete-btn');
        if (delBtn) {
          delBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteSession(s.session_id);
          });
        }

        chatSessionsList.appendChild(item);
      });
    } catch (err) {
      console.warn('Failed to load sessions:', err);
    }
  }

  async function switchSession(sessionId) {
    if (!sessionId) return;
    currentSessionId = sessionId;
    localStorage.setItem('synaptix_current_session_id', sessionId);

    // Update active highlight in sidebar
    if (chatSessionsList) {
      const items = chatSessionsList.querySelectorAll('.session-item');
      items.forEach((it) => {
        if (it.getAttribute('data-session-id') === sessionId) {
          it.classList.add('active');
        } else {
          it.classList.remove('active');
        }
      });
    }

    try {
      const response = await fetch(`/api/sessions/${sessionId}/messages`);
      if (!response.ok) {
        showToast('Could not load session history', 'warning');
        return;
      }
      const data = await response.json();
      const messages = data.messages || [];

      if (chatMessages) chatMessages.innerHTML = '';
      conversationHistory.length = 0;

      messages.forEach((m) => {
        const isUser = m.role === 'user';
        const sender = isUser ? 'You' : 'Synaptix AI';
        appendMessage(sender, m.content, isUser);
        conversationHistory.push({ role: isUser ? 'user' : 'model', content: m.content });
      });

      updateChatDockState();
      highlightAgent('Coordinator');
      closeSessionsDrawerFunc();
      if (userInput) userInput.focus();
    } catch (err) {
      showToast('Error switching session: ' + err.message, 'error');
    }
  }

  function startNewChat() {
    currentSessionId = null;
    localStorage.removeItem('synaptix_current_session_id');
    if (chatMessages) chatMessages.innerHTML = '';
    conversationHistory.length = 0;
    updateChatDockState();
    highlightAgent('Coordinator');
    closeSessionsDrawerFunc();

    if (chatSessionsList) {
      chatSessionsList.querySelectorAll('.session-item').forEach((it) => it.classList.remove('active'));
    }
    if (userInput) {
      userInput.value = '';
      userInput.focus();
    }
  }

  async function deleteSession(sessionId) {
    try {
      const response = await fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' });
      if (!response.ok) {
        showToast('Failed to delete session', 'error');
        return;
      }
      showToast('Conversation deleted', 'info');
      if (currentSessionId === sessionId) {
        startNewChat();
      }
      await loadSessions();
    } catch (err) {
      showToast('Error deleting session: ' + err.message, 'error');
    }
  }

  if (newChatBtn) {
    newChatBtn.addEventListener('click', () => {
      startNewChat();
      showToast('New conversation started', 'info');
    });
  }

  // Clear Chat Button Handler
  if (clearChatBtn) {
    clearChatBtn.addEventListener('click', () => {
      startNewChat();
      showToast('Conversation cleared', 'info');
    });
  }

  // Copy Plan Button Handler
  if (copyPlanBtn) {
    copyPlanBtn.addEventListener('click', async () => {
      if (!latestPlanMarkdown) {
        showToast('No daily plan generated yet to copy', 'warning');
        return;
      }
      try {
        await navigator.clipboard.writeText(latestPlanMarkdown);
        showToast('Daily plan copied to clipboard!', 'success');
      } catch (e) {
        showToast('Failed to copy plan: ' + e.message, 'error');
      }
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 9. TASKS MANAGEMENT (Firestore)
  // ══════════════════════════════════════════════════════════════════════════
  const tasksContainer = document.getElementById('tasksContainer');
  const createTaskForm = document.getElementById('createTaskForm');
  const taskPendingCount = document.getElementById('taskPendingCount');
  const taskCompletedCount = document.getElementById('taskCompletedCount');
  const taskPriorityCount = document.getElementById('taskPriorityCount');

  async function loadTasks() {
    if (!tasksContainer) return;
    try {
      const resp = await fetch('/api/tasks');
      const data = await resp.json();
      const tasks = data.tasks || [];

      let pending = 0, completed = 0, high = 0;
      tasks.forEach((t) => {
        if (t.status === 'completed') completed++;
        else pending++;
        if (t.priority === 'high') high++;
      });
      if (taskPendingCount) taskPendingCount.textContent = pending;
      if (taskCompletedCount) taskCompletedCount.textContent = completed;
      if (taskPriorityCount) taskPriorityCount.textContent = high;

      if (tasks.length === 0) {
        tasksContainer.innerHTML = '<p class="empty-state">No tasks stored yet. Add one above or tell the AI Assistant!</p>';
        return;
      }

      tasksContainer.innerHTML = tasks.map((t) => `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 14px;background:var(--bg-surface-elevated);border:1px solid var(--border-subtle);border-radius:10px;">
          <div>
            <div style="font-weight:600;font-size:0.92rem;color:${t.status === 'completed' ? 'var(--text-muted)' : '#fff'};text-decoration:${t.status === 'completed' ? 'line-through' : 'none'};">
              ${t.title}
            </div>
            <div style="font-size:0.75rem;color:var(--text-secondary);margin-top:3px;">
              Due: <strong>${t.due_date || 'No date'}</strong> • Priority: <span style="color:${t.priority === 'high' ? '#f87171' : t.priority === 'medium' ? '#fbbf24' : '#34d399'};text-transform:uppercase;">${t.priority}</span>
            </div>
          </div>
          <div style="display:flex;gap:6px;">
            ${t.status !== 'completed' ? `<button onclick="updateTaskStatus('${t.id}', 'completed')" class="secondary-btn btn-sm" style="color:#34d399;">✓ Done</button>` : `<button onclick="updateTaskStatus('${t.id}', 'pending')" class="secondary-btn btn-sm">↺ Reopen</button>`}
            <button onclick="deleteTaskItem('${t.id}')" class="secondary-btn btn-sm" style="color:#f87171;">✕</button>
          </div>
        </div>
      `).join('');
    } catch (err) {
      tasksContainer.innerHTML = `<p style="color:#ef4444;">Failed to load tasks: ${err.message}</p>`;
    }
  }

  window.updateTaskStatus = async (taskId, newStatus) => {
    try {
      await fetch(`/api/tasks/${taskId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      showToast(`Task marked as ${newStatus}`, 'success');
      loadTasks();
    } catch (e) {
      showToast('Error updating task: ' + e.message, 'error');
    }
  };

  window.deleteTaskItem = async (taskId) => {
    if (!confirm('Delete this task?')) return;
    try {
      await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
      showToast('Task removed', 'info');
      loadTasks();
    } catch (e) {
      showToast('Error deleting task: ' + e.message, 'error');
    }
  };

  if (createTaskForm) {
    createTaskForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const title = document.getElementById('newTaskTitle').value.trim();
      const dueDate = document.getElementById('newTaskDueDate').value;
      const priority = document.getElementById('newTaskPriority').value;
      const remInput = document.getElementById('newTaskReminder');
      if (!title) return;

      try {
        const resp = await fetch('/api/tasks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title, due_date: dueDate || null, priority }),
        });
        const taskData = await resp.json();

        // Optional attached reminder
        if (remInput && remInput.value && taskData.task) {
          try {
            await fetch('/api/reminders', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                title: `Task: ${title}`,
                remind_at: new Date(remInput.value).toISOString(),
                source_type: 'task',
                source_id: taskData.task.id,
              }),
            });
            remInput.value = '';
            showToast('Reminder attached to task!', 'info');
            if (typeof loadReminders === 'function') loadReminders();
          } catch (remErr) {
            console.warn('Failed attaching reminder:', remErr);
          }
        }

        document.getElementById('newTaskTitle').value = '';
        showToast('Task added to Firestore', 'success');
        loadTasks();
      } catch (err) {
        showToast('Failed to save task: ' + err.message, 'error');
      }
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 10. NOTES MANAGEMENT (Firestore)
  // ══════════════════════════════════════════════════════════════════════════
  const notesContainer = document.getElementById('notesContainer');
  const createNoteForm = document.getElementById('createNoteForm');
  const searchNotesInput = document.getElementById('searchNotesInput');

  async function loadNotes(searchTerm = '') {
    if (!notesContainer) return;
    try {
      const url = searchTerm ? `/api/notes?query=${encodeURIComponent(searchTerm)}` : '/api/notes';
      const resp = await fetch(url);
      const data = await resp.json();
      const notes = data.notes || [];

      if (notes.length === 0) {
        notesContainer.innerHTML = '<p class="empty-state" style="grid-column: 1 / -1;">No notes found.</p>';
        return;
      }

      notesContainer.innerHTML = notes.map((n) => `
        <div style="background:var(--bg-surface-elevated);border:1px solid var(--border-subtle);border-radius:10px;padding:14px;display:flex;flex-direction:column;justify-content:space-between;gap:8px;">
          <div>
            <div style="font-weight:600;font-size:0.92rem;color:#fff;margin-bottom:4px;">
              ${n.title || 'Untitled Note'}
            </div>
            <div style="font-size:0.82rem;color:var(--text-secondary);line-height:1.5;white-space:pre-wrap;">
              ${n.content}
            </div>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;padding-top:8px;border-top:1px solid var(--border-subtle);">
            <div style="display:flex;gap:4px;flex-wrap:wrap;">
              ${(n.tags || []).map((tag) => `<span style="font-size:0.68rem;background:rgba(59,130,246,0.15);color:#93c5fd;padding:1px 6px;border-radius:4px;">#${tag}</span>`).join('')}
            </div>
            <button onclick="deleteNoteItem('${n.id}')" style="background:transparent;border:none;color:#f87171;cursor:pointer;font-size:0.8rem;" title="Delete Note">✕</button>
          </div>
        </div>
      `).join('');
    } catch (err) {
      notesContainer.innerHTML = `<p style="color:#ef4444;">Failed to load notes: ${err.message}</p>`;
    }
  }

  window.deleteNoteItem = async (noteId) => {
    if (!confirm('Delete this note?')) return;
    try {
      await fetch(`/api/notes/${noteId}`, { method: 'DELETE' });
      showToast('Note deleted', 'info');
      loadNotes();
    } catch (e) {
      showToast('Error deleting note: ' + e.message, 'error');
    }
  };

  if (createNoteForm) {
    createNoteForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const title = document.getElementById('newNoteTitle').value.trim();
      const content = document.getElementById('newNoteContent').value.trim();
      const tagsStr = document.getElementById('newNoteTags').value.trim();
      const remInput = document.getElementById('newNoteReminder');
      if (!content) return;

      const tags = tagsStr ? tagsStr.split(',').map((t) => t.trim().toLowerCase()) : [];

      try {
        const resp = await fetch('/api/notes', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content, title: title || null, tags }),
        });
        const noteData = await resp.json();

        // Optional attached reminder
        if (remInput && remInput.value && noteData.note) {
          try {
            await fetch('/api/reminders', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                title: `Note: ${title || content.slice(0, 30)}`,
                remind_at: new Date(remInput.value).toISOString(),
                source_type: 'note',
                source_id: noteData.note.id,
              }),
            });
            remInput.value = '';
            showToast('Reminder attached to note!', 'info');
            if (typeof loadReminders === 'function') loadReminders();
          } catch (remErr) {
            console.warn('Failed attaching reminder:', remErr);
          }
        }

        document.getElementById('newNoteTitle').value = '';
        document.getElementById('newNoteContent').value = '';
        document.getElementById('newNoteTags').value = '';
        showToast('Note captured in Firestore', 'success');
        loadNotes();
      } catch (err) {
        showToast('Failed to save note: ' + err.message, 'error');
      }
    });
  }

  if (searchNotesInput) {
    let debounceTimer;
    searchNotesInput.addEventListener('input', (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        loadNotes(e.target.value.trim());
      }, 250);
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 11. CALENDAR MCP MANAGEMENT & INTERACTIVE MONTHLY GRID
  // ══════════════════════════════════════════════════════════════════════════
  const calendarEventsContainer = document.getElementById('calendarEventsContainer');
  const createEventForm = document.getElementById('createEventForm');
  const checkConflictForm = document.getElementById('checkConflictForm');
  const calendarFilterDate = document.getElementById('calendarFilterDate');
  const conflictStatusBadge = document.getElementById('conflictStatusBadge');
  const conflictResultText = document.getElementById('conflictResultText');

  // Interactive Calendar Grid & Segmented View Elements
  const calCurrentMonthYear = document.getElementById('calCurrentMonthYear');
  const calPrevMonthBtn = document.getElementById('calPrevMonthBtn');
  const calNextMonthBtn = document.getElementById('calNextMonthBtn');
  const calTodayBtn = document.getElementById('calTodayBtn');
  const calMonthGrid = document.getElementById('calMonthGrid');
  const calSelectedDateHeader = document.getElementById('calSelectedDateHeader');
  const calSelectedDateSubtitle = document.getElementById('calSelectedDateSubtitle');
  const calQuickAddEventBtn = document.getElementById('calQuickAddEventBtn');
  const calEventsCount = document.getElementById('calEventsCount');
  const calAlertsCount = document.getElementById('calAlertsCount');
  const calTimetableCount = document.getElementById('calTimetableCount');
  const calSelectedAlertsContainer = document.getElementById('calSelectedAlertsContainer');
  const calSelectedTimetableContainer = document.getElementById('calSelectedTimetableContainer');

  // Segmented View Elements
  const calTabUpcoming = document.getElementById('calTabUpcoming');
  const calTabSelectedDate = document.getElementById('calTabSelectedDate');
  const calTabPast = document.getElementById('calTabPast');
  const calViewUpcoming = document.getElementById('calViewUpcoming');
  const calViewSelectedDate = document.getElementById('calViewSelectedDate');
  const calViewPast = document.getElementById('calViewPast');
  const calUpcomingContainer = document.getElementById('calUpcomingContainer');
  const calPastContainer = document.getElementById('calPastContainer');
  const calUpcomingBadge = document.getElementById('calUpcomingBadge');
  const calPastBadge = document.getElementById('calPastBadge');
  const calSelectedDateTabLabel = document.getElementById('calSelectedDateTabLabel');

  let calCurrentYear = new Date().getFullYear();
  let calCurrentMonth = new Date().getMonth();
  let selectedCalendarDate = new Date().toISOString().split('T')[0];
  let calMonthIndicators = {}; // dateStr -> { events: bool, tasks: bool, reminders: bool }

  // ────────────────────────────────────────────────────────────────────────────
  // TIME & DATE FORMATTING HELPERS (12-Hour Local Time & Relative Badges)
  // ────────────────────────────────────────────────────────────────────────────
  function format12hTime(timeStr) {
    if (!timeStr) return '';
    try {
      const clean = timeStr.replace('Z', '');
      const dt = new Date(clean);
      if (!isNaN(dt.getTime())) {
        return dt.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
      }
      const tPart = timeStr.includes('T') ? timeStr.split('T')[1] : timeStr;
      const [h, m] = tPart.split(':');
      let hr = parseInt(h, 10);
      const ampm = hr >= 12 ? 'PM' : 'AM';
      hr = hr % 12 || 12;
      return `${hr}:${m} ${ampm}`;
    } catch {
      return timeStr;
    }
  }

  function formatEventDateSpan(startIso, endIso) {
    const start12 = format12hTime(startIso);
    const end12 = format12hTime(endIso);
    if (start12 && end12) return `${start12} – ${end12}`;
    return start12 || end12 || '';
  }

  function getRelativeEventBadge(startIso, endIso, now = new Date()) {
    try {
      const startClean = (startIso || '').replace('Z', '');
      const endClean = (endIso || startIso || '').replace('Z', '');
      const startDt = new Date(startClean);
      const endDt = new Date(endClean);
      const nowDateStr = now.toISOString().split('T')[0];
      const startDateStr = (startIso || '').split('T')[0];

      // Check if event has ended
      if (endDt < now) {
        return '<span class="cal-ended-badge">Ended</span>';
      }

      const start12 = format12hTime(startIso);

      // Event is today
      if (startDateStr === nowDateStr) {
        const diffHours = (startDt - now) / (1000 * 60 * 60);
        if (diffHours > 0 && diffHours <= 3) {
          const mins = Math.max(1, Math.round((startDt - now) / (1000 * 60)));
          return mins >= 60
            ? `<span class="cal-time-badge badge-soon">In ${Math.round(diffHours)}h · ${start12}</span>`
            : `<span class="cal-time-badge badge-soon">In ${mins}m · ${start12}</span>`;
        }
        return `<span class="cal-time-badge badge-today">Today · ${start12}</span>`;
      }

      // Event is tomorrow
      const tomorrow = new Date(now);
      tomorrow.setDate(tomorrow.getDate() + 1);
      const tomorrowDateStr = tomorrow.toISOString().split('T')[0];
      if (startDateStr === tomorrowDateStr) {
        return `<span class="cal-time-badge badge-tomorrow">Tomorrow · ${start12}</span>`;
      }

      // Future date
      const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const m = monthNames[startDt.getMonth()] || '';
      const d = startDt.getDate() || '';
      return `<span class="cal-time-badge badge-future">${m} ${d} · ${start12}</span>`;
    } catch {
      return '<span class="cal-time-badge badge-future">Upcoming</span>';
    }
  }

  // ────────────────────────────────────────────────────────────────────────────
  // SEGMENTED CALENDAR VIEW SWITCHER (Upcoming / Selected Date / Past)
  // ────────────────────────────────────────────────────────────────────────────
  function switchCalendarView(viewName) {
    const tabs = [
      { name: 'upcoming', btn: calTabUpcoming, pane: calViewUpcoming },
      { name: 'selected-date', btn: calTabSelectedDate, pane: calViewSelectedDate },
      { name: 'past', btn: calTabPast, pane: calViewPast },
    ];

    tabs.forEach(t => {
      if (t.btn) {
        if (t.name === viewName) {
          t.btn.classList.add('active');
          t.btn.setAttribute('aria-selected', 'true');
        } else {
          t.btn.classList.remove('active');
          t.btn.setAttribute('aria-selected', 'false');
        }
      }
      if (t.pane) {
        t.pane.style.display = (t.name === viewName) ? 'flex' : 'none';
      }
    });
  }

  if (calTabUpcoming) {
    calTabUpcoming.addEventListener('click', () => switchCalendarView('upcoming'));
  }
  if (calTabSelectedDate) {
    calTabSelectedDate.addEventListener('click', () => switchCalendarView('selected-date'));
  }
  if (calTabPast) {
    calTabPast.addEventListener('click', () => switchCalendarView('past'));
  }

  function renderCalendarMonth(year, month) {
    if (!calMonthGrid) return;
    const monthNames = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];
    if (calCurrentMonthYear) {
      calCurrentMonthYear.textContent = `${monthNames[month]} ${year}`;
    }

    const todayStr = new Date().toISOString().split('T')[0];
    const firstDayIndex = new Date(year, month, 1).getDay(); // 0 (Sun) to 6 (Sat)
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const daysInPrevMonth = new Date(year, month, 0).getDate();

    let cellsHtml = '';

    // Prev month padding cells
    for (let i = firstDayIndex - 1; i >= 0; i--) {
      const dayNum = daysInPrevMonth - i;
      const prevMonth = month === 0 ? 11 : month - 1;
      const prevYear = month === 0 ? year - 1 : year;
      const dateStr = `${prevYear}-${String(prevMonth + 1).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`;
      cellsHtml += renderDayCell(dateStr, dayNum, true, todayStr);
    }

    // Current month cells
    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      cellsHtml += renderDayCell(dateStr, day, false, todayStr);
    }

    // Next month padding cells to complete 35 or 42 grid cells
    const totalCells = firstDayIndex + daysInMonth;
    const remaining = totalCells > 35 ? 42 - totalCells : 35 - totalCells;
    for (let nextDay = 1; nextDay <= remaining; nextDay++) {
      const nextMonth = month === 11 ? 0 : month + 1;
      const nextYear = month === 11 ? year + 1 : year;
      const dateStr = `${nextYear}-${String(nextMonth + 1).padStart(2, '0')}-${String(nextDay).padStart(2, '0')}`;
      cellsHtml += renderDayCell(dateStr, nextDay, true, todayStr);
    }

    calMonthGrid.innerHTML = cellsHtml;

    // Attach click events
    calMonthGrid.querySelectorAll('.cal-day-cell').forEach(cell => {
      cell.addEventListener('click', () => {
        const dStr = cell.getAttribute('data-date');
        if (dStr) selectCalendarDate(dStr);
      });
    });
  }

  function renderDayCell(dateStr, dayNum, isOtherMonth, todayStr) {
    const isToday = dateStr === todayStr;
    const isSelected = dateStr === selectedCalendarDate;
    const classes = ['cal-day-cell'];
    if (isOtherMonth) classes.push('other-month');
    if (isToday) classes.push('is-today');
    if (isSelected) classes.push('is-selected');

    const ind = calMonthIndicators[dateStr] || {};
    let dotsHtml = '';
    if (ind.events) dotsHtml += '<span class="cal-dot cal-dot-event" title="Calendar Event"></span>';
    if (ind.tasks) dotsHtml += '<span class="cal-dot cal-dot-task" title="Due Task"></span>';
    if (ind.reminders) dotsHtml += '<span class="cal-dot cal-dot-reminder" title="Due Reminder"></span>';

    return `
      <div class="${classes.join(' ')}" data-date="${dateStr}">
        <span class="cal-day-num">${dayNum}</span>
        <div class="cal-day-dots">${dotsHtml}</div>
      </div>
    `;
  }

  async function fetchMonthIndicators(year, month) {
    const monthPrefix = `${year}-${String(month + 1).padStart(2, '0')}`;
    try {
      const [eventsResp, tasksResp, remResp] = await Promise.all([
        fetch(`/api/calendar/events?month=${monthPrefix}`).then(r => r.json()).catch(() => ({ events: [] })),
        fetch('/api/tasks').then(r => r.json()).catch(() => ({ tasks: [] })),
        fetch('/api/reminders').then(r => r.json()).catch(() => ({ reminders: [] }))
      ]);

      calMonthIndicators = {};

      (eventsResp.events || []).forEach(e => {
        if (e.start_time) {
          const ds = e.start_time.split('T')[0];
          if (!calMonthIndicators[ds]) calMonthIndicators[ds] = {};
          calMonthIndicators[ds].events = true;
        }
      });

      (tasksResp.tasks || []).forEach(t => {
        if (t.due_date && t.status !== 'completed') {
          const ds = t.due_date;
          if (!calMonthIndicators[ds]) calMonthIndicators[ds] = {};
          calMonthIndicators[ds].tasks = true;
        }
      });

      (remResp.reminders || []).forEach(r => {
        if (r.remind_at && r.status !== 'dismissed') {
          const ds = r.remind_at.split('T')[0];
          if (!calMonthIndicators[ds]) calMonthIndicators[ds] = {};
          calMonthIndicators[ds].reminders = true;
        }
      });

      renderCalendarMonth(year, month);
    } catch (e) {
      console.warn('Could not load calendar indicators:', e);
    }
  }

  function selectCalendarDate(dateStr) {
    selectedCalendarDate = dateStr;
    const d = new Date(dateStr + 'T00:00:00');
    const formattedDate = d.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' });
    const formattedShort = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    if (calSelectedDateHeader) calSelectedDateHeader.textContent = formattedDate;
    if (calSelectedDateTabLabel) calSelectedDateTabLabel.textContent = `Date: ${formattedShort}`;

    // Automatically switch to the Selected Date view
    switchCalendarView('selected-date');

    if (calendarFilterDate) calendarFilterDate.value = dateStr;
    const startInp = document.getElementById('newEventStart');
    const endInp = document.getElementById('newEventEnd');
    if (startInp) startInp.value = `${dateStr}T10:00`;
    if (endInp) endInp.value = `${dateStr}T11:00`;
    const chkStart = document.getElementById('checkStart');
    const chkEnd = document.getElementById('checkEnd');
    if (chkStart) chkStart.value = `${dateStr}T10:00`;
    if (chkEnd) chkEnd.value = `${dateStr}T11:00`;

    document.querySelectorAll('.cal-day-cell').forEach(c => {
      if (c.getAttribute('data-date') === dateStr) {
        c.classList.add('is-selected');
      } else {
        c.classList.remove('is-selected');
      }
    });

    loadCalendarEvents(dateStr);
    loadSelectedDateAlerts(dateStr);
    loadSelectedDateTimetable(dateStr);
  }

  async function loadSelectedDateAlerts(dateStr) {
    if (!calSelectedAlertsContainer) return;
    try {
      const [tasksResp, remResp] = await Promise.all([
        fetch('/api/tasks').then(r => r.json()).catch(() => ({ tasks: [] })),
        fetch('/api/reminders').then(r => r.json()).catch(() => ({ reminders: [] }))
      ]);

      const tasks = (tasksResp.tasks || []).filter(t => t.due_date && t.due_date === dateStr);
      const reminders = (remResp.reminders || []).filter(r => r.remind_at && r.remind_at.startsWith(dateStr));

      if (calAlertsCount) calAlertsCount.textContent = tasks.length + reminders.length;

      if (tasks.length === 0 && reminders.length === 0) {
        calSelectedAlertsContainer.innerHTML = '<p class="empty-state" style="padding:10px 0;">No tasks or reminders due on this date.</p>';
        return;
      }

      let html = '';
      tasks.forEach(t => {
        html += `
          <div style="padding:8px 10px;background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);border-radius:8px;font-size:0.82rem;">
            <div style="font-weight:600;color:#6ee7b7;">✓ Task: ${escapeHtml(t.title)}</div>
            <div style="font-size:0.72rem;color:var(--text-secondary);margin-top:2px;">Priority: ${escapeHtml(t.priority.toUpperCase())} • Status: ${escapeHtml(t.status)}</div>
          </div>
        `;
      });
      reminders.forEach(r => {
        const timeStr = new Date(r.remind_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        html += `
          <div style="padding:8px 10px;background:rgba(255,107,61,0.08);border:1px solid rgba(255,107,61,0.25);border-radius:8px;font-size:0.82rem;">
            <div style="font-weight:600;color:#fdba74;">⏰ Reminder: ${escapeHtml(r.title)}</div>
            <div style="font-size:0.72rem;color:var(--text-secondary);margin-top:2px;">At: ${timeStr} • Status: ${escapeHtml(r.status)}</div>
          </div>
        `;
      });
      calSelectedAlertsContainer.innerHTML = html;
    } catch (e) {
      calSelectedAlertsContainer.innerHTML = `<p style="color:#ef4444;font-size:0.8rem;">Error loading alerts: ${escapeHtml(e.message)}</p>`;
    }
  }

  async function loadSelectedDateTimetable(dateStr) {
    if (!calSelectedTimetableContainer) return;
    try {
      const d = new Date(dateStr + 'T00:00:00');
      const dayNames = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
      const weekday = dayNames[d.getDay()];

      const resp = await fetch(`/api/timetable?day=${weekday}`);
      const data = await resp.json();
      const blocks = data.blocks || [];

      if (calTimetableCount) calTimetableCount.textContent = blocks.length;

      if (blocks.length === 0) {
        calSelectedTimetableContainer.innerHTML = '<p class="empty-state" style="padding:10px 0;">No timetable blocks scheduled for this weekday.</p>';
        return;
      }

      calSelectedTimetableContainer.innerHTML = blocks.map(b => `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:7px 10px;background:var(--bg-surface);border:1px solid var(--border-subtle);border-radius:8px;font-size:0.8rem;">
          <div>
            <strong style="color:#fff;">${escapeHtml(b.title)}</strong>
            <div style="color:#93c5fd;font-family:monospace;font-size:0.74rem;">${escapeHtml(b.start_time)} - ${escapeHtml(b.end_time)}</div>
          </div>
          <span class="tt-cat-badge">${escapeHtml((b.category || 'focus').toUpperCase())}</span>
        </div>
      `).join('');
    } catch (e) {
      calSelectedTimetableContainer.innerHTML = `<p style="color:#ef4444;font-size:0.8rem;">Error: ${escapeHtml(e.message)}</p>`;
    }
  }

  function renderUpcomingEvents(events) {
    if (!calUpcomingContainer) return;
    if (calUpcomingBadge) calUpcomingBadge.textContent = events.length;

    if (events.length === 0) {
      calUpcomingContainer.innerHTML = `
        <div class="empty-state" style="padding:24px 0;">
          <p>No upcoming events scheduled.</p>
          <button type="button" class="secondary-btn btn-sm" onclick="document.getElementById('scheduleEventCard').scrollIntoView({behavior:'smooth'}); document.getElementById('newEventSummary').focus();" style="margin-top:8px;">+ Schedule an Event</button>
        </div>
      `;
      return;
    }

    const now = new Date();
    calUpcomingContainer.innerHTML = events.map(e => {
      const badge = getRelativeEventBadge(e.start_time, e.end_time, now);
      const timeSpan = formatEventDateSpan(e.start_time, e.end_time);
      const startDt = new Date((e.start_time || '').replace('Z', ''));
      const dateFormatted = !isNaN(startDt.getTime())
        ? startDt.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
        : (e.start_time || '').split('T')[0];

      return `
        <div class="cal-event-card">
          <div class="cal-event-info">
            <div class="cal-event-title-row">
              <strong class="cal-event-title">${escapeHtml(e.summary)}</strong>
              ${badge}
            </div>
            <div class="cal-event-time-row">
              <span>📅 ${dateFormatted}</span>
              <span>•</span>
              <span>⏱️ ${timeSpan}</span>
              ${e.location ? `<span>•</span><span>📍 ${escapeHtml(e.location)}</span>` : ''}
            </div>
          </div>
          <button type="button" onclick="deleteCalendarEventItem('${e.id}')" class="secondary-btn btn-sm" style="color:#f87171;padding:4px 8px;">✕ Cancel</button>
        </div>
      `;
    }).join('');
  }

  function renderPastEvents(events) {
    if (!calPastContainer) return;
    if (calPastBadge) calPastBadge.textContent = events.length;

    if (events.length === 0) {
      calPastContainer.innerHTML = `
        <div class="empty-state" style="padding:24px 0;">
          <p>No completed or past events recorded in the last 30 days.</p>
        </div>
      `;
      return;
    }

    calPastContainer.innerHTML = events.map(e => {
      const timeSpan = formatEventDateSpan(e.start_time, e.end_time);
      const startDt = new Date((e.start_time || '').replace('Z', ''));
      const dateFormatted = !isNaN(startDt.getTime())
        ? startDt.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })
        : (e.start_time || '').split('T')[0];

      return `
        <div class="cal-event-card cal-event-ended">
          <div class="cal-event-info">
            <div class="cal-event-title-row">
              <strong class="cal-event-title">${escapeHtml(e.summary)}</strong>
              <span class="cal-ended-badge">Ended</span>
            </div>
            <div class="cal-event-time-row">
              <span>📅 ${dateFormatted}</span>
              <span>•</span>
              <span>⏱️ ${timeSpan}</span>
              ${e.location ? `<span>•</span><span>📍 ${escapeHtml(e.location)}</span>` : ''}
            </div>
          </div>
          <button type="button" onclick="deleteCalendarEventItem('${e.id}')" class="secondary-btn btn-sm" style="color:var(--text-muted);padding:4px 8px;" title="Remove past event">✕</button>
        </div>
      `;
    }).join('');
  }

  async function loadAllCalendarData() {
    try {
      const resp = await fetch('/api/calendar/events');
      if (resp.ok) {
        const data = await resp.json();
        const allEv = data.events || [];
        const now = new Date();

        let upcoming = [];
        let past = [];

        if (Array.isArray(data.upcoming) && Array.isArray(data.past)) {
          upcoming = data.upcoming;
          past = data.past;
        } else {
          allEv.forEach(e => {
            const endIso = e.end_time || e.start_time;
            const endDt = endIso ? new Date(endIso.replace('Z', '')) : now;
            if (endDt >= now) {
              upcoming.push(e);
            } else {
              past.push(e);
            }
          });
          upcoming.sort((a, b) => (a.start_time || '').localeCompare(b.start_time || ''));
          past.sort((a, b) => (b.start_time || '').localeCompare(a.start_time || ''));
        }

        renderUpcomingEvents(upcoming);
        renderPastEvents(past);
      }
    } catch (e) {
      console.warn('Could not load upcoming/past calendar data:', e);
    }

    if (selectedCalendarDate) {
      loadCalendarEvents(selectedCalendarDate);
    }
  }

  async function loadCalendarEvents(dateStr = '') {
    if (!calendarEventsContainer) return;
    const effectiveDate = dateStr || selectedCalendarDate || '';
    try {
      const url = effectiveDate ? `/api/calendar/events?date=${encodeURIComponent(effectiveDate)}` : '/api/calendar/events';
      const resp = await fetch(url);
      const data = await resp.json();
      const events = data.events || [];

      if (calEventsCount) calEventsCount.textContent = events.length;

      if (events.length === 0) {
        calendarEventsContainer.innerHTML = '<p class="empty-state" style="padding:10px 0;">No events scheduled for this date.</p>';
        return;
      }

      calendarEventsContainer.innerHTML = events.map((e) => `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 12px;background:var(--bg-surface);border:1px solid var(--border-subtle);border-radius:8px;">
          <div>
            <div style="font-weight:600;font-size:0.88rem;color:#fff;">
              ${escapeHtml(e.summary)}
            </div>
            <div style="font-size:0.74rem;color:var(--text-secondary);margin-top:2px;">
              ⏱️ ${formatEventDateSpan(e.start_time, e.end_time)} ${e.location ? `• 📍 ${escapeHtml(e.location)}` : ''}
            </div>
          </div>
          <button onclick="deleteCalendarEventItem('${e.id}')" class="secondary-btn btn-sm" style="color:#f87171;padding:3px 7px;">✕ Cancel</button>
        </div>
      `).join('');
    } catch (err) {
      calendarEventsContainer.innerHTML = `<p style="color:#ef4444;font-size:0.8rem;">Failed to load events: ${escapeHtml(err.message)}</p>`;
    }
  }

  window.deleteCalendarEventItem = async (eventId) => {
    if (!confirm('Cancel this event?')) return;
    try {
      await fetch(`/api/calendar/events/${eventId}`, { method: 'DELETE' });
      showToast('Event cancelled', 'info');
      loadAllCalendarData();
      fetchMonthIndicators(calCurrentYear, calCurrentMonth);
    } catch (e) {
      showToast('Error deleting event: ' + e.message, 'error');
    }
  };

  if (createEventForm) {
    createEventForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const summary = document.getElementById('newEventSummary').value.trim();
      const startTime = document.getElementById('newEventStart').value;
      const endTime = document.getElementById('newEventEnd').value;
      const location = document.getElementById('newEventLocation').value.trim();
      if (!summary || !startTime || !endTime) return;

      try {
        await fetch('/api/calendar/events', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ summary, start_time: startTime, end_time: endTime, location }),
        });
        document.getElementById('newEventSummary').value = '';
        document.getElementById('newEventLocation').value = '';
        showToast('Event booked on Google Calendar!', 'success');
        loadAllCalendarData();
        fetchMonthIndicators(calCurrentYear, calCurrentMonth);
      } catch (err) {
        showToast('Failed to schedule event: ' + err.message, 'error');
      }
    });
  }

  if (checkConflictForm) {
    checkConflictForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const start = document.getElementById('checkStart').value;
      const end = document.getElementById('checkEnd').value;
      if (!start || !end) return;

      try {
        const resp = await fetch('/api/calendar/check-availability', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ start_time: start, end_time: end }),
        });
        const data = await resp.json();
        if (data.available) {
          conflictStatusBadge.textContent = 'Free / Available';
          conflictStatusBadge.className = 'status-chip success';
          conflictResultText.innerHTML = `Timeslot is clear from <strong>${escapeHtml(start)}</strong> to <strong>${escapeHtml(end)}</strong>.`;
        } else {
          conflictStatusBadge.textContent = `${data.conflicts_count} Conflict(s)`;
          conflictStatusBadge.className = 'status-chip';
          conflictStatusBadge.style.color = '#f87171';
          const confTitles = data.conflicting_events.map((c) => `• "${escapeHtml(c.summary)}"`).join('<br>');
          conflictResultText.innerHTML = `Overlaps with:<br>${confTitles}`;
        }
      } catch (err) {
        conflictResultText.textContent = 'Error checking availability: ' + err.message;
      }
    });
  }

  if (calendarFilterDate) {
    calendarFilterDate.addEventListener('change', (e) => {
      if (e.target.value) selectCalendarDate(e.target.value);
    });
  }

  if (calPrevMonthBtn) {
    calPrevMonthBtn.addEventListener('click', () => {
      calCurrentMonth--;
      if (calCurrentMonth < 0) {
        calCurrentMonth = 11;
        calCurrentYear--;
      }
      renderCalendarMonth(calCurrentYear, calCurrentMonth);
      fetchMonthIndicators(calCurrentYear, calCurrentMonth);
    });
  }

  if (calNextMonthBtn) {
    calNextMonthBtn.addEventListener('click', () => {
      calCurrentMonth++;
      if (calCurrentMonth > 11) {
        calCurrentMonth = 0;
        calCurrentYear++;
      }
      renderCalendarMonth(calCurrentYear, calCurrentMonth);
      fetchMonthIndicators(calCurrentYear, calCurrentMonth);
    });
  }

  if (calTodayBtn) {
    calTodayBtn.addEventListener('click', () => {
      const now = new Date();
      calCurrentYear = now.getFullYear();
      calCurrentMonth = now.getMonth();
      const todayStr = now.toISOString().split('T')[0];
      renderCalendarMonth(calCurrentYear, calCurrentMonth);
      fetchMonthIndicators(calCurrentYear, calCurrentMonth);
      selectCalendarDate(todayStr);
    });
  }

  if (calQuickAddEventBtn) {
    calQuickAddEventBtn.addEventListener('click', () => {
      const target = document.getElementById('scheduleEventCard');
      if (target) {
        target.scrollIntoView({ behavior: 'smooth' });
        const summaryInp = document.getElementById('newEventSummary');
        if (summaryInp) summaryInp.focus();
      }
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 12. GMAIL DRAFTS & HUMAN-IN-THE-LOOP DISPATCH
  // ══════════════════════════════════════════════════════════════════════════
  const draftsContainer = document.getElementById('draftsContainer');
  const createDraftForm = document.getElementById('createDraftForm');
  const refreshDraftsBtn = document.getElementById('refreshDraftsBtn');

  async function loadDrafts() {
    if (!draftsContainer) return;
    try {
      const resp = await fetch('/api/gmail/drafts');
      if (!resp.ok) throw new Error('Could not fetch drafts');
      const data = await resp.json();
      const drafts = data.drafts || [];

      if (drafts.length === 0) {
        draftsContainer.innerHTML = '<p class="empty-state">No drafts in queue. Compose one above or ask the AI Assistant!</p>';
        return;
      }

      draftsContainer.innerHTML = drafts.map((d) => `
        <div style="background:var(--bg-surface-elevated);border:1px solid var(--border-subtle);border-radius:10px;padding:14px;display:flex;flex-direction:column;gap:8px;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div>
              <div style="font-weight:600;font-size:0.92rem;color:#fff;">
                ${d.subject || '(No Subject)'}
              </div>
              <div style="font-size:0.75rem;color:var(--text-secondary);margin-top:2px;">
                To: <strong style="color:#93c5fd;">${d.to}</strong> • ID: <code>${d.draft_id}</code>
              </div>
            </div>
            <span class="status-chip ${d.status === 'sent' ? 'success' : 'highlight'}">
              ${d.status === 'sent' ? 'SENT' : 'DRAFT (NEEDS APPROVAL)'}
            </span>
          </div>
          <div style="font-size:0.82rem;color:var(--text-primary);background:var(--bg-input);padding:10px 12px;border-radius:8px;line-height:1.45;white-space:pre-wrap;">
            ${d.body}
          </div>
          <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:4px;">
            ${d.status !== 'sent' ? `
              <button onclick="approveAndSendDraft('${d.draft_id}')" class="primary-btn btn-sm" style="display:flex;align-items:center;gap:6px;">
                <span>🚀 Approve & Send</span>
              </button>
            ` : '<span style="font-size:0.75rem;color:var(--text-muted);">Dispatched</span>'}
          </div>
        </div>
      `).join('');
    } catch (err) {
      draftsContainer.innerHTML = `<p style="color:#ef4444;">Failed to load drafts: ${err.message}</p>`;
    }
  }

  window.approveAndSendDraft = async (draftId) => {
    if (!confirm(`Are you sure you want to approve and send draft ${draftId}?`)) return;
    try {
      const resp = await fetch('/api/gmail/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ draft_id: draftId }),
      });
      const res = await resp.json();
      if (res.success) {
        showToast('Email draft dispatched successfully!', 'success');
      } else {
        showToast('Draft dispatch result: ' + JSON.stringify(res.result || res), 'info');
      }
      loadDrafts();
    } catch (err) {
      showToast('Error dispatching draft: ' + err.message, 'error');
    }
  };

  if (createDraftForm) {
    createDraftForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const to = document.getElementById('newDraftTo').value.trim();
      const subject = document.getElementById('newDraftSubject').value.trim();
      const body = document.getElementById('newDraftBody').value.trim();
      if (!to || !subject || !body) return;

      try {
        const resp = await fetch('/api/gmail/drafts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ to, subject, body }),
        });
        if (resp.ok) {
          document.getElementById('newDraftTo').value = '';
          document.getElementById('newDraftSubject').value = '';
          document.getElementById('newDraftBody').value = '';
          showToast('Draft created! Ready for review & approval.', 'success');
          loadDrafts();
        } else {
          showToast('Failed to create draft', 'error');
        }
      } catch (err) {
        showToast('Error creating draft: ' + err.message, 'error');
      }
    });
  }

  if (refreshDraftsBtn) {
    refreshDraftsBtn.addEventListener('click', () => {
      loadDrafts();
      showToast('Drafts refreshed', 'info');
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 13. WEATHER INTEGRATION
  // ══════════════════════════════════════════════════════════════════════════
  const weatherForm = document.getElementById('weatherForm');
  const weatherCityInput = document.getElementById('weatherCityInput');
  const weatherCityName = document.getElementById('weatherCityName');
  const weatherCondition = document.getElementById('weatherCondition');
  const weatherTemp = document.getElementById('weatherTemp');
  const weatherFeelsLike = document.getElementById('weatherFeelsLike');
  const weatherHumidity = document.getElementById('weatherHumidity');
  const weatherWind = document.getElementById('weatherWind');
  const weatherOutdoorBadge = document.getElementById('weatherOutdoorBadge');
  const weatherSourceBadge = document.getElementById('weatherSourceBadge');
  const weatherRecommendationText = document.getElementById('weatherRecommendationText');
  const planTodayBtn = document.getElementById('planTodayBtn');
  const planTomorrowBtn = document.getElementById('planTomorrowBtn');

  async function loadWeather(city = null) {
    const targetCity = city || (weatherCityInput ? weatherCityInput.value.trim() : 'Bengaluru');
    try {
      const resp = await fetch(`/api/weather?city=${encodeURIComponent(targetCity)}`);
      if (!resp.ok) throw new Error('Weather fetch returned non-200');
      const data = await resp.json();

      if (weatherCityName) weatherCityName.textContent = data.city;
      if (weatherCondition) weatherCondition.textContent = data.condition;
      if (weatherTemp) weatherTemp.textContent = `${data.temperature_c}°C`;
      if (weatherFeelsLike) weatherFeelsLike.textContent = `Feels like ${data.feels_like_c}°C`;
      if (weatherHumidity) weatherHumidity.textContent = `${data.humidity_pct}%`;
      if (weatherWind) weatherWind.textContent = `${data.wind_kmh} km/h`;

      if (weatherOutdoorBadge) {
        if (data.suitable_for_outdoor) {
          weatherOutdoorBadge.textContent = 'Favorable Outdoors';
          weatherOutdoorBadge.className = 'status-chip success';
        } else {
          weatherOutdoorBadge.textContent = 'Indoor Focus Recommended';
          weatherOutdoorBadge.className = 'status-chip';
          weatherOutdoorBadge.style.color = '#fbbf24';
        }
      }

      if (weatherSourceBadge) {
        weatherSourceBadge.textContent = data.live_api_active ? 'Live OpenWeatherMap API' : 'Zero-Cost Fallback Engine';
      }

      if (weatherRecommendationText) {
        weatherRecommendationText.textContent = data.activity_recommendation;
      }
    } catch (err) {
      if (weatherCondition) weatherCondition.textContent = 'Weather Unavailable';
      if (weatherRecommendationText) weatherRecommendationText.textContent = 'Could not retrieve weather: ' + err.message;
    }
  }

  if (weatherForm) {
    weatherForm.addEventListener('submit', (e) => {
      e.preventDefault();
      loadWeather(weatherCityInput.value.trim());
    });
  }

  function triggerPlanPrompt(promptText) {
    const chatTabBtn = document.querySelector('.nav-item[data-tab="chat"]');
    if (chatTabBtn) chatTabBtn.click();
    if (userInput) {
      userInput.value = promptText;
      chatForm.dispatchEvent(new Event('submit'));
    }
  }

  if (planTodayBtn) {
    planTodayBtn.addEventListener('click', () => {
      triggerPlanPrompt('Plan my day today based on my pending tasks, calendar events, and weather.');
    });
  }

  if (planTomorrowBtn) {
    planTomorrowBtn.addEventListener('click', () => {
      triggerPlanPrompt('Plan my day tomorrow based on my pending tasks, calendar events, and weather.');
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 14. SMART DAY PLANNER TIMETABLE (Firestore Persisted)
  // ══════════════════════════════════════════════════════════════════════════
  const timetableContainer = document.getElementById('timetableContainer');
  const timetableStatusBadge = document.getElementById('timetableStatusBadge');
  const planTimestamp = document.getElementById('planTimestamp');
  const planSavedStatus = document.getElementById('planSavedStatus');
  const regeneratePlanBtn = document.getElementById('regeneratePlanBtn');
  const savedPlansSelect = document.getElementById('savedPlansSelect');
  const planHistoryCount = document.getElementById('planHistoryCount');

  function renderTimetableBlocks(data) {
    if (!timetableContainer) return;
    latestPlanMarkdown = data.formatted_markdown || data.plan || '';

    if (timetableStatusBadge) {
      const meetings = data.scheduled_events_count !== undefined ? data.scheduled_events_count : (data.scheduled_events ? data.scheduled_events.length : 0);
      const tasks = data.pending_tasks_count !== undefined ? data.pending_tasks_count : (data.prioritized_tasks ? data.prioritized_tasks.length : 0);
      timetableStatusBadge.textContent = `${meetings} Meeting(s) • ${tasks} Task(s)`;
    }

    if (planTimestamp) {
      const timeStr = data.updated_at
        ? new Date(data.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : 'Just now';
      const dateStr = data.target_date || data.date || 'Today';
      planTimestamp.textContent = `Saved at ${timeStr} (${dateStr})`;
    }

    if (planSavedStatus) {
      planSavedStatus.textContent = '☁️ Firestore Persisted';
      planSavedStatus.style.color = '#34d399';
    }

    const timetable = data.timetable || [];
    if (!timetable || timetable.length === 0) {
      // If plan is raw markdown/text
      if (data.formatted_markdown || data.plan) {
        timetableContainer.innerHTML = `
          <div style="padding:14px;background:var(--bg-surface-elevated);border-radius:10px;font-size:0.86rem;line-height:1.5;white-space:pre-wrap;color:var(--text-primary);border:1px solid var(--border-subtle);">
            ${formatMarkdown(data.formatted_markdown || data.plan)}
          </div>
        `;
        return;
      }
      timetableContainer.innerHTML = '<p class="empty-state">No timetable blocks generated for this day.</p>';
      return;
    }

    timetableContainer.innerHTML = timetable.map((block) => `
      <div style="display:flex;gap:12px;align-items:flex-start;padding:12px 14px;border-radius:10px;background:var(--bg-surface-elevated);border-left:3px solid #3b82f6;">
        <div style="font-weight:700;font-family:monospace;font-size:0.88rem;min-width:96px;color:#93c5fd;">
          ${block.time_range}
        </div>
        <div style="flex:1;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">
            <strong style="color:#fff;font-size:0.92rem;">${block.title}</strong>
            <span class="status-chip highlight">${(block.activity_type || 'FOCUS').toUpperCase()}</span>
          </div>
          <p style="margin:0;font-size:0.8rem;color:var(--text-secondary);">${block.description}</p>
        </div>
      </div>
    `).join('');
  }

  async function loadPlanHistory() {
    if (!savedPlansSelect) return;
    try {
      const resp = await fetch('/api/planner/history?limit=10');
      if (!resp.ok) return;
      const data = await resp.json();
      const plans = data.plans || [];

      if (planHistoryCount) {
        planHistoryCount.textContent = `${plans.length} saved plan(s) in Firestore`;
      }

      savedPlansSelect.innerHTML = '<option value="">Today\'s Saved Plan</option>';
      plans.forEach((p) => {
        const opt = document.createElement('option');
        opt.value = p.date;
        const timePart = p.updated_at ? new Date(p.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
        opt.textContent = `${p.date} (${timePart || 'Saved'})`;
        savedPlansSelect.appendChild(opt);
      });
    } catch (err) {
      console.warn('Could not load plan history:', err);
    }
  }

  async function loadTimetable(targetDate = null, forceGenerate = false) {
    if (!timetableContainer) return;

    // 1. Try to load saved plan from Firestore first (₹0 API cost)
    if (!forceGenerate) {
      try {
        const queryUrl = targetDate ? `/api/planner?date=${encodeURIComponent(targetDate)}` : '/api/planner/today';
        const getResp = await fetch(queryUrl);
        if (getResp.ok) {
          const res = await getResp.json();
          if (res.saved && res.plan) {
            renderTimetableBlocks(res.plan);
            loadPlanHistory();
            return;
          }
        }
      } catch (err) {
        console.warn('Saved plan lookup skipped:', err);
      }
    }

    // 2. If not saved or explicitly regenerating: generate fresh & save in Firestore
    try {
      if (timetableContainer) {
        timetableContainer.innerHTML = '<p class="empty-state">Synthesizing timetable & syncing with Firestore...</p>';
      }
      const payload = {};
      if (targetDate) payload.target_date = targetDate;
      const resp = await fetch('/api/planner/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error('Planner synthesis failed');
      const data = await resp.json();
      renderTimetableBlocks(data);
      loadPlanHistory();
    } catch (err) {
      timetableContainer.innerHTML = `<p style="color:#ef4444;">Error loading timetable: ${err.message}</p>`;
    }
  }

  if (regeneratePlanBtn) {
    regeneratePlanBtn.addEventListener('click', async () => {
      const selectedDate = savedPlansSelect ? savedPlansSelect.value : null;
      showToast('Regenerating daily plan...', 'info');
      await loadTimetable(selectedDate, true);
      showToast('Fresh plan synthesized & saved to Firestore!', 'success');
    });
  }

  if (savedPlansSelect) {
    savedPlansSelect.addEventListener('change', (e) => {
      const chosenDate = e.target.value;
      loadTimetable(chosenDate || null, false);
    });
  }

  if (planTodayBtn) {
    planTodayBtn.addEventListener('click', () => {
      loadTimetable(null, true);
      showToast('Generating today\'s plan...', 'info');
    });
  }

  if (planTomorrowBtn) {
    planTomorrowBtn.addEventListener('click', () => {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      const tomorrowStr = tomorrow.toISOString().split('T')[0];
      loadTimetable(tomorrowStr, true);
      showToast('Generating tomorrow\'s plan...', 'info');
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 14B. USER-EDITABLE TIMETABLE & WEEKLY REPLICATION
  // ══════════════════════════════════════════════════════════════════════════
  const ttDaysBar = document.getElementById('ttDaysBar');
  const userTimetableBlocksList = document.getElementById('userTimetableBlocksList');
  const addTimeBlockForm = document.getElementById('addTimeBlockForm');
  const ttToggleAddFormBtn = document.getElementById('ttToggleAddFormBtn');
  const ttCancelAddBtn = document.getElementById('ttCancelAddBtn');
  const ttApplyWeekBtn = document.getElementById('ttApplyWeekBtn');
  const ttApplyWeekdaysBtn = document.getElementById('ttApplyWeekdaysBtn');

  let activeTimetableDay = 'monday';
  let userWeeklyTimetableData = null;

  async function loadUserTimetable(dayToSelect = null) {
    if (!userTimetableBlocksList) return;
    try {
      const resp = await fetch('/api/timetable');
      if (!resp.ok) throw new Error('Could not fetch timetable');
      const data = await resp.json();
      userWeeklyTimetableData = data.days || {};

      if (dayToSelect) {
        activeTimetableDay = dayToSelect.toLowerCase();
      } else if (!activeTimetableDay || activeTimetableDay === 'monday') {
        const dayNames = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
        const todayDay = dayNames[new Date().getDay()];
        if (dayToSelect === null) activeTimetableDay = todayDay;
      }

      // Update active day pill
      if (ttDaysBar) {
        ttDaysBar.querySelectorAll('.tt-day-pill').forEach((pill) => {
          if (pill.getAttribute('data-day') === activeTimetableDay) {
            pill.classList.add('active');
          } else {
            pill.classList.remove('active');
          }
        });
      }

      renderUserDayBlocks(userWeeklyTimetableData[activeTimetableDay] || []);
    } catch (err) {
      userTimetableBlocksList.innerHTML = `<p style="color:#ef4444;font-size:0.8rem;">Error loading timetable: ${escapeHtml(err.message)}</p>`;
    }
  }

  function renderUserDayBlocks(blocks) {
    if (!userTimetableBlocksList) return;
    if (!blocks || blocks.length === 0) {
      userTimetableBlocksList.innerHTML = `
        <div class="empty-state" style="padding:18px 0;">
          <p>No time blocks scheduled for ${activeTimetableDay.toUpperCase()}.</p>
          <button type="button" class="secondary-btn btn-sm" onclick="document.getElementById('ttToggleAddFormBtn').click()" style="margin-top:8px;">+ Add First Block</button>
        </div>
      `;
      return;
    }

    userTimetableBlocksList.innerHTML = blocks.map((b) => {
      const cat = (b.category || 'focus').toLowerCase();
      return `
        <div class="tt-block-item cat-${cat}">
          <div class="tt-block-left">
            <span class="tt-block-time">${escapeHtml(b.start_time)} - ${escapeHtml(b.end_time)}</span>
            <div>
              <div class="tt-block-title">${escapeHtml(b.title)}</div>
            </div>
          </div>
          <div class="tt-block-meta">
            <span class="tt-cat-badge">${cat.toUpperCase()}</span>
            <button type="button" class="tt-del-btn" onclick="deleteUserBlock('${activeTimetableDay}', '${b.id}')" title="Delete block">✕ Delete</button>
          </div>
        </div>
      `;
    }).join('');
  }

  window.deleteUserBlock = async (day, blockId) => {
    if (!confirm('Remove this time block?')) return;
    try {
      const resp = await fetch(`/api/timetable/${encodeURIComponent(day)}/${encodeURIComponent(blockId)}`, {
        method: 'DELETE'
      });
      if (!resp.ok) throw new Error('Deletion failed');
      showToast('Time block removed', 'info');
      await loadUserTimetable(day);
    } catch (e) {
      showToast('Error removing block: ' + e.message, 'error');
    }
  };

  if (ttDaysBar) {
    ttDaysBar.querySelectorAll('.tt-day-pill').forEach((pill) => {
      pill.addEventListener('click', () => {
        const day = pill.getAttribute('data-day');
        if (day) {
          activeTimetableDay = day;
          ttDaysBar.querySelectorAll('.tt-day-pill').forEach((p) => p.classList.remove('active'));
          pill.classList.add('active');
          if (userWeeklyTimetableData) {
            renderUserDayBlocks(userWeeklyTimetableData[activeTimetableDay] || []);
          } else {
            loadUserTimetable(day);
          }
        }
      });
    });
  }

  if (ttToggleAddFormBtn) {
    ttToggleAddFormBtn.addEventListener('click', () => {
      if (addTimeBlockForm) {
        const isHidden = addTimeBlockForm.style.display === 'none';
        addTimeBlockForm.style.display = isHidden ? 'block' : 'none';
        if (isHidden) {
          const s = document.getElementById('ttNewStart');
          if (s) s.focus();
        }
      }
    });
  }

  if (ttCancelAddBtn) {
    ttCancelAddBtn.addEventListener('click', () => {
      if (addTimeBlockForm) addTimeBlockForm.style.display = 'none';
    });
  }

  if (addTimeBlockForm) {
    addTimeBlockForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const start = document.getElementById('ttNewStart').value;
      const end = document.getElementById('ttNewEnd').value;
      const title = document.getElementById('ttNewTitle').value.trim();
      const cat = document.getElementById('ttNewCategory').value;

      if (!start || !end || !title) return;

      const currentBlocks = (userWeeklyTimetableData && userWeeklyTimetableData[activeTimetableDay]) ? [...userWeeklyTimetableData[activeTimetableDay]] : [];
      currentBlocks.push({
        start_time: start,
        end_time: end,
        title: title,
        category: cat
      });

      try {
        const resp = await fetch('/api/timetable', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            day: activeTimetableDay,
            blocks: currentBlocks,
            apply_to_week: false
          })
        });
        if (!resp.ok) throw new Error('Failed to save time block');
        showToast(`Time block added to ${activeTimetableDay.toUpperCase()}!`, 'success');
        addTimeBlockForm.reset();
        addTimeBlockForm.style.display = 'none';
        await loadUserTimetable(activeTimetableDay);
      } catch (err) {
        showToast('Error saving block: ' + err.message, 'error');
      }
    });
  }

  if (ttApplyWeekBtn) {
    ttApplyWeekBtn.addEventListener('click', async () => {
      if (!confirm(`Copy ${activeTimetableDay.toUpperCase()}'s time blocks across all 7 days of the week?`)) return;
      const currentBlocks = (userWeeklyTimetableData && userWeeklyTimetableData[activeTimetableDay]) || [];
      try {
        const resp = await fetch('/api/timetable', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            day: activeTimetableDay,
            blocks: currentBlocks,
            apply_to_week: true
          })
        });
        if (!resp.ok) throw new Error('Week replication failed');
        showToast('Timetable applied across entire week!', 'success');
        await loadUserTimetable(activeTimetableDay);
      } catch (e) {
        showToast('Error replicating week: ' + e.message, 'error');
      }
    });
  }

  if (ttApplyWeekdaysBtn) {
    ttApplyWeekdaysBtn.addEventListener('click', async () => {
      if (!confirm(`Copy ${activeTimetableDay.toUpperCase()}'s schedule to all weekdays (Mon–Fri)?`)) return;
      const currentBlocks = (userWeeklyTimetableData && userWeeklyTimetableData[activeTimetableDay]) || [];
      try {
        const resp = await fetch('/api/timetable', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            day: activeTimetableDay,
            blocks: currentBlocks,
            apply_to_week: false,
            days: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
          })
        });
        if (!resp.ok) throw new Error('Weekday replication failed');
        showToast('Timetable applied to Monday–Friday!', 'success');
        await loadUserTimetable(activeTimetableDay);
      } catch (e) {
        showToast('Error replicating weekdays: ' + e.message, 'error');
      }
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 15. MULTI-USER GOOGLE AUTHENTICATION & PROFILE
  // ══════════════════════════════════════════════════════════════════════════
  const loginModal = document.getElementById('loginModal');
  const userProfileCard = document.getElementById('userProfileCard');
  const userAvatar = document.getElementById('userAvatar');
  const userName = document.getElementById('userName');
  const userEmail = document.getElementById('userEmail');
  const guestLoginBtn = document.getElementById('guestLoginBtn');

  async function checkAuth() {
    try {
      const res = await fetch('/auth/me');
      if (res.ok) {
        const data = await res.json();
        if (data.authenticated) {
          if (loginModal) loginModal.style.display = 'none';
          if (userProfileCard) userProfileCard.style.display = 'flex';
          if (userName) userName.textContent = data.name || 'User';
          if (userEmail) userEmail.textContent = data.email || '';
          if (userAvatar) {
            if (data.picture) {
              userAvatar.innerHTML = `<img src="${data.picture}" alt="${data.name || 'User'}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">`;
            } else {
              userAvatar.textContent = (data.name || data.email || 'U').charAt(0).toUpperCase();
            }
          }
          return true;
        }
      }
    } catch (err) {
      console.warn('Auth status check error:', err);
    }

    if (loginModal) loginModal.style.display = 'flex';
    if (userProfileCard) userProfileCard.style.display = 'none';
    return false;
  }

  if (guestLoginBtn) {
    guestLoginBtn.addEventListener('click', async () => {
      try {
        const res = await fetch('/auth/guest', { method: 'POST' });
        if (res.ok || res.redirected) {
          showToast('Signed in as Guest (Offline ₹0)', 'success');
          await checkAuth();
          loadTasks();
          loadNotes();
          loadAllCalendarData();
          loadDrafts();
        }
      } catch (e) {
        showToast('Guest sign-in error: ' + e.message, 'error');
      }
    });
  }

  // Initial Preloads
  switchCalendarView('upcoming');
  renderCalendarMonth(calCurrentYear, calCurrentMonth);
  fetchMonthIndicators(calCurrentYear, calCurrentMonth);
  loadAllCalendarData();
  loadWeather();
  loadTimetable();
  loadUserTimetable();
  loadTasks();
  loadNotes();
  loadDrafts();
  checkAuth();
  updateChatDockState();

  // Auto-resize / Enter to submit textarea & Focus Glow States
  if (userInput) {
    userInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event('submit'));
      }
    });

    if (auraGlowWrapper) {
      userInput.addEventListener('focus', () => {
        auraGlowWrapper.classList.add('is-focused');
      });
      userInput.addEventListener('blur', () => {
        auraGlowWrapper.classList.remove('is-focused');
      });
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 16. INTERACTIVE CURSOR SPOTLIGHT (60fps Lerp Interpolation)
  // ══════════════════════════════════════════════════════════════════════════
  const spotlight = document.getElementById('cursorSpotlight');
  if (spotlight) {
    let targetX = window.innerWidth / 2;
    let targetY = window.innerHeight / 2;
    let currentX = targetX;
    let currentY = targetY;
    let rafId = null;

    function renderSpotlight() {
      // Smooth linear interpolation (lerp)
      currentX += (targetX - currentX) * 0.12;
      currentY += (targetY - currentY) * 0.12;
      spotlight.style.transform = `translate3d(${currentX}px, ${currentY}px, 0) translate3d(-50%, -50%, 0)`;

      if (Math.abs(targetX - currentX) > 0.15 || Math.abs(targetY - currentY) > 0.15) {
        rafId = requestAnimationFrame(renderSpotlight);
      } else {
        rafId = null;
      }
    }

    window.addEventListener('mousemove', (e) => {
      targetX = e.clientX;
      targetY = e.clientY;
      spotlight.style.opacity = '1';
      if (!rafId) {
        rafId = requestAnimationFrame(renderSpotlight);
      }
    }, { passive: true });

    document.addEventListener('mouseleave', () => {
      spotlight.style.opacity = '0';
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 17. SMART REMINDERS & DUE ALERTS SYSTEM
  // ══════════════════════════════════════════════════════════════════════════
  const reminderBellBtn = document.getElementById('reminderBellBtn');
  const floatingReminderBellBtn = document.getElementById('floatingReminderBellBtn');
  const reminderBadge = document.getElementById('reminderBadge');
  const floatingReminderBadge = document.getElementById('floatingReminderBadge');
  const remindersDrawer = document.getElementById('remindersDrawer');
  const remindersOverlay = document.getElementById('remindersOverlay');
  const closeRemindersDrawer = document.getElementById('closeRemindersDrawer');
  const quickReminderForm = document.getElementById('quickReminderForm');
  const activeRemindersList = document.getElementById('activeRemindersList');
  const pastRemindersList = document.getElementById('pastRemindersList');
  const activeRemindersCount = document.getElementById('activeRemindersCount');

  const alertedReminderIds = new Set();
  let reminderAudioCtx = null;

  function initReminderAudio() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      if (!reminderAudioCtx) {
        reminderAudioCtx = new AudioCtx();
      }
      if (reminderAudioCtx.state === 'suspended') {
        reminderAudioCtx.resume();
      }
    } catch (e) {
      console.debug('Audio init error:', e);
    }
  }

  // Pre-unlock audio on any user gesture anywhere on the page
  document.addEventListener('click', initReminderAudio, { passive: true });
  document.addEventListener('keydown', initReminderAudio, { passive: true });

  function playReminderChime() {
    try {
      initReminderAudio();
      const ctx = reminderAudioCtx;
      if (!ctx) return;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(1320, ctx.currentTime + 0.15);
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.45);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.46);
    } catch (e) {
      console.debug('Audio chime error:', e);
    }
  }

  const drawerNotifPermBar = document.getElementById('drawerNotifPermBar');
  const drawerNotifIcon = document.getElementById('drawerNotifIcon');
  const drawerNotifText = document.getElementById('drawerNotifText');
  const enableDesktopNotifBtn = document.getElementById('enableDesktopNotifBtn');

  function updateNotificationPermUI() {
    if (!drawerNotifPermBar) return;
    if (typeof Notification === 'undefined') {
      drawerNotifPermBar.style.display = 'none';
      return;
    }
    const perm = Notification.permission;
    if (perm === 'granted') {
      drawerNotifPermBar.className = 'drawer-notification-perm-bar is-granted';
      if (drawerNotifIcon) drawerNotifIcon.textContent = '✓';
      if (drawerNotifText) drawerNotifText.textContent = 'Desktop notifications are active with sound & system popups.';
      if (enableDesktopNotifBtn) {
        enableDesktopNotifBtn.style.display = 'none';
      }
    } else if (perm === 'denied') {
      drawerNotifPermBar.className = 'drawer-notification-perm-bar is-denied';
      if (drawerNotifIcon) drawerNotifIcon.textContent = '⚠️';
      if (drawerNotifText) drawerNotifText.textContent = 'Desktop notifications blocked by browser. Click lock icon in URL bar to allow.';
      if (enableDesktopNotifBtn) {
        enableDesktopNotifBtn.style.display = 'none';
      }
    } else {
      drawerNotifPermBar.className = 'drawer-notification-perm-bar';
      if (drawerNotifIcon) drawerNotifIcon.textContent = '🔔';
      if (drawerNotifText) drawerNotifText.textContent = 'Enable desktop notifications for alerts when Synaptix is minimized.';
      if (enableDesktopNotifBtn) {
        enableDesktopNotifBtn.style.display = 'inline-block';
        enableDesktopNotifBtn.textContent = 'Enable Alerts';
      }
    }
  }

  function requestNotificationPermission() {
    initReminderAudio();
    if (typeof Notification !== 'undefined') {
      if (Notification.permission === 'default') {
        Notification.requestPermission().then((perm) => {
          updateNotificationPermUI();
          if (perm === 'granted') {
            showToast('Desktop notifications enabled!', 'success');
            try {
              new Notification('⏰ Synaptix Reminders Active', {
                body: 'You will receive timely alerts for tasks, notes, and events!',
              });
            } catch (e) {}
          }
        }).catch(() => {});
      } else {
        updateNotificationPermUI();
      }
    }
  }

  if (enableDesktopNotifBtn) {
    enableDesktopNotifBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      requestNotificationPermission();
    });
  }

  // Request browser permission proactively on user interaction
  document.addEventListener('click', requestNotificationPermission, { once: true });
  if (userInput) {
    userInput.addEventListener('focus', requestNotificationPermission, { once: true });
  }

  function formatReminderTime(isoStr) {
    if (!isoStr) return 'Unset time';
    try {
      const dt = new Date(isoStr);
      const now = new Date();
      const diffMs = dt - now;
      const isPast = diffMs < 0;

      const timeStr = dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const isToday = dt.toDateString() === now.toDateString();
      const tomorrow = new Date();
      tomorrow.setDate(now.getDate() + 1);
      const isTomorrow = dt.toDateString() === tomorrow.toDateString();

      if (isPast) {
        return `⚠️ Overdue (${dt.toLocaleDateString([], { month: 'short', day: 'numeric' })} ${timeStr})`;
      } else if (isToday) {
        return `Today at ${timeStr}`;
      } else if (isTomorrow) {
        return `Tomorrow at ${timeStr}`;
      } else {
        return `${dt.toLocaleDateString([], { month: 'short', day: 'numeric' })} at ${timeStr}`;
      }
    } catch {
      return isoStr;
    }
  }

  function updateRemindersBadge(count) {
    [reminderBadge, floatingReminderBadge].forEach((b) => {
      if (!b) return;
      if (count > 0) {
        b.textContent = count;
        b.style.display = 'flex';
      } else {
        b.style.display = 'none';
      }
    });
  }

  function openRemindersDrawerFunc() {
    updateNotificationPermUI();
    requestNotificationPermission();
    if (remindersDrawer) remindersDrawer.classList.add('is-open');
    if (remindersOverlay) remindersOverlay.style.display = 'block';
    loadReminders();
  }

  function closeRemindersDrawerFunc() {
    if (remindersDrawer) remindersDrawer.classList.remove('is-open');
    if (remindersOverlay) remindersOverlay.style.display = 'none';
  }

  if (reminderBellBtn) reminderBellBtn.addEventListener('click', openRemindersDrawerFunc);
  if (floatingReminderBellBtn) floatingReminderBellBtn.addEventListener('click', openRemindersDrawerFunc);
  if (closeRemindersDrawer) closeRemindersDrawer.addEventListener('click', closeRemindersDrawerFunc);
  if (remindersOverlay) remindersOverlay.addEventListener('click', closeRemindersDrawerFunc);

  async function loadReminders() {
    try {
      const res = await fetch('/api/reminders');
      if (!res.ok) return;
      const data = await res.json();
      const reminders = data.reminders || [];

      const active = reminders.filter((r) => r.status === 'pending' || r.status === 'snoozed');
      const past = reminders.filter((r) => r.status === 'dismissed' || r.status === 'triggered');

      if (activeRemindersCount) activeRemindersCount.textContent = active.length;

      // Render Active Reminders
      if (activeRemindersList) {
        if (active.length === 0) {
          activeRemindersList.innerHTML = '<p class="empty-state">No upcoming reminders.</p>';
        } else {
          const nowIso = new Date().toISOString();
          activeRemindersList.innerHTML = active.map((r) => {
            const isDue = r.remind_at <= nowIso;
            const typeClass = (r.source_type || 'custom').toLowerCase();
            return `
              <div class="reminder-card ${isDue ? 'is-due' : ''}" id="rem-card-${r.id}">
                <div class="reminder-card-top">
                  <span class="reminder-card-title">${escapeHtml(r.title)}</span>
                  <span class="reminder-badge-type ${typeClass}">${r.source_type || 'Custom'}</span>
                </div>
                <div class="reminder-card-time">
                  <span>⏱ ${formatReminderTime(r.remind_at)}</span>
                  ${r.status === 'snoozed' ? '<span style="color:var(--glow-orange);font-weight:600;margin-left:6px;">(Snoozed)</span>' : ''}
                </div>
                <div class="reminder-card-actions">
                  <button class="rem-btn rem-snooze" onclick="snoozeReminderItem('${r.id}', 10)">+10m Snooze</button>
                  <button class="rem-btn rem-dismiss" onclick="dismissReminderItem('${r.id}')">✓ Dismiss</button>
                  <button class="rem-btn rem-delete" onclick="deleteReminderItem('${r.id}')" title="Delete">✕</button>
                </div>
              </div>
            `;
          }).join('');
        }
      }

      // Render Past Reminders
      if (pastRemindersList) {
        if (past.length === 0) {
          pastRemindersList.innerHTML = '<p class="empty-state">No past reminders.</p>';
        } else {
          pastRemindersList.innerHTML = past.slice(0, 10).map((r) => `
            <div class="reminder-card" style="opacity:0.65;">
              <div class="reminder-card-top">
                <span class="reminder-card-title">${escapeHtml(r.title)}</span>
                <span style="font-size:0.7rem;color:var(--text-muted);text-transform:capitalize;">${r.status}</span>
              </div>
              <div class="reminder-card-time">
                <span>Completed / Dismissed</span>
              </div>
              <div class="reminder-card-actions">
                <button class="rem-btn rem-delete" onclick="deleteReminderItem('${r.id}')" title="Delete">✕</button>
              </div>
            </div>
          `).join('');
        }
      }
    } catch (err) {
      console.warn('Failed to load reminders:', err);
    }
  }

  function showReminderToast(reminder) {
    // 1. Play subtle chime sound
    playReminderChime();

    // 2. Desktop Browser Notification
    if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
      try {
        new Notification('⏰ Synaptix Reminder', {
          body: reminder.title,
          requireInteraction: true,
        });
      } catch (e) {
        console.debug('Browser notification error:', e);
      }
    }

    // 3. In-App Dark Aura Toast Alert
    if (!toastContainer) return;
    const existing = document.getElementById(`reminder-toast-${reminder.id}`);
    if (existing) return;

    const toast = document.createElement('div');
    toast.id = `reminder-toast-${reminder.id}`;
    toast.className = 'toast reminder-toast';
    toast.innerHTML = `
      <div class="reminder-toast-header">
        <span>⏰</span>
        <span>Smart Reminder Due</span>
      </div>
      <div class="reminder-toast-body">${escapeHtml(reminder.title)}</div>
      <div class="reminder-toast-actions">
        <button class="toast-btn toast-btn-snooze" data-id="${reminder.id}">Snooze 10m</button>
        <button class="toast-btn toast-btn-dismiss" data-id="${reminder.id}">Dismiss</button>
      </div>
    `;

    toast.querySelector('.toast-btn-snooze').addEventListener('click', async (e) => {
      e.stopPropagation();
      await snoozeReminderItem(reminder.id, 10);
      toast.remove();
    });

    toast.querySelector('.toast-btn-dismiss').addEventListener('click', async (e) => {
      e.stopPropagation();
      await dismissReminderItem(reminder.id);
      toast.remove();
    });

    toastContainer.appendChild(toast);
  }

  function showInlineChatReminderAlert(reminder) {
    if (!chatMessages) return;
    const existing = document.getElementById(`inline-rem-alert-${reminder.id}`);
    if (existing) return;

    const alertCard = document.createElement('div');
    alertCard.id = `inline-rem-alert-${reminder.id}`;
    alertCard.className = 'chat-reminder-alert-card';
    alertCard.innerHTML = `
      <div class="chat-rem-header">
        <div class="chat-rem-icon">⏰</div>
        <div class="chat-rem-meta">
          <span class="chat-rem-badge">Smart Reminder Due</span>
          <span class="chat-rem-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
        </div>
      </div>
      <div class="chat-rem-title">${escapeHtml(reminder.title)}</div>
      <div class="chat-rem-actions">
        <button type="button" class="chat-rem-btn chat-rem-snooze" onclick="snoozeReminderItem('${reminder.id}', 10); document.getElementById('inline-rem-alert-${reminder.id}')?.remove();">+10m Snooze</button>
        <button type="button" class="chat-rem-btn chat-rem-dismiss" onclick="dismissReminderItem('${reminder.id}'); document.getElementById('inline-rem-alert-${reminder.id}')?.remove();">✓ Dismiss</button>
      </div>
    `;

    chatMessages.appendChild(alertCard);
    chatMessages.scrollTo({ top: chatMessages.scrollHeight, behavior: 'smooth' });
  }

  async function pollDueReminders() {
    try {
      const nowIso = new Date().toISOString();
      const res = await fetch(`/api/reminders/due?now=${encodeURIComponent(nowIso)}`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.success && data.due_reminders) {
        updateRemindersBadge(data.due_reminders.length);
        data.due_reminders.forEach((r) => {
          if (!alertedReminderIds.has(r.id)) {
            alertedReminderIds.add(r.id);
            showReminderToast(r);
            showInlineChatReminderAlert(r);
          }
        });
      }
    } catch (err) {
      console.debug('Error polling due reminders:', err);
    }
  }

  window.snoozeReminderItem = async (reminderId, minutes = 10) => {
    try {
      const res = await fetch(`/api/reminders/${reminderId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'snoozed', snooze_minutes: minutes }),
      });
      if (res.ok) {
        showToast(`Reminder snoozed for ${minutes} minutes`, 'info');
        loadReminders();
        pollDueReminders();
      }
    } catch (err) {
      showToast('Failed to snooze reminder: ' + err.message, 'error');
    }
  };

  window.dismissReminderItem = async (reminderId) => {
    try {
      const res = await fetch(`/api/reminders/${reminderId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'dismissed' }),
      });
      if (res.ok) {
        showToast('Reminder dismissed', 'success');
        loadReminders();
        pollDueReminders();
      }
    } catch (err) {
      showToast('Failed to dismiss reminder: ' + err.message, 'error');
    }
  };

  window.deleteReminderItem = async (reminderId) => {
    if (!confirm('Delete this reminder?')) return;
    try {
      const res = await fetch(`/api/reminders/${reminderId}`, { method: 'DELETE' });
      if (res.ok) {
        showToast('Reminder deleted', 'info');
        loadReminders();
        pollDueReminders();
      }
    } catch (err) {
      showToast('Failed to delete reminder: ' + err.message, 'error');
    }
  };

  if (quickReminderForm) {
    quickReminderForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const title = document.getElementById('quickReminderTitle').value.trim();
      const timeVal = document.getElementById('quickReminderTime').value;
      if (!title || !timeVal) return;

      try {
        const remindAtIso = new Date(timeVal).toISOString();
        const res = await fetch('/api/reminders', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title, remind_at: remindAtIso, source_type: 'custom' }),
        });
        if (res.ok) {
          document.getElementById('quickReminderTitle').value = '';
          document.getElementById('quickReminderTime').value = '';
          showToast('Smart reminder scheduled!', 'success');
          loadReminders();
          pollDueReminders();
        } else {
          showToast('Failed to create reminder', 'error');
        }
      } catch (err) {
        showToast('Error creating reminder: ' + err.message, 'error');
      }
    });
  }

  // Initial Sessions & Reminders Load
  loadSessions();
  const savedSessionId = localStorage.getItem('synaptix_current_session_id');
  if (savedSessionId) {
    switchSession(savedSessionId);
  }

  loadReminders();
  pollDueReminders();
  setInterval(pollDueReminders, 10000);
});
