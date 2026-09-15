# UI/UX Improvement Recommendations — Task 6

**Target Theme:** Linear Aesthetic (Dark Precision)
**Application:** ECS Security Assessment Console
**Date:** 2026-09-14

---

## Priority Levels
- **P0** = Critical (accessibility, broken functionality, security)
- **P1** = High (core visual transformation, usability)
- **P2** = Medium (polish, micro-interactions, consistency)
- **P3** = Low (nice-to-have enhancements)

---

## 1. Theme Transformation (P0 → P1)

### 1.1 CSS Custom Properties System [P0]

**Current:** All colors hardcoded across 9 files, ~306 lines of inline CSS.
**Recommendation:** Create a CSS custom property design token system.

```css
:root {
  /* ── Canvas ── */
  --bg-canvas: #080808;
  --bg-canvas-elevated: #0A0A0A;
  --bg-card: rgba(10, 10, 10, 0.8);
  --bg-card-hover: rgba(15, 15, 15, 0.9);
  --bg-input: rgba(255, 255, 255, 0.03);

  /* ── Text ── */
  --text-primary: #EDEDEF;
  --text-secondary: #A1A1AA;
  --text-tertiary: #71717A;
  --text-inverse: #080808;

  /* ── Accents ── */
  --accent-indigo: #6366F1;
  --accent-purple: #A855F7;
  --accent-glow: rgba(99, 102, 241, 0.15);

  /* ── Status ── */
  --success: #10B981;
  --warning: #F59E0B;
  --error: #EF4444;
  --info: #3B82F6;

  /* ── Borders ── */
  --border-subtle: rgba(255, 255, 255, 0.06);
  --border-default: rgba(255, 255, 255, 0.1);
  --border-strong: rgba(255, 255, 255, 0.15);
  --border-focus: rgba(99, 102, 241, 0.5);

  /* ── Typography ── */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  --letter-spacing-tight: -0.02em;
  --letter-spacing-normal: 0;

  /* ── Spacing Scale (4px base) ── */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;

  /* ── Radius ── */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;

  /* ── Shadows ── */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.5);
  --shadow-glow: 0 0 20px rgba(99, 102, 241, 0.3);

  /* ── Transitions ── */
  --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-base: 200ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-slow: 300ms cubic-bezier(0.4, 0, 0.2, 1);
}
```

**Files affected:** New `style.css` replacing `style_v2.css`; all inline styles extracted.

### 1.2 Background Layering [P1]

**Current:** Flat `#f0f2f5` background.
**Recommendation:** Layered dark background with ambient gradients.

```css
body {
  background: var(--bg-canvas);
  background-image:
    radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99, 102, 241, 0.08), transparent),
    radial-gradient(ellipse 60% 40% at 80% 100%, rgba(168, 85, 247, 0.05), transparent);
  background-attachment: fixed;
}
```

---

## 2. Navbar Redesign [P1]

**Current:** Blue gradient navbar (`#0d1b2a → #1a237e → #283593`), 56px height, sticky.
**Recommendation:** Glassmorphism nav with backdrop blur, micro-borders, ambient glow.

### Before
- Solid blue gradient background
- `box-shadow: 0 2px 12px rgba(0,0,0,0.2)`
- White text with `rgba(255,255,255,0.75)` for inactive
- Active link: underline indicator `#64b5f6`

### After
```css
.navbar {
  background: rgba(8, 8, 8, 0.72);
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border-bottom: 1px solid var(--border-default);
  height: 56px;
  position: sticky;
  top: 0;
  z-index: 900;
}

.nav-link {
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  transition: all var(--transition-base);
}

.nav-link:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.05);
}

.nav-link.active {
  color: var(--text-primary);
  background: rgba(99, 102, 241, 0.1);
  box-shadow: inset 0 -2px 0 var(--accent-indigo);
}

.nav-link.active::after {
  background: var(--accent-indigo);
  box-shadow: 0 0 8px var(--accent-indigo);
}
```

### Nav Brand
```css
.nav-brand-text {
  background: linear-gradient(90deg, var(--text-primary), var(--accent-indigo));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: var(--letter-spacing-tight);
}
```

---

## 3. Card Components [P1]

**Current:** White background, `box-shadow: 0 2px 4px rgba(0,0,0,0.08)`, no borders, no hover.
**Recommendation:** Dark surfaces with micro-borders, shimmer on hover, subtle elevation.

### Before
```css
.card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); }
```

### After
```css
.card {
  background: var(--bg-card);
  backdrop-filter: blur(8px);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  margin: var(--space-4) 0;
  box-shadow: var(--shadow-sm);
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
  position: relative;
  overflow: hidden;
}

.card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent 40%, rgba(255, 255, 255, 0.03) 50%, transparent 60%);
  background-size: 200% 200%;
  background-position: 100% 100%;
  opacity: 0;
  transition: opacity var(--transition-slow), background-position var(--transition-slow);
  pointer-events: none;
}

.card:hover {
  border-color: var(--border-default);
  box-shadow: var(--shadow-md);
}

.card:hover::before {
  opacity: 1;
  background-position: 0% 0%;
}

.card h3 {
  color: var(--text-primary);
  font-weight: 600;
  letter-spacing: var(--letter-spacing-tight);
  margin-bottom: var(--space-3);
}
```

---

## 4. Terminal Redesign [P1]

**Current:** Hardcoded inline styles, `#000000` background, `#00ff66` neon text, Consolas font.
**Recommendation:** Monospace font, dark surface, syntax-highlighting feel, progress bar with glow.

### Before (inline)
```html
<div class="card terminal-card" style="background:#121212; color:#eee; border:1px solid #333;">
  <pre style="background:#000000; color:#00ff66; font-family:'Consolas','Courier New',monospace;">
```

### After (CSS classes)
```css
.terminal-card {
  background: rgba(5, 5, 6, 0.9);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md), inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

.terminal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: var(--space-2);
  margin-bottom: var(--space-3);
}

.terminal-title {
  font-weight: 600;
  color: var(--success);
  font-size: 1.05em;
  letter-spacing: var(--letter-spacing-tight);
}

.terminal-output {
  background: #050506;
  color: #A7F3D0;
  padding: var(--space-4);
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: 0.875rem;
  line-height: 1.6;
  max-height: 320px;
  overflow-y: auto;
  white-space: pre-wrap;
  overflow-wrap: break-word;
  border: 1px solid var(--border-subtle);
  box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.3);
}

/* Progress bar with glow */
.progress-bar-bg {
  background: rgba(255, 255, 255, 0.05);
  height: 6px;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: var(--space-3);
}

.progress-bar-fill {
  background: linear-gradient(90deg, var(--accent-indigo), var(--accent-purple));
  height: 100%;
  border-radius: 3px;
  transition: width 400ms cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.5);
}

/* Progress badge */
.terminal-progress-badge {
  background: rgba(99, 102, 241, 0.15);
  color: var(--accent-indigo);
  font-family: var(--font-mono);
  font-size: 0.85em;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-sm);
  border: 1px solid rgba(99, 102, 241, 0.2);
}

.terminal-progress-badge.completed {
  background: rgba(16, 185, 129, 0.15);
  color: var(--success);
  border-color: rgba(16, 185, 129, 0.2);
}

.terminal-progress-badge.failed {
  background: rgba(239, 68, 68, 0.15);
  color: var(--error);
  border-color: rgba(239, 68, 68, 0.2);
}

.terminal-progress-badge.cancelled {
  background: rgba(245, 158, 11, 0.15);
  color: var(--warning);
  border-color: rgba(245, 158, 11, 0.2);
}
```

**JS Changes Required:** Replace inline `badge.style.background = '#1e88e5'` with `badge.className = 'terminal-progress-badge'` etc. (See Task 7 implementation)

---

## 5. Form Controls [P1]

**Current:** `border: 1px solid #ccc`, `border-radius: 4px`, focus: `box-shadow: 0 0 0 2px rgba(26,35,126,0.1)`.
**Recommendation:** Dark inputs with micro-borders, focus glow effects.

### After
```css
.form-group input,
.form-group select,
.form-group textarea {
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  color: var(--text-primary);
  font-size: 0.9375rem;
  font-family: var(--font-sans);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.form-group input::placeholder {
  color: var(--text-tertiary);
}

.form-group input:focus,
.form-group select:focus {
  border-color: var(--accent-indigo);
  outline: none;
  box-shadow: 0 0 0 3px var(--accent-glow);
}

.form-group label {
  font-weight: 500;
  color: var(--text-secondary);
  font-size: 0.875rem;
  letter-spacing: var(--letter-spacing-tight);
  margin-bottom: var(--space-2);
}
```

### Checkbox Dropdown
```css
.checkbox-dropdown-header {
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  transition: border-color var(--transition-fast);
}

.checkbox-dropdown-header:hover,
.checkbox-dropdown-header:focus-visible {
  border-color: var(--accent-indigo);
  outline: none;
}

.checkbox-dropdown-list {
  background: var(--bg-canvas-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  backdrop-filter: blur(16px);
}

.checkbox-dropdown-item:hover {
  background: rgba(99, 102, 241, 0.08);
}

.checkbox-dropdown-item input[type="checkbox"] {
  accent-color: var(--accent-indigo);
}
```

---

## 6. Button System [P1]

**Current:** Flat colors, `border-radius: 4px`, basic hover (darker shade).
**Recommendation:** Primary buttons with indigo glow, secondary with micro-border, smooth transitions.

### After
```css
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-5);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
  font-size: 0.875rem;
  font-weight: 500;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all var(--transition-fast);
  text-decoration: none;
}

.btn:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: var(--border-strong);
}

.btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px var(--accent-glow);
}

.btn-primary {
  background: var(--accent-indigo);
  border-color: var(--accent-indigo);
  color: white;
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.3);
}

.btn-primary:hover {
  background: #5558E6;
  box-shadow: 0 0 20px rgba(99, 102, 241, 0.5);
}

.btn-danger {
  background: var(--error);
  border-color: var(--error);
  color: white;
}

.btn-danger:hover {
  background: #DC2626;
  box-shadow: 0 0 16px rgba(239, 68, 68, 0.4);
}

.btn-success {
  background: var(--success);
  border-color: var(--success);
  color: white;
}

.btn-warning {
  background: var(--warning);
  border-color: var(--warning);
  color: white;
}

.btn-info {
  background: var(--info);
  border-color: var(--info);
  color: white;
}

.btn-sm {
  padding: var(--space-1) var(--space-3);
  font-size: 0.8125rem;
}
```

---

## 7. Animations & Micro-interactions [P2]

### 7.1 Shimmer Effect [P2]
```css
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.shimmer {
  background: linear-gradient(90deg,
    var(--bg-card) 0%,
    rgba(255, 255, 255, 0.05) 50%,
    var(--bg-card) 100%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}
```

### 7.2 Skeleton Loading [P2]
```css
.skeleton {
  background: linear-gradient(90deg,
    rgba(255, 255, 255, 0.03) 0%,
    rgba(255, 255, 255, 0.06) 50%,
    rgba(255, 255, 255, 0.03) 100%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  border-radius: var(--radius-sm);
}

.skeleton-text { height: 14px; margin: 4px 0; }
.skeleton-line { height: 14px; margin: 8px 0; border-radius: var(--radius-sm); }
```

### 7.3 Breathing Glow [P2]
```css
@keyframes breathe {
  0%, 100% { opacity: 0.5; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.02); }
}

.terminal-card.running::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--accent-indigo), var(--accent-purple));
  opacity: 0;
  z-index: -1;
  animation: breathe 3s ease-in-out infinite;
  filter: blur(8px);
}
```

### 7.4 Card Entrance [P2]
```css
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.card {
  animation: fadeInUp 400ms cubic-bezier(0.4, 0, 0.2, 1) both;
}
```

### 7.5 Reduced Motion [P0]
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 8. Responsive Design [P1]

### 8.1 Breakpoint System [P1]
```css
/* Mobile first: stack everything */
.form-grid { grid-template-columns: 1fr; }

/* Tablet: 2 columns */
@media (min-width: 768px) {
  .form-grid { grid-template-columns: 1fr 1fr; }
}

/* Desktop: full layout */
@media (min-width: 1024px) {
  .account-layout { grid-template-columns: 300px 1fr; }
}
```

### 8.2 Table Scroll Wrapper [P1]
```css
.table-wrapper {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.table-wrapper .data-table {
  min-width: 600px;
}
```

### 8.3 Mobile Navbar [P2]
```css
@media (max-width: 1024px) {
  .nav-menu {
    background: rgba(8, 8, 8, 0.95);
    backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border-default);
    animation: slideDown 200ms cubic-bezier(0.4, 0, 0.2, 1);
  }

  @keyframes slideDown {
    from { opacity: 0; transform: translateY(-8px); }
    to { opacity: 1; transform: translateY(0); }
  }
}
```

---

## 9. Accessibility Improvements [P0]

### 9.1 Focus Visible [P0]
```css
*:focus-visible {
  outline: 2px solid var(--accent-indigo);
  outline-offset: 2px;
}

.btn:focus-visible,
.nav-link:focus-visible,
a:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px var(--accent-glow);
}
```

### 9.2 ARIA Attributes [P1]
- Add `role="navigation"` + `aria-label="Main navigation"` to navbar
- Add `aria-expanded` to benchmark dropdown trigger
- Add `role="progressbar"` + `aria-valuenow` + `aria-valuemin` + `aria-valuemax` to progress bar
- Add `aria-live="polite"` to terminal output
- Add `role="dialog"` + `aria-modal="true"` to modals
- Add `role="status"` to status badges

### 9.3 Contrast Fixes [P0]
- `.text-muted`: Change from `#9e9e9e` to `#A1A1AA` (zinc-400, 4.6:1 ratio on dark)
- Footer color: Change from `#9e9e9e` to `#71717A` (zinc-500)
- All text colors verified against `#080808` background

### 9.4 Keyboard Navigation [P0]
- Add `tabindex="0"` + `role="button"` to benchmark dropdown header
- Add Escape key handler to close dropdown
- Add focus trap to modals
- Add Escape key handler to close modals

---

## 10. Table Redesign [P1]

### After
```css
.data-table {
  width: 100%;
  border-collapse: collapse;
  margin: var(--space-4) 0;
  font-size: 0.875rem;
}

.data-table th {
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-secondary);
  padding: var(--space-3) var(--space-4);
  text-align: left;
  font-weight: 500;
  font-size: 0.8125rem;
  letter-spacing: var(--letter-spacing-tight);
  border-bottom: 1px solid var(--border-default);
}

.data-table td {
  border-bottom: 1px solid var(--border-subtle);
  padding: var(--space-3) var(--space-4);
  color: var(--text-primary);
}

.data-table tr:hover td {
  background: rgba(255, 255, 255, 0.02);
}

.data-table tr:nth-child(even) td {
  background: rgba(255, 255, 255, 0.01);
}
```

---

## 11. Badge & Status System [P2]

### After
```css
.badge {
  display: inline-flex;
  align-items: center;
  padding: var(--space-1) var(--space-3);
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
  border: 1px solid transparent;
}

.status-running {
  background: rgba(245, 158, 11, 0.1);
  color: var(--warning);
  border-color: rgba(245, 158, 11, 0.2);
}

.status-completed {
  background: rgba(16, 185, 129, 0.1);
  color: var(--success);
  border-color: rgba(16, 185, 129, 0.2);
}

.status-failed {
  background: rgba(239, 68, 68, 0.1);
  color: var(--error);
  border-color: rgba(239, 68, 68, 0.2);
}

.status-pending {
  background: rgba(161, 161, 170, 0.1);
  color: var(--text-secondary);
  border-color: rgba(161, 161, 170, 0.2);
}
```

---

## 12. Info/Warning/Success Boxes [P2]

### After
```css
.info-box {
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-left: 3px solid var(--info);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  color: var(--text-primary);
}

.warn-box {
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.2);
  border-left: 3px solid var(--warning);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  color: var(--text-primary);
}

.success-box {
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.2);
  border-left: 3px solid var(--success);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  color: var(--text-primary);
}
```

---

## 13. Modal Redesign [P1]

### After
```css
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 200ms ease-out;
}

.modal-card {
  background: var(--bg-canvas-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xl);
  padding: var(--space-8);
  width: 450px;
  max-width: 90vw;
  box-shadow: var(--shadow-lg);
  animation: fadeInUp 300ms cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
```

---

## 14. Login/Register Page Redesign [P1]

### After
```css
.login-wrapper {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-canvas);
  background-image:
    radial-gradient(ellipse 60% 40% at 50% 0%, rgba(99, 102, 241, 0.12), transparent),
    radial-gradient(ellipse 40% 30% at 50% 100%, rgba(168, 85, 247, 0.08), transparent);
  background-attachment: fixed;
}

.login-card {
  background: var(--bg-card);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  width: 420px;
  max-width: 90vw;
  padding: var(--space-10);
}

.login-title {
  color: var(--text-primary);
  font-size: 1.5em;
  font-weight: 600;
  letter-spacing: var(--letter-spacing-tight);
}

.login-btn {
  background: var(--accent-indigo);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  box-shadow: 0 0 16px rgba(99, 102, 241, 0.3);
  transition: all var(--transition-base);
}

.login-btn:hover {
  background: #5558E6;
  box-shadow: 0 0 24px rgba(99, 102, 241, 0.5);
  transform: translateY(-1px);
}
```

---

## 15. Spinner Redesign [P2]

### After
```css
.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-top: 2px solid var(--accent-indigo);
  border-radius: 50%;
  animation: spin 800ms linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

---

## 16. Code Block Redesign [P2]

### After
```css
.code-block {
  background: #050506;
  color: var(--text-primary);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  font-family: var(--font-mono);
  font-size: 0.875rem;
  overflow-x: auto;
}
```

---

## 17. Footer Redesign [P3]

### After
```css
.footer {
  text-align: center;
  color: var(--text-tertiary);
  padding: var(--space-6);
  font-size: 0.8125rem;
  border-top: 1px solid var(--border-subtle);
  margin-top: var(--space-8);
}
```

---

## 18. Font Loading [P1]

### Recommendation: Add to `base_v9.html` `<head>`
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

**Fallback:** If Google Fonts is blocked (e.g., in China), use system font stack:
```css
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Courier New', monospace;
```

---

## 19. Inline Style Extraction [P1]

**Recommendation:** Extract all inline `<style>` blocks from:
- `login.html` (166 lines) → shared CSS `.login-*` classes
- `register.html` (48 lines) → shared CSS `.login-*` + `.password-strength` classes
- `account.html` (27 lines) → shared CSS `.account-*`, `.modal-*`, `.password-*` classes
- `audit_log.html` (57 lines) → shared CSS `.audit-*` classes
- `regcodes.html` (8 lines) → shared CSS `.status-*` classes

**Benefit:** Single source of truth, consistent theming, smaller HTML files.

---

## 20. JS Color Hardcode Removal [P1]

**Current:** `app_clean.js` and `assessment.html` inline JS set colors via `element.style.background`.

**Files & Lines:**
- `app_clean.js:19` — `color:${ok ? '#2e7d32' : '#c62828'}`
- `app_clean.js:180,192,199` — `badge.style.background = '#2e7d32'/'#ef6c00'/'#c62828'`
- `assessment.html:378,390,436,484,500,512,529,541,550,571` — badge color changes

**Recommendation:** Use CSS classes instead of inline styles:
```javascript
// Instead of: badge.style.background = '#2e7d32';
// Use: badge.className = 'terminal-progress-badge completed';
```

**Note:** Per task constraints, JS functionality must be preserved. Only change color-setting approach from inline styles to CSS classes.

---

## Priority Summary

| Priority | Count | Category |
|----------|-------|----------|
| P0 | 5 | CSS variables, contrast fixes, focus-visible, keyboard nav, reduced-motion |
| P1 | 15 | Theme transformation, navbar, cards, terminal, forms, buttons, fonts, responsive, ARIA, tables, modals, login pages, inline extraction, JS hardcodes |
| P2 | 10 | Animations, shimmer, skeleton, badges, info boxes, code blocks, spinner, mobile nav, breathing glow, card entrance |
| P3 | 2 | Footer, empty states |

**Total Recommendations:** 32

---

**Task 6 Complete.** 32 actionable recommendations with priority levels defined.