/**
 * Admin App - Ilse's task management interface
 * Uses Alpine.js for reactivity
 */
function adminApp() {
  return {
    days: [],
    tasks: {},  // keyed by date string
    selectedDayIdx: 0,
    showModal: false,
    editingTask: null,
    insertAtDate: null,
    insertAtOrder: 0,
    theme: localStorage.getItem('admin-theme') || 'solid',
    form: {
      title: '',
      description: '',
      priority: 'optional',
      expected_minutes: 30,
      repeat_daily: false,
      repeat_weekly: false,
      weekly_days: [],  // 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri
      repeat_monthly: false
    },
    
    // Drag and drop state
    draggedTask: null,
    draggedFromDate: null,
    dropTargetTask: null,

    // ============ Theme ============
    
    setTheme(newTheme) {
      this.theme = newTheme;
      localStorage.setItem('admin-theme', newTheme);
      document.documentElement.setAttribute('data-theme', newTheme);
    },

    // ============ Initialization ============

    async init() {
      this.buildDays();
      await this.loadAllTasks();
      // Scroll to today
      this.$nextTick(() => this.scrollToDay(this.selectedDayIdx));
    },

    buildDays() {
      const days = [];
      const today = new Date();
      const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
      
      // Find Monday of current week
      const dayOfWeek = today.getDay(); // 0=Sun, 1=Mon, etc.
      const monday = new Date(today);
      monday.setDate(today.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));
      
      for (let i = 0; i < 7; i++) {
        const d = new Date(monday);
        d.setDate(monday.getDate() + i);
        const isToday = d.toDateString() === today.toDateString();
        days.push({
          date: d,
          dateStr: d.toISOString().split('T')[0],
          shortName: dayNames[i],
          dayName: dayNames[i],
          dateFormatted: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          isToday: isToday
        });
      }
      this.days = days;
      
      // Set initial selection to today
      this.selectedDayIdx = days.findIndex(d => d.isToday);
      if (this.selectedDayIdx < 0) this.selectedDayIdx = 0;
    },

    // ============ Data Loading ============

    async loadAllTasks() {
      for (const day of this.days) {
        try {
          const response = await fetch(`/api/tasks/date/${day.dateStr}`);
          let tasks = await response.json();
          tasks.sort((a, b) => a.order - b.order);
          this.tasks[day.dateStr] = tasks;
        } catch (err) {
          console.error('Failed to load tasks for', day.dateStr, err);
          this.tasks[day.dateStr] = [];
        }
      }
    },

    async regenerateWeek() {
      if (!confirm('This will refresh all tasks from templates. Continue?')) return;
      
      try {
        const response = await fetch('/api/admin/regenerate-week', { method: 'POST' });
        const result = await response.json();
        console.log('Regenerated:', result);
        await this.loadAllTasks();
      } catch (err) {
        console.error('Failed to regenerate:', err);
      }
    },

    getTasksForDay(dateStr) {
      return this.tasks[dateStr] || [];
    },

    getDayTotalTime(dateStr) {
      const tasks = this.getTasksForDay(dateStr);
      const total = tasks.reduce((sum, t) => sum + (t.expected_minutes || 0), 0);
      if (total === 0) return '';
      const hrs = Math.floor(total / 60);
      const mins = total % 60;
      return hrs > 0 ? `${hrs}h ${mins}m total` : `${mins}m total`;
    },

    // ============ Navigation ============

    scrollToDay(idx) {
      this.selectedDayIdx = idx;
      const panel = document.getElementById('panel-' + idx);
      if (panel) {
        panel.scrollIntoView({ behavior: 'smooth', inline: 'center' });
      }
    },

    onScroll() {
      const container = document.getElementById('day-panels');
      const panels = container.querySelectorAll('.day-panel');
      const containerCenter = container.scrollLeft + container.clientWidth / 2;
      
      let closestIdx = 0;
      let closestDist = Infinity;
      
      panels.forEach((panel, idx) => {
        const panelCenter = panel.offsetLeft + panel.clientWidth / 2;
        const dist = Math.abs(panelCenter - containerCenter);
        if (dist < closestDist) {
          closestDist = dist;
          closestIdx = idx;
        }
      });
      
      this.selectedDayIdx = closestIdx;
    },
    
    onWheel(e) {
      const container = document.getElementById('day-panels');
      container.scrollLeft += e.deltaY * 2;
    },

    // ============ Modal Handling ============

    openCreateModal(dateStr, order) {
      this.editingTask = null;
      this.insertAtDate = dateStr;
      this.insertAtOrder = order;
      const d = new Date(dateStr);
      const dayIdx = (d.getDay() + 6) % 7; // Convert Sun=0 to Mon=0
      this.form = {
        title: '',
        description: '',
        priority: 'optional',
        expected_minutes: 30,
        repeat_daily: false,
        repeat_weekly: false,
        weekly_days: dayIdx < 5 ? [dayIdx] : [],
        repeat_monthly: false
      };
      this.showModal = true;
    },
    
    toggleWeeklyDay(idx) {
      const i = this.form.weekly_days.indexOf(idx);
      if (i >= 0) {
        this.form.weekly_days.splice(i, 1);
      } else {
        this.form.weekly_days.push(idx);
        this.form.weekly_days.sort();
      }
    },

    openEditModal(task) {
      this.editingTask = task;
      
      // Pre-populate repeat settings from task's repeat_info
      let repeatDaily = false;
      let repeatWeekly = false;
      let repeatMonthly = false;
      let weeklyDays = [];
      
      if (task.repeat_info) {
        if (task.repeat_info.type === 'daily') {
          repeatDaily = true;
        } else if (task.repeat_info.type === 'weekly') {
          repeatWeekly = true;
          const dayMap = { 'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4 };
          weeklyDays = (task.repeat_info.days || [])
            .map(d => dayMap[d])
            .filter(d => d !== undefined);
        } else if (task.repeat_info.type === 'monthly') {
          repeatMonthly = true;
        }
      }
      
      this.form = {
        title: task.title,
        description: task.description || '',
        priority: task.priority,
        expected_minutes: task.expected_minutes || 30,
        repeat_daily: repeatDaily,
        repeat_weekly: repeatWeekly,
        weekly_days: weeklyDays,
        repeat_monthly: repeatMonthly
      };
      this.showModal = true;
    },

    // ============ Task CRUD ============

    async saveTask() {
      if (this.editingTask) {
        // Determine repeat type from form
        let repeatType = 'none';
        let weekdays = '';
        
        if (this.form.repeat_daily) {
          repeatType = 'daily';
        } else if (this.form.repeat_weekly && this.form.weekly_days.length > 0) {
          repeatType = 'weekly';
          weekdays = this.form.weekly_days.join(',');
        } else if (this.form.repeat_monthly) {
          repeatType = 'monthly';
        }
        
        // If task is template-based, update the template
        if (this.editingTask.template_id) {
          try {
            console.log('Updating template:', this.editingTask.template_id);
            await fetch(`/api/admin/templates/${this.editingTask.template_id}`, {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                title: this.form.title,
                description: this.form.description || null,
                priority: this.form.priority,
                expected_minutes: this.form.expected_minutes,
                repeat_type: repeatType,
                weekdays: weekdays
              })
            });
          } catch (err) {
            console.error('Failed to update template:', err);
          }
        } else {
          // Non-template task: just update the task instance
          try {
            await fetch(`/api/tasks/${this.editingTask.id}`, {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                title: this.form.title,
                description: this.form.description || null,
                priority: this.form.priority,
                expected_minutes: this.form.expected_minutes
              })
            });
          } catch (err) {
            console.error('Failed to update task:', err);
          }
        }
      } else {
        // Determine repeat type
        let repeatType = 'none';
        let weekdays = '';
        
        if (this.form.repeat_daily) {
          repeatType = 'daily';
        } else if (this.form.repeat_weekly && this.form.weekly_days.length > 0) {
          repeatType = 'weekly';
          weekdays = this.form.weekly_days.join(',');
        } else if (this.form.repeat_monthly) {
          repeatType = 'monthly';
        }
        
        // If repeating, create a template
        if (repeatType !== 'none') {
          try {
            await fetch('/api/admin/templates', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                title: this.form.title,
                description: this.form.description || null,
                priority: this.form.priority,
                expected_minutes: this.form.expected_minutes,
                order: this.insertAtOrder,
                repeat_type: repeatType,
                weekdays: weekdays
              })
            });
          } catch (err) {
            console.error('Failed to create template:', err);
          }
        } else {
          // Non-repeating: create single task
          const dayTasks = this.getTasksForDay(this.insertAtDate);
          for (const t of dayTasks) {
            if (t.order >= this.insertAtOrder) {
              t.order += 1;
            }
          }
          if (dayTasks.length > 0) {
            await fetch('/api/admin/tasks/reorder', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(dayTasks.map(t => ({ id: t.id, order: t.order })))
            });
          }
          
          try {
            await fetch('/api/admin/tasks', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                title: this.form.title,
                description: this.form.description || null,
                priority: this.form.priority,
                expected_minutes: this.form.expected_minutes,
                order: this.insertAtOrder,
                scheduled_date: this.insertAtDate
              })
            });
          } catch (err) {
            console.error('Failed to create task:', err);
          }
        }
      }

      this.showModal = false;
      await this.loadAllTasks();
    },

    async deleteTask(taskId) {
      try {
        const response = await fetch(`/api/admin/tasks/${taskId}`, { method: 'DELETE' });
        if (!response.ok) {
          console.error('Delete failed:', response.status);
        }
        await this.loadAllTasks();
      } catch (err) {
        console.error('Failed to delete task:', err);
      }
    },

    // ============ Drag and Drop ============

    onDragStart(e, task, dateStr) {
      this.draggedTask = task;
      this.draggedFromDate = dateStr;
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', task.id);
      setTimeout(() => {
        e.target.classList.add('dragging');
      }, 0);
    },
    
    onDragEnd(e) {
      e.target.classList.remove('dragging');
      this.draggedTask = null;
      this.draggedFromDate = null;
      this.dropTargetTask = null;
      document.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
    },
    
    onTaskDragOver(e, task) {
      if (!this.draggedTask || this.draggedTask.id === task.id) return;
      e.target.closest('.admin-task-card')?.classList.add('drag-over');
      this.dropTargetTask = task;
    },
    
    onTaskDragLeave(e) {
      e.target.closest('.admin-task-card')?.classList.remove('drag-over');
    },
    
    onDragOver(e, dateStr) {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
    },
    
    onDragLeave(e) {
      if (!e.relatedTarget?.closest('.day-panel-tasks')) {
        e.currentTarget.closest('.day-panel')?.classList.remove('drag-over');
      }
    },
    
    async onDrop(e, targetDate) {
      e.preventDefault();
      document.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
      
      if (!this.draggedTask) return;
      
      const task = this.draggedTask;
      const fromDate = this.draggedFromDate;
      const fromTasks = this.tasks[fromDate] || [];
      const targetTasks = this.tasks[targetDate] || [];
      
      // Determine new order
      let newOrder = 0;
      if (this.dropTargetTask && targetDate === this.dropTargetTask.scheduled_date?.split('T')[0]) {
        newOrder = this.dropTargetTask.order;
      } else if (targetTasks.length > 0) {
        newOrder = Math.max(...targetTasks.map(t => t.order)) + 1;
      }
      
      // Clear drag state
      this.draggedTask = null;
      this.draggedFromDate = null;
      const dropTarget = this.dropTargetTask;
      this.dropTargetTask = null;
      
      // Optimistic UI update
      if (fromDate === targetDate && dropTarget) {
        // Same day reorder
        const fromIdx = fromTasks.findIndex(t => t.id === task.id);
        const toIdx = fromTasks.findIndex(t => t.id === dropTarget.id);
        
        if (fromIdx !== -1 && toIdx !== -1 && fromIdx !== toIdx) {
          fromTasks.splice(fromIdx, 1);
          const insertIdx = fromIdx < toIdx ? toIdx - 1 : toIdx;
          fromTasks.splice(insertIdx, 0, task);
          fromTasks.forEach((t, i) => t.order = i);
          this.tasks[fromDate] = [...fromTasks];
          
          const reorders = fromTasks.map((t, i) => ({ id: t.id, order: i }));
          fetch('/api/admin/tasks/reorder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(reorders)
          }).catch(err => {
            console.error('Reorder failed:', err);
            this.loadAllTasks();
          });
        }
      } else if (fromDate !== targetDate) {
        // Move to different day
        console.log(`Moving task ${task.id} (${task.title}) from ${fromDate} to ${targetDate}`);
        
        // Optimistic: remove from source
        const fromIdx = fromTasks.findIndex(t => t.id === task.id);
        if (fromIdx !== -1) {
          fromTasks.splice(fromIdx, 1);
          fromTasks.forEach((t, i) => t.order = i);
          this.tasks[fromDate] = [...fromTasks];
        }
        
        // Check if task already exists on target date (same template)
        const existingOnTarget = targetTasks.find(t => 
          t.template_id && t.template_id === task.template_id
        );
        
        if (existingOnTarget) {
          // Task already exists on target - just delete from source, don't add to target
          console.log(`Task already exists on ${targetDate}, just removing from ${fromDate}`);
          // UI already updated (removed from source)
        } else {
          // Add to target
          targetTasks.forEach(t => {
            if (t.order >= newOrder) t.order += 1;
          });
          task.order = newOrder;
          task.scheduled_date = targetDate;
          targetTasks.push(task);
          targetTasks.sort((a, b) => a.order - b.order);
          this.tasks[targetDate] = [...targetTasks];
        }
        
        // Backend call
        fetch(`/api/admin/tasks/${task.id}/move?target_date=${targetDate}&order=${newOrder}`, {
          method: 'POST'
        }).then(async response => {
          if (!response.ok) {
            const errText = await response.text();
            console.error('Move failed:', response.status, errText);
            this.loadAllTasks();
          } else {
            const data = await response.json();
            console.log('Move succeeded:', data);
            // Reload to get correct state (new task IDs, etc)
            await this.loadAllTasks();
          }
        }).catch(err => {
          console.error('Move failed:', err);
          this.loadAllTasks();
        });
      }
    }
  };
}
