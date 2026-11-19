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
  // 2. SIDEBAR COLLAPSE & MOBILE DRAWER
  // ══════════════════════════════════════════════════════════════════════════
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
    });
  }

  if (mobileSidebarToggle && sidebar) {
    mobileSidebarToggle.addEventListener('click', () => {
      sidebar.classList.toggle('mobile-open');
    });
  }

  // Close mobile sidebar on backdrop click
  document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768 && sidebar && sidebar.classList.contains('mobile-open')) {
      if (!sidebar.contains(e.target) && !mobileSidebarToggle.contains(e.target)) {
        sidebar.classList.remove('mobile-open');
      }
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
      if (targetTab === 'calendar') loadCalendarEvents();
      if (targetTab === 'gmail') loadDrafts();
      if (targetTab === 'planner') {
        loadWeather();
        loadTimetable();
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
  // 6. MODE SELECTOR DROPDOWN
  // ══════════════════════════════════════════════════════════════════════════
  const modePlaceholders = {
    auto: 'How can I help you?',
    gmail: 'Draft an email to [person] about [topic]...',
    tasks: 'Add high-priority task [title] due [date]...',
    notes: 'Capture note: [title or content]...',
    calendar: 'Schedule a meeting with [person] tomorrow at 3pm...',
    planner: 'Plan my day today based on tasks and meetings...',
  };

  const modeAgentMap = {
    auto: 'Coordinator',
    gmail: 'GmailAgent',
    tasks: 'TaskAgent',
    notes: 'NotesAgent',
    calendar: 'CalendarAgent',
    planner: 'SmartDayPlannerAgent',
  };

  if (modeSelect) {
    modeSelect.addEventListener('change', () => {
      const mode = modeSelect.value;
      if (userInput) {
        userInput.placeholder = modePlaceholders[mode] || 'How can I help you?';
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

      try {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: query,
            session_id: currentSessionId,
            conversation_history: conversationHistory.slice(-6),
          }),
        });

        if (loadingElem) loadingElem.remove();

        if (response.status === 429) {
          const errData = await response.json();
          appendMessage(
            'Synaptix Guard',
            `⛔ **Daily Free-Tier Quota Limit Reached (HTTP 429)**\n\n${(errData.detail && errData.detail.message) || 'Operation paused to guarantee zero costs.'}`,
            false
          );
          return;
        }

        if (!response.ok) {
          const errData = await response.json();
          appendMessage(
            'Synaptix Error',
            `⚠️ Error (${response.status}): ${JSON.stringify(errData.detail || errData)}`,
            false
          );
          return;
        }

        const data = await response.json();
        currentSessionId = data.session_id || currentSessionId;

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

      } catch (err) {
        if (loadingElem) loadingElem.remove();
        appendMessage('Synaptix Error', `⚠️ Could not reach backend: ${err.message}`, false);
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

  // Clear Chat Button Handler
  if (clearChatBtn) {
    clearChatBtn.addEventListener('click', () => {
      if (chatMessages) chatMessages.innerHTML = '';
      conversationHistory.length = 0;
      currentSessionId = null;
      updateChatDockState();
      highlightAgent('Coordinator');
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
      if (!title) return;

      try {
        await fetch('/api/tasks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title, due_date: dueDate || null, priority }),
        });
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
      if (!content) return;

      const tags = tagsStr ? tagsStr.split(',').map((t) => t.trim().toLowerCase()) : [];

      try {
        await fetch('/api/notes', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content, title: title || null, tags }),
        });
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
  // 11. CALENDAR MCP MANAGEMENT
  // ══════════════════════════════════════════════════════════════════════════
  const calendarEventsContainer = document.getElementById('calendarEventsContainer');
  const createEventForm = document.getElementById('createEventForm');
  const checkConflictForm = document.getElementById('checkConflictForm');
  const calendarFilterDate = document.getElementById('calendarFilterDate');
  const conflictStatusBadge = document.getElementById('conflictStatusBadge');
  const conflictResultText = document.getElementById('conflictResultText');

  async function loadCalendarEvents(dateStr = '') {
    if (!calendarEventsContainer) return;
    try {
      const url = dateStr ? `/api/calendar/events?date=${encodeURIComponent(dateStr)}` : '/api/calendar/events';
      const resp = await fetch(url);
      const data = await resp.json();
      const events = data.events || [];

      if (events.length === 0) {
        calendarEventsContainer.innerHTML = '<p class="empty-state">No events scheduled.</p>';
        return;
      }

      calendarEventsContainer.innerHTML = events.map((e) => `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 14px;background:var(--bg-surface-elevated);border:1px solid var(--border-subtle);border-radius:10px;">
          <div>
            <div style="font-weight:600;font-size:0.92rem;color:#fff;">
              ${e.summary}
            </div>
            <div style="font-size:0.75rem;color:var(--text-secondary);margin-top:3px;">
              ⏱️ ${e.start_time.replace('T', ' ')} → ${e.end_time.replace('T', ' ')} ${e.location ? `• 📍 ${e.location}` : ''}
            </div>
          </div>
          <button onclick="deleteCalendarEventItem('${e.id}')" class="secondary-btn btn-sm" style="color:#f87171;">✕ Cancel</button>
        </div>
      `).join('');
    } catch (err) {
      calendarEventsContainer.innerHTML = `<p style="color:#ef4444;">Failed to load events: ${err.message}</p>`;
    }
  }

  window.deleteCalendarEventItem = async (eventId) => {
    if (!confirm('Cancel this event?')) return;
    try {
      await fetch(`/api/calendar/events/${eventId}`, { method: 'DELETE' });
      showToast('Event cancelled', 'info');
      loadCalendarEvents();
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
        loadCalendarEvents();
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
          conflictResultText.innerHTML = `Timeslot is clear from <strong>${start}</strong> to <strong>${end}</strong>.`;
        } else {
          conflictStatusBadge.textContent = `${data.conflicts_count} Conflict(s)`;
          conflictStatusBadge.className = 'status-chip';
          conflictStatusBadge.style.color = '#f87171';
          const confTitles = data.conflicting_events.map((c) => `• "${c.summary}"`).join('<br>');
          conflictResultText.innerHTML = `Overlaps with:<br>${confTitles}`;
        }
      } catch (err) {
        conflictResultText.textContent = 'Error checking availability: ' + err.message;
      }
    });
  }

  if (calendarFilterDate) {
    calendarFilterDate.addEventListener('change', (e) => {
      loadCalendarEvents(e.target.value);
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
          loadCalendarEvents();
          loadDrafts();
        }
      } catch (e) {
        showToast('Guest sign-in error: ' + e.message, 'error');
      }
    });
  }

  // Initial Preloads
  loadCalendarEvents();
  loadWeather();
  loadTimetable();
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
});
