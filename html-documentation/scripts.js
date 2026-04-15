/**
 * Slide Navigation with GSAP Animations
 * Supports keyboard, touch, and click navigation
 */

// State
let currentSlide = 0;
const totalSlides = 8;
let isAnimating = false;

// DOM Elements
const slides = document.querySelectorAll('.slide');
const progressIndicator = document.querySelector('.progress-indicator');

// Touch tracking
let touchStartX = 0;
let touchEndX = 0;

// Test Flow Animation
let flowAnimation = null;

function animateTestFlow() {
  const flowContainer = document.querySelector('#test-flow');
  if (!flowContainer) return;

  // Kill existing animation if running
  if (flowAnimation) {
    flowAnimation.kill();
  }

  const steps = flowContainer.querySelectorAll('.flow-step');
  const arrows = flowContainer.querySelectorAll('.flow-arrow');

  // Reset all steps and arrows to default state
  steps.forEach(step => {
    gsap.set(step, {
      borderColor: '#4a5568',
      boxShadow: 'none',
      backgroundColor: 'transparent'
    });
  });
  arrows.forEach(arrow => {
    gsap.set(arrow, { color: '#4a5568' });
  });

  // Create GSAP timeline with repeat
  flowAnimation = gsap.timeline({ repeat: -1, repeatDelay: 1 });

  steps.forEach((step, index) => {
    // Highlight current step
    flowAnimation.to(step, {
      borderColor: '#00ff88',
      boxShadow: '0 0 20px #00ff88',
      backgroundColor: 'rgba(0, 255, 136, 0.1)',
      duration: 0.3
    });

    // Highlight arrow (if not last step)
    if (index < arrows.length) {
      flowAnimation.to(arrows[index], {
        color: '#00ff88',
        duration: 0.2
      }, '-=0.1');
    }

    // Delay before moving to next step
    flowAnimation.to(step, {
      duration: 0.5
    });

    // Reset step appearance
    flowAnimation.to(step, {
      borderColor: '#4a5568',
      boxShadow: 'none',
      backgroundColor: 'transparent',
      duration: 0.3
    });

    // Reset arrow (if not last step)
    if (index < arrows.length) {
      flowAnimation.to(arrows[index], {
        color: '#4a5568',
        duration: 0.2
      }, '-=0.3');
    }
  });
}

function stopTestFlowAnimation() {
  if (flowAnimation) {
    flowAnimation.kill();
    flowAnimation = null;

    // Reset all steps and arrows
    const flowContainer = document.querySelector('#test-flow');
    if (flowContainer) {
      const steps = flowContainer.querySelectorAll('.flow-step');
      const arrows = flowContainer.querySelectorAll('.flow-arrow');
      steps.forEach(step => {
        gsap.set(step, {
          borderColor: '#4a5568',
          boxShadow: 'none',
          backgroundColor: 'transparent'
        });
      });
      arrows.forEach(arrow => {
        gsap.set(arrow, { color: '#4a5568' });
      });
    }
  }
}

function onSlideChange(index) {
  if (index === 3) { // slide-4 is index 3
    // Small delay to ensure slide is visible
    setTimeout(() => {
      animateTestFlow();
    }, 100);
  } else {
    stopTestFlowAnimation();
  }
}

// Navigation Functions
function goToSlide(index) {
  if (isAnimating || index === currentSlide || index < 0 || index >= totalSlides) return;

  isAnimating = true;
  const prevIndex = currentSlide;
  const prevSlide = slides[prevIndex];
  const nextSlide = slides[index];
  const direction = index > prevIndex ? 1 : -1;

  // Update state
  currentSlide = index;

  // Remove active class and add prev class for exit animation
  prevSlide.classList.remove('active');
  prevSlide.classList.add('prev');

  // Prepare next slide
  nextSlide.classList.remove('prev');
  nextSlide.style.transform = `translateX(${direction * 100}px)`;
  nextSlide.style.opacity = '1';
  nextSlide.style.visibility = 'visible';

  // GSAP animation: current slides out, new slide in
  gsap.fromTo(
    prevSlide,
    { x: 0, opacity: 1 },
    {
      x: -direction * window.innerWidth,
      opacity: 0,
      duration: 0.6,
      ease: 'power2.inOut',
      onComplete: () => {
        prevSlide.classList.remove('prev');
        prevSlide.style.transform = '';
      }
    }
  );

  gsap.fromTo(
    nextSlide,
    { x: direction * window.innerWidth },
    {
      x: 0,
      opacity: 1,
      duration: 0.6,
      ease: 'power2.inOut',
      onComplete: () => {
        nextSlide.classList.add('active');
        nextSlide.style.transform = '';
        nextSlide.style.opacity = '';
        isAnimating = false;
        // Trigger slide-specific animations
        onSlideChange(index);
      }
    }
  );

  // Update progress indicator
  updateProgressDots();
}

function nextSlide() {
  if (currentSlide < totalSlides - 1) {
    goToSlide(currentSlide + 1);
  }
}

function prevSlide() {
  if (currentSlide > 0) {
    goToSlide(currentSlide - 1);
  }
}

// Progress Indicator
function createProgressDots() {
  progressIndicator.innerHTML = '';
  for (let i = 0; i < totalSlides; i++) {
    const dot = document.createElement('div');
    dot.className = 'progress-dot' + (i === 0 ? ' active' : '');
    dot.dataset.index = i;
    dot.addEventListener('click', () => goToSlide(i));
    progressIndicator.appendChild(dot);
  }
}

function updateProgressDots() {
  const dots = document.querySelectorAll('.progress-dot');
  dots.forEach((dot, index) => {
    if (index === currentSlide) {
      dot.classList.add('active');
    } else {
      dot.classList.remove('active');
    }
  });
}

// Keyboard Navigation
document.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowRight' || e.key === ' ') {
    e.preventDefault();
    nextSlide();
  }
  if (e.key === 'ArrowLeft') {
    e.preventDefault();
    prevSlide();
  }
});

// Touch Navigation
document.addEventListener('touchstart', (e) => {
  touchStartX = e.touches[0].clientX;
}, { passive: true });

document.addEventListener('touchend', (e) => {
  touchEndX = e.changedTouches[0].clientX;
  const diff = touchStartX - touchEndX;
  const threshold = 50;

  if (Math.abs(diff) > threshold) {
    if (diff > 0) {
      nextSlide(); // Swipe left -> next
    } else {
      prevSlide(); // Swipe right -> prev
    }
  }
}, { passive: true });

// Initialize
function init() {
  createProgressDots();

  // Set initial slide state (already has .active in HTML, but ensure proper positioning)
  slides.forEach((slide, index) => {
    if (index === 0) {
      slide.classList.add('active');
      slide.style.transform = 'translateX(0)';
    } else {
      slide.style.transform = 'translateX(100px)';
    }
  });

  // Trigger initial slide animations
  onSlideChange(0);
}

init();

// ===== T11: COPY BUTTON FUNCTIONALITY =====
function addCopyButtons() {
  const codeBlocks = document.querySelectorAll('pre code');
  codeBlocks.forEach(block => {
    const pre = block.parentElement;
    if (pre.querySelector('.copy-btn')) return;

    const button = document.createElement('button');
    button.className = 'copy-btn';
    button.textContent = '复制';
    button.addEventListener('click', () => copyCode(block, button));
    pre.style.position = 'relative';
    pre.appendChild(button);
  });
}

async function copyCode(codeBlock, button) {
  const code = codeBlock.textContent;
  try {
    await navigator.clipboard.writeText(code);
    showToast('代码已复制！');
    button.textContent = '已复制';
    setTimeout(() => { button.textContent = '复制'; }, 1500);
  } catch (err) {
    showToast('复制失败');
  }
}

// ===== T11: TOAST NOTIFICATION =====
function showToast(message) {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  document.body.appendChild(toast);

  gsap.fromTo(toast,
    { opacity: 0, y: 20 },
    { opacity: 1, y: 0, duration: 0.3 }
  );

  setTimeout(() => {
    gsap.to(toast, {
      opacity: 0, y: -20, duration: 0.3,
      onComplete: () => toast.remove()
    });
  }, 2000);
}

// ===== T11: PAGE VISIBILITY DETECTION =====
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    gsap.globalTimeline.pause();
  } else {
    gsap.globalTimeline.resume();
  }
});

// ===== LOADER FADE OUT =====
window.addEventListener('load', () => {
  gsap.to('#loader', {
    opacity: 0,
    duration: 0.5,
    onComplete: () => {
      document.getElementById('loader').style.display = 'none';
    }
  });
});

// Initialize copy buttons after DOM is ready
setTimeout(addCopyButtons, 500);
