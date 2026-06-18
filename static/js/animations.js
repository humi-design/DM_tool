/**
 * Viraly Animations Manager
 * Handles scroll-triggered animations, counters, and micro-interactions
 */

class AnimationsManager {
  constructor() {
    this.scrollObserver = null;
    this.counterObserver = null;
    this.init();
  }

  init() {
    this.initScrollAnimations();
    this.initCounterAnimations();
    this.initNavbarScroll();
    this.initSmoothScroll();
    this.initFAQ();
    this.initDemoNavigation();
  }

  // ============================================
  // Scroll Animations
  // ============================================
  initScrollAnimations() {
    const animatedElements = document.querySelectorAll('.animate-on-scroll, .stagger-children');
    
    if (animatedElements.length === 0) return;

    const observerOptions = {
      root: null,
      rootMargin: '0px 0px -100px 0px',
      threshold: 0.1
    };

    this.scrollObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          // Optional: unobserve after animation
          // this.scrollObserver.unobserve(entry.target);
        }
      });
    }, observerOptions);

    animatedElements.forEach(el => {
      this.scrollObserver.observe(el);
    });
  }

  // ============================================
  // Counter Animations
  // ============================================
  initCounterAnimations() {
    const counters = document.querySelectorAll('.counter[data-count]');
    
    if (counters.length === 0) return;

    this.counterObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting && !entry.target.classList.contains('counted')) {
          this.animateCounter(entry.target);
          entry.target.classList.add('counted');
        }
      });
    }, { threshold: 0.5 });

    counters.forEach(counter => {
      this.counterObserver.observe(counter);
    });
  }

  animateCounter(element) {
    const target = parseInt(element.getAttribute('data-count'));
    const duration = 2000;
    const step = target / (duration / 16);
    let current = 0;
    const suffix = element.getAttribute('data-suffix') || '';
    const prefix = element.getAttribute('data-prefix') || '';

    const updateCounter = () => {
      current += step;
      if (current < target) {
        element.textContent = prefix + Math.floor(current).toLocaleString() + suffix;
        requestAnimationFrame(updateCounter);
      } else {
        element.textContent = prefix + target.toLocaleString() + suffix;
      }
    };

    updateCounter();
  }

  // ============================================
  // Navbar Scroll Effect
  // ============================================
  initNavbarScroll() {
    const navbar = document.querySelector('.navbar');
    
    if (!navbar) return;

    let lastScroll = 0;
    
    window.addEventListener('scroll', () => {
      const currentScroll = window.pageYOffset;
      
      if (currentScroll > 50) {
        navbar.classList.add('scrolled');
      } else {
        navbar.classList.remove('scrolled');
      }
      
      lastScroll = currentScroll;
    }, { passive: true });
  }

  // ============================================
  // Smooth Scroll
  // ============================================
  initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', (e) => {
        const targetId = anchor.getAttribute('href');
        if (targetId === '#') return;
        
        const target = document.querySelector(targetId);
        if (target) {
          e.preventDefault();
          const navbarHeight = document.querySelector('.navbar')?.offsetHeight || 0;
          const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - navbarHeight - 20;
          
          window.scrollTo({
            top: targetPosition,
            behavior: 'smooth'
          });
        }
      });
    });
  }

  // ============================================
  // FAQ Accordion
  // ============================================
  initFAQ() {
    document.querySelectorAll('.faq-item').forEach(item => {
      const question = item.querySelector('.faq-question');
      
      if (question) {
        question.addEventListener('click', () => {
          const isOpen = item.classList.contains('open');
          
          // Close all other items
          document.querySelectorAll('.faq-item.open').forEach(openItem => {
            if (openItem !== item) {
              openItem.classList.remove('open');
            }
          });
          
          // Toggle current item
          item.classList.toggle('open', !isOpen);
        });
      }
    });
  }

  // ============================================
  // Demo Page Navigation
  // ============================================
  initDemoNavigation() {
    const navItems = document.querySelectorAll('.demo-nav-item');
    const panels = document.querySelectorAll('.demo-panel');
    
    navItems.forEach(item => {
      item.addEventListener('click', () => {
        const target = item.getAttribute('data-target');
        
        // Update nav active state
        navItems.forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');
        
        // Show corresponding panel
        panels.forEach(panel => {
          panel.classList.remove('active');
          if (panel.id === target) {
            panel.classList.add('active');
          }
        });
      });
    });

    // Simulate typing in demo
    this.initDemoTyping();
  }

  initDemoTyping() {
    const typingElements = document.querySelectorAll('[data-typing]');
    
    typingElements.forEach(el => {
      const text = el.getAttribute('data-typing');
      const speed = parseInt(el.getAttribute('data-speed')) || 50;
      
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting && !el.classList.contains('typed')) {
            this.typeText(el, text, speed);
            el.classList.add('typed');
          }
        });
      }, { threshold: 0.5 });
      
      observer.observe(el);
    });
  }

  typeText(element, text, speed) {
    let index = 0;
    element.textContent = '';
    
    const type = () => {
      if (index < text.length) {
        element.textContent += text.charAt(index);
        index++;
        setTimeout(type, speed);
      }
    };
    
    type();
  }

  // ============================================
  // Parallax Effect (optional)
  // ============================================
  initParallax() {
    const parallaxElements = document.querySelectorAll('.parallax-image');
    
    if (parallaxElements.length === 0) return;
    
    window.addEventListener('scroll', () => {
      const scrollY = window.pageYOffset;
      
      parallaxElements.forEach(el => {
        const speed = parseFloat(el.getAttribute('data-parallax-speed')) || 0.5;
        el.style.transform = `translateY(${scrollY * speed}px)`;
      });
    }, { passive: true });
  }

  // ============================================
  // Cleanup
  // ============================================
  destroy() {
    if (this.scrollObserver) {
      this.scrollObserver.disconnect();
    }
    if (this.counterObserver) {
      this.counterObserver.disconnect();
    }
  }
}

// Initialize animations manager
document.addEventListener('DOMContentLoaded', () => {
  window.animationsManager = new AnimationsManager();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && window.animationsManager) {
    // Re-trigger animations if needed
  }
});