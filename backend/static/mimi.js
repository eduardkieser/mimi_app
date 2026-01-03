/**
 * Mimi Task App - Client interface for task completion
 * Uses Alpine.js for reactivity
 */
function taskApp() {
  return {
    tasks: [],
    theme: localStorage.getItem('mimi-theme') || 'solid',
    audioCtx: null,
    displayDate: new Date(),
    refreshCooldown: false,
    touchStartX: 0,
    touchStartY: 0,
    
    // ============ Computed Properties ============
    
    get displayDateFormatted() {
      return this.displayDate.toLocaleDateString('en-US', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      });
    },
    
    get isToday() {
      const today = new Date();
      return this.displayDate.toDateString() === today.toDateString();
    },
    
    get displayDateStr() {
      return this.displayDate.toISOString().split('T')[0];
    },
    
    // ============ Theme ============
    
    setTheme(newTheme) {
      this.theme = newTheme;
      localStorage.setItem('mimi-theme', newTheme);
      document.documentElement.setAttribute('data-theme', newTheme);
    },
    
    // ============ Navigation ============
    
    prevDay() {
      this.animateSwipe('right');
      const newDate = new Date(this.displayDate);
      newDate.setDate(newDate.getDate() - 1);
      this.displayDate = newDate;
      this.loadTasks();
    },
    
    nextDay() {
      if (this.isToday) return;
      this.animateSwipe('left');
      const newDate = new Date(this.displayDate);
      newDate.setDate(newDate.getDate() + 1);
      this.displayDate = newDate;
      this.loadTasks();
    },
    
    animateSwipe(direction) {
      const taskList = document.getElementById('task-list');
      if (!taskList) return;
      taskList.classList.add('swipe-' + direction);
      setTimeout(() => {
        taskList.classList.remove('swipe-' + direction);
      }, 300);
    },
    
    // ============ Touch/Swipe Handling ============
    
    onTouchStart(e) {
      this.touchStartX = e.touches[0].clientX;
      this.touchStartY = e.touches[0].clientY;
    },
    
    onTouchEnd(e) {
      if (!this.touchStartX) return;
      
      const touchEndX = e.changedTouches[0].clientX;
      const touchEndY = e.changedTouches[0].clientY;
      
      const deltaX = touchEndX - this.touchStartX;
      const deltaY = touchEndY - this.touchStartY;
      
      const minSwipeDistance = 80;
      if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > minSwipeDistance) {
        if (deltaX > 0) {
          this.prevDay();
        } else {
          this.nextDay();
        }
      }
      
      this.touchStartX = 0;
      this.touchStartY = 0;
    },
    
    checkRefresh() {
      if (this.refreshCooldown) return;
      
      const scrollTop = window.scrollY;
      const scrollHeight = document.documentElement.scrollHeight;
      const clientHeight = window.innerHeight;
      
      if (scrollTop <= 0 || scrollTop + clientHeight >= scrollHeight) {
        this.refreshCooldown = true;
        this.loadTasks();
        setTimeout(() => { this.refreshCooldown = false; }, 2000);
      }
    },
    
    // ============ Initialization ============
    
    async init() {
      await this.loadTasks();
    },
    
    // ============ Data Loading ============
    
    async loadTasks() {
      try {
        const response = await fetch(`/api/tasks/date/${this.displayDateStr}`);
        this.tasks = await response.json();
        this.tasks.sort((a, b) => a.order - b.order);
      } catch (err) {
        console.error('Failed to load tasks:', err);
      }
    },
    
    // ============ Task Actions ============
    
    async toggleTask(task) {
      if (!this.isToday) return;
      
      const wasCompleted = task.status === 'completed';
      const endpoint = wasCompleted 
        ? `/api/tasks/${task.id}/uncomplete`
        : `/api/tasks/${task.id}/complete`;
      
      try {
        const response = await fetch(endpoint, { method: 'POST' });
        const updated = await response.json();
        
        const idx = this.tasks.findIndex(t => t.id === task.id);
        if (idx !== -1) {
          this.tasks[idx] = { ...updated, justCompleted: !wasCompleted };
          
          if (!wasCompleted) {
            this.playDing();
            this.vibrate();
            setTimeout(() => {
              this.tasks[idx].justCompleted = false;
            }, 500);
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err);
      }
    },
    
    // ============ Audio/Haptics ============
    
    vibrate() {
      if (navigator.vibrate) {
        navigator.vibrate(50);
      }
    },
    
    getAudioContext() {
      if (!this.audioCtx || this.audioCtx.state === 'closed') {
        this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (this.audioCtx.state === 'suspended') {
        this.audioCtx.resume();
      }
      return this.audioCtx;
    },
    
    playDing() {
      try {
        const audioCtx = this.getAudioContext();
        
        // Main tone - A5
        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        
        oscillator.frequency.value = 880;
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.5);
        
        oscillator.start(audioCtx.currentTime);
        oscillator.stop(audioCtx.currentTime + 0.5);
        
        // Harmonic for richness - E6
        const osc2 = audioCtx.createOscillator();
        const gain2 = audioCtx.createGain();
        osc2.connect(gain2);
        gain2.connect(audioCtx.destination);
        osc2.frequency.value = 1320;
        osc2.type = 'sine';
        gain2.gain.setValueAtTime(0.15, audioCtx.currentTime);
        gain2.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
        osc2.start(audioCtx.currentTime);
        osc2.stop(audioCtx.currentTime + 0.3);
      } catch (e) {
        console.warn('Audio playback failed:', e);
      }
    }
  };
}

