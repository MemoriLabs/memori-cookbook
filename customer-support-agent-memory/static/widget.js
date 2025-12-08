/**
 * Customer Support AI Chat Widget
 *
 * This script creates an embeddable chat widget that can be int                <!-- Chat Window -->
                <div id="chat-window" style="display: none; width: 350px; height: 500px; min-width: 300px; min-height: 400px; max-width: 800px; max-height: 80vh; background: white; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.15); position: absolute; ${config.position.includes('right') ? 'right: 0;' : 'left: 0;'} bottom: 80px; flex-direction: column; overflow: hidden;")rated into any website
 * to provide AI-powered customer support using the backend API.
 *
 * Usage:
 * 1. Include this script in your HTML: <script src="https://your-api-domain.com/widget.js"></script>
 * 2. Initialize the widget: CustomerSupportWidget.init({ apiUrl: 'https://your-api-domain.com' });
 * 3. The chat widget will appear as a floating button on your website
 */

(function() {
    'use strict';

    // Widget configuration
    let config = {
        apiUrl: 'http://localhost:8000',
        domainId: null, // domain_id assigned by backend and provided to the widget
        position: 'bottom-right',
        primaryColor: '#007bff',
        secondaryColor: '#f8f9fa',
        textColor: '#333',
        widgetTitle: 'Customer Support',
        placeholder: 'Type your message...',
        welcomeMessage: 'Hi! How can I help you today?',
        autoScrape: true // Automatically scrape current website when starting session
    };

    let widget = null;
    let sessionId = null;
    let userId = null;
    let isOpen = false;
    let isLoading = false;
    let isExpanded = false; // Track widget size state

    // Widget size presets
    const widgetSizes = {
        default: { width: '350px', height: '500px' },
        expanded: { width: '500px', height: '650px' }
    };

    // Generate unique user ID
    function generateUserId() {
        return 'user_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    }

    // Get or create user ID from localStorage
    function getUserId() {
        if (!userId) {
            userId = localStorage.getItem('customerSupportUserId');
            if (!userId) {
                userId = generateUserId();
                localStorage.setItem('customerSupportUserId', userId);
            }
        }
        return userId;
    }

    // Get stored session ID from localStorage
    function getStoredSessionId() {
        return localStorage.getItem('customerSupportSessionId');
    }

    // Store session ID in localStorage
    function storeSessionId(sessionIdValue) {
        sessionId = sessionIdValue;
        localStorage.setItem('customerSupportSessionId', sessionIdValue);
    }

    // Clear stored session ID (for new sessions)
    function clearStoredSessionId() {
        sessionId = null;
        localStorage.removeItem('customerSupportSessionId');
    }

    // Get authorization headers
    function getAuthHeaders() {
        const headers = {
            'Content-Type': 'application/json',
        };

        // Use domainId to identify the site.
        if (config.domainId) {
            headers['X-Domain-ID'] = String(config.domainId);
        }

        return headers;
    }

    // Validate configuration
    function validateConfig() {
        if (!config.domainId) {
            console.error('CustomerSupportWidget: domainId is required. Please provide config.domainId or data-domain-id attribute');
            return false;
        }
        if (!config.apiUrl) {
            console.error('CustomerSupportWidget: API URL is required. Please provide config.apiUrl');
            return false;
        }
        return true;
    }

    // Create widget HTML structure
    function createWidget() {
        const widgetHTML = `
            <div id="customer-support-widget" style="position: fixed; ${config.position.includes('right') ? 'right: 20px;' : 'left: 20px;'} ${config.position.includes('bottom') ? 'bottom: 20px;' : 'top: 20px;'} z-index: 9999; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                <!-- Chat Button -->
                <div id="chat-button" style="width: 60px; height: 60px; background: ${config.primaryColor}; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.2); transition: all 0.3s ease;">
                    <svg width="24" height="24" fill="white" viewBox="0 0 24 24">
                        <path d="M20 2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h4l4 4 4-4h4c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z"/>
                    </svg>
                </div>

                <!-- Chat Window -->
                <div id="chat-window" style="display: none; width: 350px; height: 500px; background: white; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.15); position: absolute; ${config.position.includes('right') ? 'right: 0;' : 'left: 0;'} bottom: 80px; flex-direction: column; overflow: hidden;">
                    <!-- Header -->
                    <div style="background: ${config.primaryColor}; color: white; padding: 16px; display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <button id="resize-toggle-button" style="background: rgba(255,255,255,0.2); border: none; color: white; cursor: pointer; padding: 6px; border-radius: 4px; font-size: 12px; transition: background-color 0.2s;" title="Toggle widget size">
                                <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M10 10H8v4h4v-2h-2v-2zm4 4h2v-4h-4v2h2v2zm-4-8h2V4h4v2h2V4h-2V2h-4v2H8v2h2v2zm8 8v2h2v-2h-2zm0 4v2h-2v-2h2zm-4 0v2h-2v-2h2z"/>
                                </svg>
                            </button>
                            <h3 style="margin: 0; font-size: 16px; font-weight: 600;">${config.widgetTitle}</h3>
                        </div>
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <button id="new-session-button" style="background: rgba(255,255,255,0.2); border: none; color: white; cursor: pointer; padding: 6px 10px; border-radius: 4px; font-size: 12px; transition: background-color 0.2s;" title="Start new conversation">
                                <svg width="14" height="14" fill="currentColor" viewBox="0 0 24 24" style="margin-right: 4px;">
                                    <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
                                </svg>
                                New
                            </button>
                            <button id="close-chat" style="background: none; border: none; color: white; cursor: pointer; padding: 4px;">
                                <svg width="20" height="20" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                                </svg>
                            </button>
                        </div>
                    </div>

                    <!-- Messages Container -->
                    <div id="messages-container" style="flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; min-height: 200px;">
                        <div class="message bot-message" style="background: ${config.secondaryColor}; padding: 12px; border-radius: 12px; max-width: 80%; align-self: flex-start;">
                            ${config.welcomeMessage}
                        </div>
                    </div>

                    <!-- Loading Indicator -->
                    <div id="loading-indicator" style="display: none; padding: 8px 16px; font-size: 14px; color: #666;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <div style="width: 16px; height: 16px; border: 2px solid #ddd; border-top: 2px solid ${config.primaryColor}; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                            AI is typing...
                        </div>
                    </div>

                    <!-- Input Container -->
                    <div style="padding: 16px; border-top: 1px solid #eee; display: flex; gap: 8px; align-items: flex-end;">
                        <textarea id="message-input" placeholder="${config.placeholder}" style="flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 8px; outline: none; font-size: 14px; resize: none; min-height: 20px; max-height: 120px; overflow-y: auto; font-family: inherit; line-height: 1.4;"></textarea>
                        <button id="send-button" style="background: ${config.primaryColor}; color: white; border: none; padding: 12px 16px; border-radius: 8px; cursor: pointer; font-size: 14px; flex-shrink: 0;">Send</button>
                    </div>
                </div>
            </div>

            <style>
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }

                #customer-support-widget #chat-button:hover {
                    transform: scale(1.05);
                }

                #customer-support-widget .message {
                    margin-bottom: 8px;
                    word-wrap: break-word;
                    font-size: 14px;
                    line-height: 1.4;
                }

                #customer-support-widget .user-message {
                    background: ${config.primaryColor} !important;
                    color: white !important;
                    align-self: flex-end !important;
                    max-width: 80% !important;
                }

                #customer-support-widget .bot-message {
                    background: ${config.secondaryColor} !important;
                    color: ${config.textColor} !important;
                    align-self: flex-start !important;
                    max-width: 80% !important;
                }

                #customer-support-widget #message-input:focus {
                    border-color: ${config.primaryColor};
                }

                #customer-support-widget #send-button:hover {
                    opacity: 0.9;
                }

                #customer-support-widget #send-button:disabled {
                    opacity: 0.6;
                    cursor: not-allowed;
                }

                #customer-support-widget #new-session-button:hover {
                    background: rgba(255,255,255,0.3) !important;
                }

                #customer-support-widget #new-session-button:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }

                #customer-support-widget #resize-toggle-button:hover {
                    background: rgba(255,255,255,0.3) !important;
                }

                #customer-support-widget #resize-toggle-button:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }

                #customer-support-widget #chat-window {
                    overflow: hidden;
                    transition: width 0.3s ease, height 0.3s ease;
                }

                #customer-support-widget #message-input {
                    transition: height 0.1s ease;
                }

                #customer-support-widget #message-input::-webkit-scrollbar {
                    width: 4px;
                }

                #customer-support-widget #message-input::-webkit-scrollbar-track {
                    background: #f1f1f1;
                    border-radius: 2px;
                }

                #customer-support-widget #message-input::-webkit-scrollbar-thumb {
                    background: #c1c1c1;
                    border-radius: 2px;
                }

                #customer-support-widget #message-input::-webkit-scrollbar-thumb:hover {
                    background: #a1a1a1;
                }

                #customer-support-widget #messages-container::-webkit-scrollbar {
                    width: 6px;
                }

                #customer-support-widget #messages-container::-webkit-scrollbar-track {
                    background: #f8f9fa;
                    border-radius: 3px;
                }

                #customer-support-widget #messages-container::-webkit-scrollbar-thumb {
                    background: #dee2e6;
                    border-radius: 3px;
                }

                #customer-support-widget #messages-container::-webkit-scrollbar-thumb:hover {
                    background: #adb5bd;
                }
            </style>
        `;

        document.body.insertAdjacentHTML('beforeend', widgetHTML);
        widget = document.getElementById('customer-support-widget');

        // Attach event listeners
        attachEventListeners();
    }

    // Attach event listeners
    function attachEventListeners() {
        const chatButton = document.getElementById('chat-button');
        const closeButton = document.getElementById('close-chat');
        const newSessionButton = document.getElementById('new-session-button');
        const resizeToggleButton = document.getElementById('resize-toggle-button');
        const sendButton = document.getElementById('send-button');
        const messageInput = document.getElementById('message-input');

        chatButton.addEventListener('click', toggleChat);
        closeButton.addEventListener('click', closeChat);
        newSessionButton.addEventListener('click', handleNewSession);
        resizeToggleButton.addEventListener('click', toggleWidgetSize);
        sendButton.addEventListener('click', sendMessage);

        // Auto-resize textarea
        messageInput.addEventListener('input', autoResizeTextarea);

        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    // Toggle chat window
    function toggleChat() {
        if (isOpen) {
            closeChat();
        } else {
            openChat();
        }
    }

    // Open chat window
    async function openChat() {
        const chatWindow = document.getElementById('chat-window');
        chatWindow.style.display = 'flex';
        isOpen = true;

        // Check for stored session ID first
        if (!sessionId) {
            sessionId = getStoredSessionId();
            console.log('Retrieved stored sessionId:', sessionId);
        }

        // If we have a stored session, try to load its history first
        if (sessionId) {
            console.log('Loading conversation history for existing session:', sessionId);
            await loadConversationHistory();
        } else {
            // Only start a new session if we don't have a stored one
            console.log('No stored session found, starting new session');
            await startSession();
        }

        // Focus on input
        setTimeout(() => {
            const messageInput = document.getElementById('message-input');
            messageInput.focus();
            autoResizeTextarea(); // Ensure proper initial sizing
        }, 100);
    }

    // Close chat window
    function closeChat() {
        const chatWindow = document.getElementById('chat-window');
        chatWindow.style.display = 'none';
        isOpen = false;
    }

    // Handle new session button click
    async function handleNewSession() {
        if (isLoading) return; // Don't allow new session while loading

        // Clear stored session to start fresh
        clearStoredSessionId();

        // Clear messages container
        const messagesContainer = document.getElementById('messages-container');
        messagesContainer.innerHTML = '';

        // Start new session
        console.log('User clicked new session button');
        await startSession();
    }

    // Auto-resize textarea based on content
    function autoResizeTextarea() {
        const textarea = document.getElementById('message-input');
        if (!textarea) return;

        // Reset height to calculate new height
        textarea.style.height = 'auto';

        // Calculate new height based on scroll height
        const newHeight = Math.min(textarea.scrollHeight, 120); // Max height 120px
        const minHeight = 20; // Min height 20px

        textarea.style.height = Math.max(newHeight, minHeight) + 'px';
    }

    // Toggle widget size between default and expanded
    function toggleWidgetSize() {
        if (isLoading) return; // Don't allow resize while loading

        const chatWindow = document.getElementById('chat-window');
        const resizeToggleButton = document.getElementById('resize-toggle-button');

        if (!chatWindow || !resizeToggleButton) return;

        isExpanded = !isExpanded;

        const targetSize = isExpanded ? widgetSizes.expanded : widgetSizes.default;

        // Apply new size
        chatWindow.style.width = targetSize.width;
        chatWindow.style.height = targetSize.height;

        // Update button icon based on state
        const icon = resizeToggleButton.querySelector('svg');
        if (isExpanded) {
            // Icon for "shrink" state
            icon.innerHTML = '<path d="M4 4h6v2H6v4H4V4zm10 0h6v6h-2V6h-4V4zm-6 10H4v-6h2v4h4v2zm6 0v-2h4v-4h2v6h-6z"/>';
            resizeToggleButton.title = 'Shrink widget';
        } else {
            // Icon for "expand" state
            icon.innerHTML = '<path d="M10 10H8v4h4v-2h-2v-2zm4 4h2v-4h-4v2h2v2zm-4-8h2V4h4v2h2V4h-2V2h-4v2H8v2h2v2zm8 8v2h2v-2h-2zm0 4v2h-2v-2h2zm-4 0v2h-2v-2h2z"/>';
            resizeToggleButton.title = 'Expand widget';
        }

        console.log(`Widget ${isExpanded ? 'expanded' : 'shrunk'} to ${targetSize.width} x ${targetSize.height}`);
    }

    // Load conversation history
    async function loadConversationHistory() {
        try {
            console.log(`Loading conversation history for session: ${sessionId}, user: ${getUserId()}`);
            const response = await fetch(`${config.apiUrl}/sessions/${sessionId}/conversations?user_id=${getUserId()}`, {
                method: 'GET',
                headers: getAuthHeaders()
            });

            if (!response.ok) {
                if (response.status === 404) {
                    // Session not found, clear stored session and start new one
                    console.warn('Stored session not found, starting new session');
                    clearStoredSessionId();
                    await startSession();
                    return;
                }
                console.warn('Failed to load conversation history:', response.status);
                return;
            }

            const data = await response.json();
            console.log('Loaded conversation data:', data);

            // Clear existing messages except welcome message
            const messagesContainer = document.getElementById('messages-container');
            messagesContainer.innerHTML = '';

            // Add conversation history
            if (data.messages && data.messages.length > 0) {
                console.log(`Loading ${data.messages.length} messages from history`);
                data.messages.forEach(msg => {
                    addMessageToHistory(msg.content, msg.role === 'user' ? 'user' : 'bot');
                });
            } else {
                // Add welcome message if no history
                console.log('No conversation history found, showing welcome message');
                addMessageToHistory(config.welcomeMessage, 'bot');
            }

        } catch (error) {
            console.error('Error loading conversation history:', error);
            // Add welcome message on error
            const messagesContainer = document.getElementById('messages-container');
            if (messagesContainer.children.length === 0) {
                addMessageToHistory(config.welcomeMessage, 'bot');
            }
        }
    }

    // Add message to history (without scrolling animation)
    function addMessageToHistory(text, sender) {
        const messagesContainer = document.getElementById('messages-container');
        const messageDiv = document.createElement('div');

        messageDiv.className = `message ${sender}-message`;
        messageDiv.style.cssText = `
            padding: 12px;
            border-radius: 12px;
            max-width: 80%;
            word-wrap: break-word;
            font-size: 14px;
            line-height: 1.4;
            margin-bottom: 8px;
        `;

        if (sender === 'user') {
            messageDiv.style.cssText += `
                background: ${config.primaryColor};
                color: white;
                align-self: flex-end;
            `;
        } else {
            messageDiv.style.cssText += `
                background: ${config.secondaryColor};
                color: ${config.textColor};
                align-self: flex-start;
            `;
        }

        // Handle markdown-like formatting for bot messages
        if (sender === 'bot') {
            messageDiv.innerHTML = formatBotMessage(text);
        } else {
            messageDiv.textContent = text;
        }

        messagesContainer.appendChild(messageDiv);
    }

    // Start a new session
    async function startSession() {
        try {
            console.log('Starting new session for user:', getUserId());
            const websiteUrl = config.autoScrape ? window.location.origin : null;

            const response = await fetch(`${config.apiUrl}/session`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({
                    user_id: getUserId(),
                    website_url: websiteUrl
                })
            });

            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('Authentication failed. Please check your API key.');
                }
                throw new Error(`Failed to start session: ${response.status}`);
            }

            const data = await response.json();
            console.log('New session created:', data.session_id);
            storeSessionId(data.session_id);

            // For new sessions, just show welcome message (don't load history)
            const messagesContainer = document.getElementById('messages-container');
            messagesContainer.innerHTML = '';
            addMessageToHistory(config.welcomeMessage, 'bot');

        } catch (error) {
            console.error('Error starting session:', error);
            addMessage(`Sorry, there was an error starting the chat session: ${error.message}`, 'bot');
        }
    }

    // Send message
    async function sendMessage() {
        const messageInput = document.getElementById('message-input');
        const message = messageInput.value.trim();

        if (!message || isLoading) return;

        // Add user message to chat
        addMessage(message, 'user');
        messageInput.value = '';

        // Reset textarea height
        autoResizeTextarea();

        // Show loading
        setLoading(true);

        try {
            const response = await fetch(`${config.apiUrl}/ask`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({
                    question: message,
                    session_id: sessionId,
                    user_id: getUserId(),
                    website_context: window.location.href
                })
            });

            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('Authentication failed. Please check your API key.');
                }
                if (response.status === 503) {
                    // Agent is still deploying
                    const errorData = await response.json().catch(() => ({}));
                    const deploymentMessage = errorData.detail ||
                        "🚀 Our AI assistant is getting ready for you! This usually takes just 1-2 minutes. Please try asking your question again in a moment.";
                    addMessage(deploymentMessage, 'bot');
                    return; // Don't throw, just show the message
                }
                throw new Error(`Failed to send message: ${response.status}`);
            }

            const data = await response.json();
            addMessage(data.answer, 'bot');

        } catch (error) {
            console.error('Error sending message:', error);
            addMessage(`Sorry, there was an error processing your message: ${error.message}`, 'bot');
        } finally {
            setLoading(false);
        }
    }

    // Add message to chat (for new messages with scrolling)
    function addMessage(text, sender) {
        addMessageToHistory(text, sender);

        // Scroll to bottom for new messages
        const messagesContainer = document.getElementById('messages-container');
        setTimeout(() => {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }, 10);
    }

    // Format bot message (basic markdown support)
    function formatBotMessage(text) {
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code style="background: #f0f0f0; padding: 2px 4px; border-radius: 3px; font-family: monospace;">$1</code>')
            .replace(/\n/g, '<br>');
    }

    // Set loading state
    function setLoading(loading) {
        isLoading = loading;
        const loadingIndicator = document.getElementById('loading-indicator');
        const sendButton = document.getElementById('send-button');
        const newSessionButton = document.getElementById('new-session-button');
        const resizeToggleButton = document.getElementById('resize-toggle-button');

        if (loading) {
            loadingIndicator.style.display = 'block';
            sendButton.disabled = true;
            if (newSessionButton) newSessionButton.disabled = true;
            if (resizeToggleButton) resizeToggleButton.disabled = true;
        } else {
            loadingIndicator.style.display = 'none';
            sendButton.disabled = false;
            if (newSessionButton) newSessionButton.disabled = false;
            if (resizeToggleButton) resizeToggleButton.disabled = false;
        }
    }

    // Note: query parameters are parsed via URLSearchParams where needed; no custom parser required.

    // Try to read configuration from the <script> tag that loaded this file.
    function readScriptTagConfig() {
        try {
            // Find current script (the last script with src containing 'widget.js')
            const scripts = document.getElementsByTagName('script');
            for (let i = scripts.length - 1; i >= 0; i--) {
                const s = scripts[i];
                if (!s.src) continue;
                if (s.src.indexOf('widget.js') !== -1) {
                    const url = new URL(s.src, window.location.href);
                    // Use the native URLSearchParams to parse query params from the script src
                    const qp = {};
                    for (const [k, v] of url.searchParams.entries()) {
                        qp[k] = v;
                    }

                    const data = {};
                    // prefer data- attributes (kebab-case) then query params
                    if (s.dataset) {
                        // Primary identifier for server-side registration is domainId (X-Domain-ID)
                        if (s.dataset.domainId) data.domainId = s.dataset.domainId;
                        if (s.dataset.apiUrl) data.apiUrl = s.dataset.apiUrl;
                        if (s.dataset.primaryColor) data.primaryColor = s.dataset.primaryColor;
                        if (s.dataset.widgetTitle) data.widgetTitle = s.dataset.widgetTitle;
                        if (s.dataset.autoScrape) data.autoScrape = s.dataset.autoScrape === 'true';
                        if (s.dataset.position) data.position = s.dataset.position;
                    }

                    // fallback to query params
                    if (!data.domainId && qp.domainId) data.domainId = qp.domainId || qp['domain-id'];
                    if (!data.apiUrl && qp.apiUrl) data.apiUrl = qp.apiUrl || qp.api_url || qp.url;

                    // If apiUrl isn't provided, default to the script's origin (useful when widget is hosted on the API server)
                    if (!data.apiUrl && url && url.origin) {
                        data.apiUrl = url.origin;
                    }
                    if (!data.primaryColor && qp.primaryColor) data.primaryColor = qp.primaryColor || qp.primary_color;
                    if (!data.widgetTitle && qp.widgetTitle) data.widgetTitle = qp.widgetTitle || qp.widget_title;
                    if (typeof data.autoScrape === 'undefined' && qp.autoScrape) data.autoScrape = data.autoScrape === 'true' || qp.auto_scrape === 'true';
                    if (!data.position && qp.position) data.position = qp.position;

                    return data;
                }
            }
        } catch (e) {
            // ignore
        }
        return {};
    }

    // Public API
    window.CustomerSupportWidget = {
        init: async function(userConfig = {}) {
            // Merge user config with defaults
            config = Object.assign(config, userConfig);

            // Validate configuration
            if (!validateConfig()) {
                console.error('CustomerSupportWidget initialization failed due to invalid configuration');
                return false;
            }

            // Developers should provide domainId in the widget config (data-domain-id or via init)
            if (!config.domainId) {
                console.warn('CustomerSupportWidget: domainId not provided. Provide domainId via config.domainId or data-domain-id attribute.');
            }

            // Create widget when DOM is ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', createWidget);
            } else {
                createWidget();
            }

            return true;
        },

        open: function() {
            if (widget) openChat();
        },

        close: function() {
            if (widget) closeChat();
        },

        newSession: async function() {
            // Use the same logic as the button click
            if (widget && isOpen) {
                await handleNewSession();
            } else {
                // If chat is not open, just clear the stored session
                clearStoredSessionId();
            }
        },

        destroy: function() {
            if (widget) {
                widget.remove();
                widget = null;
                clearStoredSessionId();
                isOpen = false;
            }
        },

        sendMessage: function(message) {
            if (widget && isOpen) {
                const messageInput = document.getElementById('message-input');
                messageInput.value = message;
                autoResizeTextarea(); // Resize textarea for the new content
                sendMessage();
            }
        }
    };

    // Auto-initialize behavior:
    // 1) If the hosting page provided a global `window.CustomerSupportWidgetConfig`, use it.
    // 2) Otherwise, try to read config from the <script src=".../widget.js?..." data-...> tag.
    (function autoInit() {
        // 1) global config
        if (typeof window.CustomerSupportWidgetConfig !== 'undefined') {
            window.CustomerSupportWidget.init(window.CustomerSupportWidgetConfig);
            return;
        }

        // 2) script tag config
       const sconf = readScriptTagConfig();
       if (sconf && (sconf.domainId || sconf.apiUrl)) {
           // Helpful debug log for integrators — can be removed later
           try { console.debug('CustomerSupportWidget: resolved script config', sconf); } catch (e) {}
             // Map keys that may be strings
             const initConfig = {};
             if (sconf.domainId) initConfig.domainId = sconf.domainId;
             if (sconf.apiUrl) initConfig.apiUrl = sconf.apiUrl;
             if (sconf.primaryColor) initConfig.primaryColor = sconf.primaryColor;
             if (sconf.widgetTitle) initConfig.widgetTitle = sconf.widgetTitle;
             if (typeof sconf.autoScrape !== 'undefined') initConfig.autoScrape = !!sconf.autoScrape;
             if (sconf.position) initConfig.position = sconf.position;

             window.CustomerSupportWidget.init(initConfig);
             return;
         }
    })();

})();
