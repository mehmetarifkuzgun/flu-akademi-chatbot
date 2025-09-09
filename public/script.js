// Chat functionality
class ChatBot {
    constructor() {
        this.messagesContainer = document.getElementById('messages-container');
        this.chatInput = document.getElementById('chat-input');
        this.sendButton = document.getElementById('send-btn');
        this.newChatButton = document.querySelector('.new-chat-btn');
        this.canvas = document.getElementById('waves-animation');
        
        // WebSocket connection
        this.ws = null;
        this.isConnected = false;
        this.isThinking = false;
        this.currentBotMessage = '';
        
        this.init();
        this.initWavesAnimation();
        this.connectWebSocket();
    }

    connectWebSocket() {
        try {
            // Vercel deployment için URL'i dinamik yap
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsHost = window.location.hostname === 'localhost' ? 
                'localhost:8000' : window.location.host;
            const wsPath = window.location.hostname === 'localhost' ? 
                '/ws/chat' : '/ws/chat';
            
            const wsUrl = `${wsProtocol}//${wsHost}${wsPath}`;
            
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                this.isConnected = true;
                this.updateSendButton();
            };

            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };

            this.ws.onclose = () => {
                this.isConnected = false;
                this.updateSendButton();
                // 3 saniye sonra yeniden bağlan
                setTimeout(() => this.connectWebSocket(), 3000);
            };

            this.ws.onerror = (error) => {
                console.error('🔌 WebSocket hatası:', error);
                this.isConnected = false;
                this.updateSendButton();
            };
        } catch (error) {
            console.error('WebSocket bağlantı hatası:', error);
            this.isConnected = false;
            this.updateSendButton();
        }
    }

    handleWebSocketMessage(data) {
        
        switch (data.type) {
            case 'bot_thinking':
                this.isThinking = true;
                this.showThinkingIndicator();
                break;
            
            case 'bot_start':
                // Thinking indicator'ı burada GİZLEME, ilk chunk geldiğinde gizle
                this.currentBotMessage = '';
                break;
            
            case 'bot_chunk':
                // İlk chunk geldiğinde thinking indicator'ı gizle
                if (this.isThinking) {
                    this.isThinking = false;
                    this.hideThinkingIndicator();
                }
                this.updateStreamingMessage(data.full_content);
                break;
            
            case 'bot_complete':
                this.finalizeMessage(data.content);
                this.isThinking = false;
                this.hideThinkingIndicator(); // Güvenlik için
                this.currentBotMessage = '';
                break;
            
            case 'error':
                this.addMessage(data.content, 'bot', true);
                this.isThinking = false;
                this.hideThinkingIndicator();
                this.currentBotMessage = '';
                break;
        }
    }

    init() {
        // Send button click
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Enter key to send message
        this.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Input event to update send button state
        this.chatInput.addEventListener('input', () => {
            this.updateSendButton();
        });

        // New chat button
        this.newChatButton.addEventListener('click', () => this.newChat());

        // Initial state
        this.updateSendButton();
    }

    sendMessage() {
        const message = this.chatInput.textContent.trim();
        if (!message || !this.isConnected || this.isThinking) return;

        // Hide quick messages when sending a message
        const quickMessagesContainer = document.getElementById('quick-messages');
        if (quickMessagesContainer) {
            quickMessagesContainer.classList.add('hidden');
        }

        // Add user message
        this.addMessage(message, 'user');
        
        // Clear input
        this.chatInput.textContent = '';
        this.updateSendButton();

        // Hide empty state if first message
        this.hideEmptyState();

        // Send message via WebSocket
        try {
            this.ws.send(JSON.stringify({
                message: message
            }));
        } catch (error) {
            console.error('Mesaj gönderme hatası:', error);
            this.addMessage('Bağlantı hatası. Lütfen tekrar deneyin.', 'bot', true);
        }
    }

    addMessage(text, sender, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message${isError ? ' error' : ''}`;
        
        // Add avatar for bot messages
        if (sender === 'bot') {
            const avatarDiv = document.createElement('div');
            avatarDiv.className = 'message-avatar';
            avatarDiv.innerHTML = '<img src="/static/Avatar_Default.svg" alt="Bot" width="32" height="32">';
            messageDiv.appendChild(avatarDiv);
        }
        
        // Create message content with proper formatting
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Use markdown for bot messages, plain text for user messages
        if (sender === 'bot' && typeof marked !== 'undefined') {
            contentDiv.innerHTML = marked.parse(text);
        } else {
            contentDiv.textContent = text;
        }
        
        // Add timestamp
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString('tr-TR', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        contentDiv.appendChild(timeDiv);
        messageDiv.appendChild(contentDiv);
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    showThinkingIndicator() {
        
        // Remove existing thinking indicator
        this.hideThinkingIndicator();
        
        const thinkingDiv = document.createElement('div');
        thinkingDiv.className = 'message bot-message thinking';
        thinkingDiv.id = 'thinking-indicator';
        thinkingDiv.style.minHeight = '60px'; // Minimum yükseklik garantisi
        
        // Add avatar for bot messages
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = '<img src="/static/Avatar_Default.svg" alt="Bot" width="32" height="32">';
        thinkingDiv.appendChild(avatarDiv);
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.style.padding = '12px'; // Daha fazla alan
        
        const dotsDiv = document.createElement('div');
        dotsDiv.className = 'thinking-dots';
        dotsDiv.innerHTML = '<span></span><span></span><span></span>';
        
        const textDiv = document.createElement('div');
        textDiv.className = 'thinking-text';
        textDiv.textContent = 'Düşünelim...';
        textDiv.style.fontWeight = 'bold';
        textDiv.style.fontSize = '14px';
        textDiv.style.color = '#666';
        textDiv.style.marginTop = '8px';
        
        contentDiv.appendChild(dotsDiv);
        contentDiv.appendChild(textDiv);
        thinkingDiv.appendChild(contentDiv);
        
        this.messagesContainer.appendChild(thinkingDiv);
        this.scrollToBottom();
    }

    hideThinkingIndicator() {
        const existing = document.getElementById('thinking-indicator');
        if (existing) {
            existing.remove();
        }
    }

    updateStreamingMessage(content) {
        // Remove existing streaming message
        const existing = document.getElementById('streaming-message');
        if (existing) {
            existing.remove();
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message streaming';
        messageDiv.id = 'streaming-message';
        
        // Add avatar for bot messages
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = '<img src="/static/Avatar_Default.svg" alt="Bot" width="32" height="32">';
        messageDiv.appendChild(avatarDiv);
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Use markdown for streaming content
        if (typeof marked !== 'undefined') {
            contentDiv.innerHTML = marked.parse(content);
        } else {
            contentDiv.textContent = content;
        }
        
        // Add typing cursor
        const cursorDiv = document.createElement('div');
        cursorDiv.className = 'typing-cursor';
        contentDiv.appendChild(cursorDiv);
        
        messageDiv.appendChild(contentDiv);
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    finalizeMessage(content) {
        // Remove streaming message
        const existing = document.getElementById('streaming-message');
        if (existing) {
            existing.remove();
        }
        
        // Add final message
        this.addMessage(content, 'bot');
    }



    hideEmptyState() {
        const emptyState = document.querySelector('._emptyChatContainer_13xc0_106');
        if (emptyState) {
            emptyState.style.display = 'none';
        }
    }

    showEmptyState() {
        const emptyState = document.querySelector('._emptyChatContainer_13xc0_106');
        if (emptyState) {
            emptyState.style.display = 'flex';
        }
    }

    newChat() {
        // Clear messages
        this.messagesContainer.innerHTML = '';
        
        // Show empty state
        this.showEmptyState();
        
        // Clear input
        this.chatInput.textContent = '';
        this.updateSendButton();
    }

    updateSendButton() {
        const hasText = this.chatInput.textContent.trim().length > 0;
        this.sendButton.disabled = !hasText || !this.isConnected || this.isThinking;
        
        // Update button appearance based on connection status
        if (!this.isConnected) {
            this.sendButton.title = 'Bağlantı bekleniyor...';
        } else if (this.isThinking) {
            this.sendButton.title = 'Bot yanıt hazırlıyor...';
        } else {
            this.sendButton.title = 'Mesaj gönder';
        }
    }

    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    // Waves animation
    initWavesAnimation() {
        if (!this.canvas) return;
        
        const ctx = this.canvas.getContext('2d');
        let animationId;
        let time = 0;

        const resizeCanvas = () => {
            const rect = this.canvas.parentElement.getBoundingClientRect();
            this.canvas.width = rect.width;
            this.canvas.height = rect.height;
        };

        const drawWave = (amplitude, frequency, phase, opacity) => {
            ctx.globalAlpha = opacity;
            ctx.beginPath();
            
            const width = this.canvas.width;
            const height = this.canvas.height;
            const centerY = height * 0.7;
            
            ctx.moveTo(0, centerY);
            
            for (let x = 0; x <= width; x += 2) {
                const y = centerY + Math.sin((x * frequency) + phase + time) * amplitude;
                ctx.lineTo(x, y);
            }
            
            ctx.lineTo(width, height);
            ctx.lineTo(0, height);
            ctx.closePath();
            
            const gradient = ctx.createLinearGradient(0, centerY - amplitude, 0, height);
            gradient.addColorStop(0, '#ffffb7');  // Sarı (açık)
            gradient.addColorStop(1, '#fff192');  // Sarı (koyu)
            
            ctx.fillStyle = gradient;
            ctx.fill();
        };

        const animate = () => {
            ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            
            // Draw multiple waves
            drawWave(30, 0.01, 0, 0.7);
            drawWave(20, 0.015, Math.PI / 3, 0.5);
            drawWave(15, 0.02, Math.PI / 2, 0.3);
            
            time += 0.02;
            animationId = requestAnimationFrame(animate);
        };

        // Initialize
        resizeCanvas();
        animate();

        // Handle resize
        window.addEventListener('resize', resizeCanvas);

        // Cleanup function
        return () => {
            if (animationId) {
                cancelAnimationFrame(animationId);
            }
            window.removeEventListener('resize', resizeCanvas);
        };
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize ChatBot
    new ChatBot();

    // Handle course selector dropdown
    const courseSelectorBtn = document.querySelector('.course-selector-btn');
    const courseDropdown = document.getElementById('course-dropdown');
    const closeDropdown = document.getElementById('close-dropdown');
    const courseItems = document.querySelectorAll('.course-item');

    if (courseSelectorBtn && courseDropdown) {
        // Toggle dropdown
        courseSelectorBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            courseDropdown.classList.toggle('show');
        });

        // Close dropdown
        if (closeDropdown) {
            closeDropdown.addEventListener('click', () => {
                courseDropdown.classList.remove('show');
            });
        }

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!courseDropdown.contains(e.target) && !courseSelectorBtn.contains(e.target)) {
                courseDropdown.classList.remove('show');
            }
        });

        // Handle course selection
        courseItems.forEach(item => {
            item.addEventListener('click', () => {
                const courseId = item.getAttribute('data-course');
                
                // YouTube videoyu açabilir veya ders içeriğini yükleyebiliriz
                if (courseId === 'neolitik') {
                    // Örnek YouTube link - gerçek link ile değiştirebilirsiniz
                    window.open('https://www.youtube.com/watch?v=BuYCChDWRr8&t', '_blank');
                }
                
                courseDropdown.classList.remove('show');
            });
        });
    } else {
        console.error('Course selector elements not found!');
    }

    // Handle quick message buttons
    const quickMessageBtns = document.querySelectorAll('.quick-message-btn');
    const quickMessagesContainer = document.getElementById('quick-messages');
    const chatInput = document.getElementById('chat-input');
    
    quickMessageBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const message = btn.getAttribute('data-message');
            if (message && chatInput) {
                // Set the message in the input field
                chatInput.textContent = message;
                chatInput.dispatchEvent(new Event('input'));
                
                // Hide quick messages after selection
                if (quickMessagesContainer) {
                    quickMessagesContainer.classList.add('hidden');
                }
                
                // Focus on input
                chatInput.focus();
                
                // Trigger send automatically
                const sendBtn = document.getElementById('send-btn');
                if (sendBtn) {
                    sendBtn.click();
                }
            }
        });
    });

    // Handle built with badge click
    const badge = document.querySelector('._badge_x2i82_1');
    if (badge) {
        badge.addEventListener('click', () => {
            window.open('https://azure.microsoft.com/en-us/products/ai-studio', '_blank');
        });
    }

    // Mobile-specific functionality
    initMobileFeatures();
});

// Mobile-specific features
function initMobileFeatures() {
    // Prevent zoom on iOS when focusing input
    if (isIOS()) {
        const chatInput = document.getElementById('chat-input');
        if (chatInput) {
            // Ensure minimum font size to prevent zoom
            chatInput.style.fontSize = '16px';
        }
    }

    // Handle viewport height changes on mobile (keyboard show/hide)
    let initialViewportHeight = window.innerHeight;
    
    function handleViewportChange() {
        const currentHeight = window.innerHeight;
        const heightDifference = initialViewportHeight - currentHeight;
        
        // If height decreased significantly (keyboard likely opened)
        if (heightDifference > 150) {
            document.body.classList.add('keyboard-open');
            // Scroll to bottom when keyboard opens
            setTimeout(() => {
                const messagesContainer = document.getElementById('messages-container');
                if (messagesContainer) {
                    messagesContainer.scrollTop = messagesContainer.scrollHeight;
                }
            }, 100);
        } else {
            document.body.classList.remove('keyboard-open');
        }
    }

    // Listen for viewport changes
    window.addEventListener('resize', handleViewportChange);
    window.addEventListener('orientationchange', () => {
        setTimeout(() => {
            initialViewportHeight = window.innerHeight;
            handleViewportChange();
        }, 500);
    });

    // Touch-friendly interactions
    let touchStartY = 0;
    let touchEndY = 0;
    
    // Handle pull-to-refresh prevention
    document.addEventListener('touchstart', function(e) {
        touchStartY = e.changedTouches[0].screenY;
    }, { passive: true });

    document.addEventListener('touchend', function(e) {
        touchEndY = e.changedTouches[0].screenY;
        handleGesture();
    }, { passive: true });

    function handleGesture() {
        const swipeDistance = touchEndY - touchStartY;
        const messagesContainer = document.getElementById('messages-container');
        
        // If swiping down at the top of messages, prevent browser refresh
        if (swipeDistance > 50 && messagesContainer && messagesContainer.scrollTop === 0) {
            // Could add a custom pull-to-refresh here if needed
        }
    }

    // Better mobile dropdown behavior
    const courseDropdown = document.getElementById('course-dropdown');
    const closeDropdownBtn = document.getElementById('close-dropdown');
    
    if (courseDropdown && closeDropdownBtn) {
        // Close dropdown when clicking overlay (mobile)
        courseDropdown.addEventListener('click', (e) => {
            if (e.target === courseDropdown) {
                courseDropdown.classList.remove('show');
            }
        });

        // Prevent dropdown content clicks from closing
        const courseList = courseDropdown.querySelector('.course-list');
        if (courseList) {
            courseList.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        }
    }

    // Mobile-optimized scrolling
    const messagesContainer = document.getElementById('messages-container');
    if (messagesContainer && isMobile()) {
        // Smoother scrolling on mobile
        messagesContainer.style.webkitOverflowScrolling = 'touch';
        messagesContainer.style.scrollBehavior = 'smooth';
    }

    // Handle safe area insets for devices with notches
    if (CSS.supports('padding-top: env(safe-area-inset-top)')) {
        document.documentElement.style.setProperty('--safe-area-top', 'env(safe-area-inset-top)');
        document.documentElement.style.setProperty('--safe-area-bottom', 'env(safe-area-inset-bottom)');
    }
}

// Utility functions for mobile detection
function isMobile() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || 
           ('ontouchstart' in window) || 
           (navigator.maxTouchPoints > 0);
}

function isIOS() {
    return /iPad|iPhone|iPod/.test(navigator.userAgent) || 
           (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
}

function isAndroid() {
    return /Android/i.test(navigator.userAgent);
}
