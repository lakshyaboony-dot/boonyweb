// Interactive Guide System for Boony Web App

class BoonyGuideSystem {
    constructor() {
        this.isActive = false;
        this.currentTooltip = null;
        this.currentAudios = new Set();
        this.isMuted = (localStorage.getItem('boony.muted') === 'true');
        this.guideData = {
            'login': {
                '#usernameInput': 'Enter your registered username, email, or user ID here 📧',
                '#passwordInput': 'Type your secure password 🔐',
                '#loginButton': 'Click to login to your account 🚀'
            },
            'dashboard': {
                '#daySelector': 'Select which day you want to practice 📅',
                '.btn-astra': 'Click on any activity to start learning 🎯',
                '.quick-actions': 'These are your daily learning activities 📚'
            },
            'signup': {
                '#fullNameInput': 'Enter your complete name as per documents 👤',
                '#mobileInput': 'Enter your 10-digit mobile number 📱',
                '#genderSelect': 'Select your gender from the dropdown 👫'
            }
        };
        this.init();
        this.setupTTS();
    }

    init() {
        this.createGuideButton();
        this.createTooltipContainer();
        this.bindEvents();
    }

    setupTTS() {
        // Listen for mute events
        window.addEventListener('boony:mute', (e) => { 
            this.isMuted = !!(e.detail && e.detail.muted); 
            if (this.isMuted) this.stopAllAudio(); 
        });
    }

    mapToMsVoice(p) { 
        if (p.accent === 'en-US') return p.voice === 'female' ? 'en-US-JennyNeural' : 'en-US-GuyNeural'; 
        return p.voice === 'female' ? 'en-IN-KavyaNeural' : 'hi-IN-PrabhatNeural'; 
    }

    getTTSEndpoint(text) { 
        const p = window.getPrefs ? window.getPrefs() : { voice: 'female', accent: 'en-IN', lang: 'hinglish', mode: 'auto' }; 
        const qs = new URLSearchParams({
            text, 
            voice: p.voice, 
            accent: p.accent, 
            lang: p.lang, 
            voice_name: this.mapToMsVoice(p), 
            mode: p.mode
        }); 
        return `/tts?${qs.toString()}`; 
    }

    stopAllAudio() { 
        this.currentAudios.forEach(a => {
            try { a.pause(); a.src = ''; } catch (e) {} 
            this.currentAudios.delete(a); 
        }); 
        try { window.dispatchEvent(new CustomEvent('boony:audio', { detail: { playing: false } })); } catch (e) {} 
    }

    async speak(text) { 
        if (!text || this.isMuted) return; 
        this.stopAllAudio(); 
        try { 
            const a = new Audio(this.getTTSEndpoint(text)); 
            this.currentAudios.add(a); 
            a.addEventListener('ended', () => this.currentAudios.delete(a), { once: true }); 
            a.addEventListener('error', () => this.currentAudios.delete(a), { once: true }); 
            try { window.dispatchEvent(new CustomEvent('boony:audio', { detail: { playing: true } })); } catch (e) {} 
            await a.play(); 
        } catch (e) { 
            console.log('TTS Error:', e);
        } 
    }

    createGuideButton() {
        const guideButton = document.createElement('div');
        guideButton.id = 'boony-guide-btn';
        guideButton.innerHTML = `
            <div class="guide-btn-content">
                <span class="guide-icon">🤖</span>
                <span class="guide-text">Help</span>
            </div>
        `;
        guideButton.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 50px;
            padding: 12px 20px;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            z-index: 1000;
            transition: all 0.3s ease;
            font-family: Arial, sans-serif;
            font-size: 14px;
            font-weight: bold;
        `;
        
        guideButton.addEventListener('mouseenter', () => {
            guideButton.style.transform = 'scale(1.1)';
            guideButton.style.boxShadow = '0 6px 20px rgba(0,0,0,0.3)';
        });
        
        guideButton.addEventListener('mouseleave', () => {
            guideButton.style.transform = 'scale(1)';
            guideButton.style.boxShadow = '0 4px 15px rgba(0,0,0,0.2)';
        });
        
        document.body.appendChild(guideButton);
    }

    createTooltipContainer() {
        const tooltipContainer = document.createElement('div');
        tooltipContainer.id = 'boony-tooltip';
        tooltipContainer.style.cssText = `
            position: absolute;
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            padding: 10px 15px;
            border-radius: 8px;
            font-size: 13px;
            font-family: Arial, sans-serif;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            z-index: 1001;
            display: none;
            max-width: 250px;
            word-wrap: break-word;
            pointer-events: none;
        `;
        document.body.appendChild(tooltipContainer);
    }

    bindEvents() {
        const guideButton = document.getElementById('boony-guide-btn');
        guideButton.addEventListener('click', () => this.toggleGuide());
        
        document.addEventListener('mouseover', (e) => {
            if (this.isActive) {
                this.showTooltip(e.target);
            }
        });
        
        document.addEventListener('mouseout', (e) => {
            if (this.isActive) {
                this.hideTooltip();
            }
        });
    }

    toggleGuide() {
        this.isActive = !this.isActive;
        const guideButton = document.getElementById('boony-guide-btn');
        
        if (this.isActive) {
            guideButton.style.background = 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)';
            guideButton.querySelector('.guide-text').textContent = 'Exit Help';
            this.showWelcomeMessage();
        } else {
            guideButton.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
            guideButton.querySelector('.guide-text').textContent = 'Help';
            this.hideTooltip();
            this.hideWelcomeMessage();
        }
    }

    showWelcomeMessage() {
        const welcomeMsg = document.createElement('div');
        welcomeMsg.id = 'guide-welcome';
        welcomeMsg.innerHTML = `
            <div style="display: flex; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 20px; margin-right: 10px;">🤖</span>
                <strong>Boony Guide Activated!</strong>
            </div>
            <p style="margin: 0; font-size: 14px;">Hover over any element to get helpful tips! 💡</p>
        `;
        
        // Speak welcome message
        this.speak('Boony Guide Activated! Hover over any element to get helpful tips!');
        welcomeMsg.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            z-index: 1002;
            max-width: 300px;
            font-family: Arial, sans-serif;
            animation: slideIn 0.3s ease;
        `;
        
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(style);
        
        document.body.appendChild(welcomeMsg);
        
        // Auto-hide message after 2 seconds
        setTimeout(() => {
            if (document.getElementById('guide-welcome')) {
                welcomeMsg.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                welcomeMsg.style.opacity = '0';
                welcomeMsg.style.transform = 'translateX(100%)';
                
                // Remove element after animation
                setTimeout(() => {
                    if (welcomeMsg.parentNode) {
                        welcomeMsg.parentNode.removeChild(welcomeMsg);
                    }
                }, 500);
            }
        }, 2000);
    }

    hideWelcomeMessage() {
        const welcomeMsg = document.getElementById('guide-welcome');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }
    }

    showTooltip(element) {
        const tooltip = document.getElementById('boony-tooltip');
        const currentPage = this.getCurrentPage();
        const pageGuides = this.guideData[currentPage];
        
        if (!pageGuides) return;
        
        let tooltipText = null;
        
        // Check for exact ID match
        if (element.id && pageGuides[`#${element.id}`]) {
            tooltipText = pageGuides[`#${element.id}`];
        }
        // Check for class match
        else if (element.className) {
            const classes = element.className.split(' ');
            for (let className of classes) {
                if (pageGuides[`.${className}`]) {
                    tooltipText = pageGuides[`.${className}`];
                    break;
                }
            }
        }
        // Check for parent elements
        else {
            let parent = element.parentElement;
            while (parent && !tooltipText) {
                if (parent.className) {
                    const classes = parent.className.split(' ');
                    for (let className of classes) {
                        if (pageGuides[`.${className}`]) {
                            tooltipText = pageGuides[`.${className}`];
                            break;
                        }
                    }
                }
                parent = parent.parentElement;
            }
        }
        
        if (tooltipText) {
            tooltip.textContent = tooltipText;
            tooltip.style.display = 'block';
            
            // Speak the tooltip text
            this.speak(tooltipText.replace(/[📧🔐🚀📅🎯📚👤📱👫💡]/g, ''));
            
            const rect = element.getBoundingClientRect();
            tooltip.style.left = `${rect.left + window.scrollX}px`;
            tooltip.style.top = `${rect.bottom + window.scrollY + 5}px`;
            
            // Adjust position if tooltip goes off screen
            const tooltipRect = tooltip.getBoundingClientRect();
            if (tooltipRect.right > window.innerWidth) {
                tooltip.style.left = `${window.innerWidth - tooltipRect.width - 10}px`;
            }
            if (tooltipRect.bottom > window.innerHeight) {
                tooltip.style.top = `${rect.top + window.scrollY - tooltipRect.height - 5}px`;
            }
        }
    }

    hideTooltip() {
        const tooltip = document.getElementById('boony-tooltip');
        tooltip.style.display = 'none';
    }

    getCurrentPage() {
        const path = window.location.pathname;
        if (path.includes('login')) return 'login';
        if (path.includes('signup')) return 'signup';
        if (path.includes('dashboard') || path === '/') return 'dashboard';
        return 'default';
    }

    // Method to add custom tooltips dynamically
    addTooltip(selector, text, page = null) {
        const currentPage = page || this.getCurrentPage();
        if (!this.guideData[currentPage]) {
            this.guideData[currentPage] = {};
        }
        this.guideData[currentPage][selector] = text;
    }
}

// Initialize the guide system when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.boonyGuide = new BoonyGuideSystem();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BoonyGuideSystem;
}