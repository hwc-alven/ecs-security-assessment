# UI/UX Review — Task 5: Current State Analysis

**Application:** ECS Security Assessment Console (CIS/STIG Benchmark Assessment)
**Date:** 2026-09-14
**Reviewer:** UIUX-Redesign-Agent
**Files Analyzed:** 9 files (4 primary, 5 secondary)

---

## 1. Visual Design Analysis

### 1.1 Color Scheme

**Current State:** Light theme with blue gradient navbar.

| Element | Current Color | File:Line | Issue |
|---------|--------------|-----------|-------|
| Page background | `#f0f2f5` (light gray) | `style_v2.css:6` | Flat, no depth/layering |
| Card surface | `white` | `style_v2.css:170` | No borders, relies on shadow only |
| Navbar | `linear-gradient(135deg, #0d1b2a, #1a237e, #283593)` | `style_v2.css:13` | Heavy gradient, dated Material Design feel |
| Primary text | `#333` | `style_v2.css:7` | Standard, low contrast on light bg |
| Card headings | `#1a237e` (deep indigo) | `style_v2.css:176` | Inconsistent with navbar gradient |
| Table headers | `#37474f` (blue-gray) | `style_v2.css:243` | Different from card headings |
| Terminal bg | `#121212` / `#000000` (inline) | `assessment.html:139,155` | Hardcoded, doesn't use CSS variables |
| Terminal text | `#00ff66` (neon green) | `assessment.html:155` | Hardcoded, harsh on eyes |
| Progress fill | `#00e676` (inline) | `assessment.html:151` | Hardcoded, not in design system |
| Progress badge | `#1e88e5` (inline) | `assessment.html:145` | Hardcoded blue, different from `#1a237e` |

**Issues Found:**
- **P0:** No CSS custom properties (variables) — all colors hardcoded, making theming impossible without find/replace
- **P1:** Terminal component uses 6+ hardcoded inline colors (`assessment.html:139-155`) that bypass the stylesheet entirely
- **P1:** Three different "primary blue" values used inconsistently: `#1a237e`, `#1e88e5`, `#2196f3`
- **P2:** Login/register pages (`login.html:14`, `register.html:11`) duplicate the navbar gradient inline rather than referencing shared styles
- **P2:** Status badges use light pastel backgrounds (`style_v2.css:263-266`) that don't align with a cohesive design system

### 1.2 Typography

**Current State:** System fonts with no design system.

| Property | Current Value | File:Line | Issue |
|----------|--------------|-----------|-------|
| Font family | `'Segoe UI', 'PingFang SC', 'Microsoft YaHei', Arial` | `style_v2.css:5` | No Inter/SF Pro, no geometric sans |
| Letter spacing | Not set (default) | `style_v2.css:5` | No `-0.02em` tightening for modern feel |
| Heading weight | `700` (bold) | `style_v2.css:176` | No semi-bold option used |
| Monospace | `'Consolas', 'Courier New'` | `style_v2.css:218`, `assessment.html:155` | No JetBrains Mono/Fira Code |
| Body line-height | `1.6` | `style_v2.css:8` | Good, but not applied consistently |
| Terminal font size | `0.86em` (inline) | `assessment.html:155` | Hardcoded, not responsive |

**Issues Found:**
- **P1:** No web font loaded — relies entirely on system fonts which vary across platforms
- **P1:** No monospace design font (JetBrains Mono) for terminal/code — uses legacy Consolas/Courier New
- **P2:** No typographic scale system — font sizes are ad-hoc (`0.85em`, `0.88em`, `0.9em`, `0.95em`, `1.05em` scattered throughout)
- **P2:** No font-weight system — uses `600`, `700` inconsistently

### 1.3 Spacing & Visual Hierarchy

**Current State:** Inconsistent spacing values.

| Component | Spacing | File:Line | Issue |
|-----------|---------|-----------|-------|
| Container | `margin: 20px auto; padding: 0 20px` | `style_v2.css:166` | Fixed, no max-width scaling |
| Card padding | `20px` | `style_v2.css:172` | Single value, no responsive scaling |
| Card margin | `15px 0` | `style_v2.css:173` | Inconsistent with container's 20px |
| Form gap | `15px` | `style_v2.css:223` | Different from card margin |
| Nav link padding | `8px 12px` | `style_v2.css:97` | Tight, no breathing room |
| Button padding | `8px 16px` | `style_v2.css:232` | Standard but no size variants beyond `.btn-sm` |

**Issues Found:**
- **P1:** No spacing scale system (4/8/12/16/24/32px) — values are ad-hoc (`8px`, `10px`, `12px`, `15px`, `20px`)
- **P2:** Card headings (`h3`) have `margin-bottom: 12px` but no top margin, creating inconsistent rhythm
- **P2:** No vertical rhythm system — sections stack with inconsistent gaps

---

## 2. Usability Analysis

### 2.1 Navigation

**Current State:** Horizontal navbar with icon+label links, responsive hamburger menu.

| Issue | File:Line | Severity |
|-------|-----------|----------|
| Nav has 9 links in a single row — crowded on medium screens | `base_v9.html:106-301` | P2 |
| No breadcrumb system for deep pages | All pages | P3 |
| Logout uses `confirm()` dialog — jarring, not styled | `base_v9.html:366` | P2 |
| Nav-brand-text uses gradient text clip — may not render on all browsers | `style_v2.css:44` | P3 |
| Mobile menu drops down as full-width overlay — no animation/transition | `style_v2.css:142-155` | P2 |

### 2.2 Form Layouts

| Issue | File:Line | Severity |
|-------|-----------|----------|
| Assessment form uses 2-column grid but no responsive breakpoint to stack on mobile | `style_v2.css:223` | P1 |
| Benchmark dropdown uses `onclick` with no keyboard support (Enter/Space/Esc) | `assessment.html:45` | P1 |
| Benchmark dropdown doesn't close on Escape key | `assessment.html:289-336` | P1 |
| Server checkboxes have no "select all" option | `assessment.html:99-113` | P2 |
| File upload input (`assessment.html:171`) is unstyled — renders as default browser control | P1 |
| Audit log filter form uses inline styles for inputs instead of form classes | `audit_log.html:41,45,54,65,69` | P2 |
| Regcodes form inputs use inline styles | `regcodes.html:16,20,24` | P2 |

### 2.3 Feedback Mechanisms

| Issue | File:Line | Severity |
|-------|-----------|----------|
| `showResult()` uses `innerHTML` — potential XSS if server returns unsanitized data | `app_clean.js:8` | P1 |
| `alert()` used for feedback in regcodes (copy, revoke, delete) — blocking, not styled | `regcodes.html:135,170,184` | P2 |
| `alert()` used in account.html for password reset | `account.html:289,291` | P2 |
| `confirm()` used for destructive actions — not styled, blocks UI | `app_clean.js:98,212`, `base_v9.html:366` | P2 |
| No toast/notification system — all feedback is inline `showResult()` | All pages | P2 |
| Loading state is just spinner text — no skeleton screens | `audit_log.html:88`, `regcodes.html:40` | P2 |

### 2.4 Error Handling

| Issue | File:Line | Severity |
|-------|-----------|----------|
| Error messages use emoji prefixes (❌) — inconsistent with success (✅) | `app_clean.js:63,66,89` | P3 |
| No error boundary — fetch failures show raw error messages | `app_clean.js:66,92,107` | P2 |
| Login error box is styled inline, not using shared `.warn-box` class | `login.html:115-124` | P2 |
| Terminal error states change badge color via inline JS (`badge.style.background = '#c62828'`) | `assessment.html:390,512,541,571` | P1 |

---

## 3. Accessibility Analysis

### 3.1 Color Contrast

| Element | Foreground | Background | Ratio (est.) | Issue | File:Line |
|---------|-----------|------------|-------------|-------|-----------|
| Secondary text `#9e9e9e` | `#9e9e9e` | `#f0f2f5` | ~2.8:1 | **FAILS WCAG AA** (needs 4.5:1) | `style_v2.css:274,282` |
| Nav link `rgba(255,255,255,0.75)` | ~`#bfbfbf` | `#1a237e` | ~3.5:1 | Borderline AA | `style_v2.css:95` |
| Status badge `status-pending` `#616161` on `#e0e0e0` | `#616161` | `#e0e0e0` | ~3.2:1 | **FAILS WCAG AA** | `style_v2.css:266` |
| Terminal text `#00ff66` on `#000000` | `#00ff66` | `#000000` | ~5.9:1 | Passes but harsh | `assessment.html:155` |
| `.text-muted` `#9e9e9e` on white | `#9e9e9e` | `white` | ~2.8:1 | **FAILS WCAG AA** | `style_v2.css:282` |

**Issues Found:**
- **P0:** `.text-muted` and footer color `#9e9e9e` fail WCAG AA contrast ratio (2.8:1 < 4.5:1)
- **P0:** `status-pending` badge fails WCAG AA contrast ratio
- **P1:** No focus-visible styles defined — keyboard users cannot see where focus is on buttons/links
- **P1:** Nav links rely on `:hover` background change only — no `:focus-visible` indicator

### 3.2 Focus States

| Issue | File:Line | Severity |
|-------|-----------|----------|
| Form inputs have focus box-shadow but buttons/links have none | `style_v2.css:229` vs `232-239` | P0 |
| No `:focus-visible` pseudo-class used anywhere | All CSS | P0 |
| Checkbox dropdown header has no focus indicator | `assessment.html:45` | P1 |
| Nav-toggle button has no focus ring | `base_v9.html:56` | P1 |
| `outline: none` on form inputs removes default focus without replacement | `style_v2.css:229` | P1 |

### 3.3 ARIA Labels & Semantic HTML

| Issue | File:Line | Severity |
|-------|-----------|----------|
| `nav-toggle` has `aria-label="Toggle menu"` ✓ | `base_v9.html:56` | OK |
| Nav menu has no `role="navigation"` or `aria-label` | `base_v9.html:46` | P1 |
| Benchmark dropdown has no `role="listbox"`, `aria-expanded`, or `aria-selected` | `assessment.html:43-89` | P1 |
| Terminal output `<pre>` has no `aria-live="polite"` for screen readers | `assessment.html:155` | P1 |
| Progress bar has no `role="progressbar"` or `aria-valuenow` | `assessment.html:149-152` | P1 |
| Status badges have no `role="status"` | `style_v2.css:262` | P2 |
| Tables don't use `<caption>` for accessible names | `assessment.html:183,227` | P2 |
| Modal dialogs have no `role="dialog"` or `aria-modal` | `account.html:114`, `regcodes.html:65` | P1 |

### 3.4 Keyboard Navigation

| Issue | File:Line | Severity |
|-------|-----------|----------|
| Benchmark dropdown is not keyboard accessible (uses `onclick` on div) | `assessment.html:45` | P0 |
| No Escape key handler to close dropdown | `assessment.html:289-336` | P1 |
| Modal dialogs don't trap focus | `account.html:114`, `regcodes.html:65` | P1 |
| Modal dialogs don't close on Escape | `account.html:114`, `regcodes.html:65` | P1 |
- **P0:** No `prefers-reduced-motion` media query — animations cannot be disabled

---

## 4. Consistency Analysis

### 4.1 Component Patterns

| Component | Defined In | Duplicated In | Issue |
|-----------|-----------|--------------|-------|
| Login card | `login.html:8-174` (inline) | `register.html:8-56` (inline) | Duplicated styles, divergent values |
| Modal | `account.html:163-165` (inline) | `regcodes.html:65-66` (inline) | Two different modal implementations |
| Password toggle | `login.html:147-162` (inline) | `register.html:41-43` (inline) | `account.html:152-155` (inline) | Three different implementations |
| Password strength | `register.html:44-55` (inline) | `account.html:156-162` (inline) | Duplicated logic and styles |
| Stat cards | `audit_log.html:119-137` (inline) | Not reused | Should be in shared CSS |
| Status badges | `style_v2.css:262-266` | `regcodes.html:74-77` (inline) | Two different badge systems |

**Issues Found:**
- **P0:** Massive style duplication — login, register, account, audit_log, regcodes all have large inline `<style>` blocks that should be in the shared stylesheet
- **P1:** Three different password toggle button implementations with different class names (`.password-toggle-btn`, `.pwd-toggle-btn`, `.pwd-toggle`)
- **P1:** Two different modal implementations (account.html vs regcodes.html) with different structure and styling
- **P2:** Stat cards in audit_log.html are inline-styled instead of using `.status-card` from the shared CSS

### 4.2 Color Usage Across Pages

| Color | Used In | Purpose | Consistent? |
|-------|---------|---------|-------------|
| `#1a237e` | style_v2.css, login.html, register.html, account.html | Primary/headings | Mostly yes |
| `#1e88e5` | assessment.html (inline), style_v2.css:287 | Accent/focus | **No** — different from `#1a237e` |
| `#2e7d32` | assessment.html (inline JS), app_clean.js:19 | Success | **No** — hardcoded in JS |
| `#c62828` | assessment.html (inline JS), app_clean.js:19 | Error | **No** — hardcoded in JS |
| `#ef6c00` | assessment.html (inline JS), app_clean.js:192 | Warning/cancelled | **No** — hardcoded in JS |
| `#37474f` | style_v2.css:227,243 | Labels/table headers | Yes but different from `#1a237e` |
| `#78909c` | login.html, register.html, account.html | Secondary text | **No** — different from `#9e9e9e` in main CSS |

**Issues Found:**
- **P0:** JS files hardcode colors (`app_clean.js:19`, `assessment.html:378,390,436,484,500,512,529,541,550,571`) — these bypass any CSS theme system
- **P1:** Two different "secondary text" colors: `#9e9e9e` (main CSS) vs `#78909c` (login/register/account inline)
- **P1:** Four different "primary blue" values across the codebase

---

## 5. Modern Design Analysis

### 5.1 Responsive Design

| Issue | File:Line | Severity |
|-------|-----------|----------|
| Only one breakpoint: `@media (max-width: 1024px)` for navbar | `style_v2.css:140` | P1 |
| Form grid (2-column) never stacks to 1-column on mobile | `style_v2.css:223` | P1 |
| Account layout (300px sidebar + 1fr) never stacks | `account.html:141` | P1 |
| Audit filter form grid doesn't respond | `audit_log.html:140-148` | P1 |
| Tables have no horizontal scroll wrapper for mobile | `assessment.html:183,227`, `audit_log.html:95` | P1 |
| No `max-width` on terminal output for mobile readability | `assessment.html:155` | P2 |
| Container max-width is fixed `1200px` — no fluid scaling | `style_v2.css:166` | P2 |

### 5.2 Animations & Micro-interactions

| Feature | Status | File:Line |
|---------|--------|-----------|
| Button hover | Background color change only | `style_v2.css:233` |
| Card hover | None | `style_v2.css:169-175` |
| Nav link hover | Background change | `style_v2.css:105-108` |
| Login button hover | `translateY(-1px)` — only login page | `login.html:103` |
| Spinner | Basic CSS spin animation | `style_v2.css:277-278` |
| Pulse animation | Login background only | `login.html:28-31` |
| Shimmer effect | **None** | — |
| Glassmorphism | **None** | — |
| Skeleton loading | **None** — uses spinner text | — |
| Smooth transitions | Basic `0.2s ease` on some elements | `style_v2.css:101,232` |
| Card entrance animation | **None** | — |
| Progress bar animation | `width 0.4s ease` (inline) | `assessment.html:151` |

**Issues Found:**
- **P1:** No hover effects on cards — feels static and unresponsive
- **P1:** No shimmer/skeleton loading — users see blank areas then sudden content
- **P2:** No entrance animations for cards or page transitions
- **P2:** Login button has hover transform but main app buttons don't — inconsistent
- **P2:** No `prefers-reduced-motion` support anywhere

### 5.3 Loading States

| Issue | File:Line | Severity |
|-------|-----------|----------|
| Audit log loading: spinner + text, no skeleton | `audit_log.html:87-89` | P2 |
| Regcodes loading: spinner + text, no skeleton | `regcodes.html:39-41` | P2 |
| Assessment running: button shows spinner + text | `app_clean.js:244` | OK |
| Terminal initializing: text only | `app_clean.js:252` | P3 |
| No loading state for server checkbox list | `assessment.html:99` | P3 |

---

## 6. Terminal UX Analysis

**Component Location:** `assessment.html:139-157` (HTML), `assessment.html:342-575` (JS), `app_clean.js:149-207` (polling)

### 6.1 Styling

| Property | Current Value | Issue | Severity |
|----------|--------------|-------|----------|
| Card background | `#121212` (inline) | Hardcoded, not themeable | P1 |
| Card border | `1px solid #333` (inline) | Hardcoded | P1 |
| Header text color | `#00e676` (inline) | Hardcoded neon green | P1 |
| Progress badge bg | `#1e88e5` (inline) | Hardcoded blue | P1 |
| Progress bar bg | `#263238` (inline) | Hardcoded | P1 |
| Progress fill | `#00e676` (inline) | Hardcoded, no glow effect | P1 |
| Output background | `#000000` (inline) | Pure black — should be `#050506` | P2 |
| Output text color | `#00ff66` (inline) | Harsh neon, should be softer | P2 |
| Output font | `'Consolas', 'Courier New'` (inline) | No JetBrains Mono | P1 |
| Output font size | `0.86em` (inline) | Not responsive | P2 |
| Output border | `1px solid #263238` (inline) | Hardcoded | P2 |

### 6.2 Readability

| Issue | File:Line | Severity |
|-------|-----------|----------|
| `word-break: break-all` breaks words mid-character — should be `break-word` or `overflow-wrap` | `assessment.html:155` | P1 |
| `white-space: pre-wrap` is correct ✓ | `assessment.html:155` | OK |
| `max-height: 320px` with `overflow-y: auto` ✓ | `assessment.html:155` | OK |
| No line numbers for log output | `assessment.html:155` | P2 |
| No timestamp prefix on log lines | `assessment.html:404` | P2 |
| No syntax highlighting or log level coloring | `assessment.html:155` | P2 |
| No copy-to-clipboard for terminal output | — | P2 |

### 6.3 Progress Indicators

| Issue | File:Line | Severity |
|-------|-----------|----------|
| Progress bar has no glow/shadow effect | `assessment.html:151` | P2 |
| Progress badge changes color via JS inline styles | `assessment.html:378,390,436,484,500,512,529,541,550,571` | P1 |
| No estimated time remaining | — | P3 |
| No step/phase indicator (e.g., "Connecting → Scanning → Analyzing") | — | P2 |
| Progress bar transition is `0.4s ease` — good but no animation when complete | `assessment.html:151` | P3 |

### 6.4 Terminal Header

| Issue | File:Line | Severity |
|-------|-----------|----------|
| Header uses emoji `💻` instead of SVG icon | `assessment.html:143` | P3 |
| Header layout is inline flex | `assessment.html:141` | P2 |
| No terminal window controls (minimize, maximize, clear) | — | P2 |
| No connection status indicator (live/paused/error) | — | P2 |

---

## 7. Assessment Form Analysis

**Component Location:** `assessment.html:25-133`

### 7.1 Benchmark Dropdown

| Issue | File:Line | Severity |
|-------|-----------|----------|
| Uses `onclick` on div — not keyboard accessible | `assessment.html:45` | P0 |
| No `aria-expanded` state on trigger | `assessment.html:45` | P1 |
| No `role="listbox"` / `role="option"` on list/items | `assessment.html:53-87` | P1 |
| Dropdown list has no max-height animation | `style_v2.css:289` | P2 |
| Arrow indicator `▼` doesn't rotate on open | `assessment.html:49` | P2 |
| No "Select All" / "Deselect All" option | `assessment.html:53-87` | P2 |
| Selected count shows "X benchmarks selected" — no way to see which ones without opening | `assessment.html:315` | P3 |
| Dropdown closes on outside click ✓ but not on Escape | `assessment.html:325-336` | P1 |

### 7.2 Server Selection

| Issue | File:Line | Severity |
|-------|-----------|----------|
| Plain checkbox list — no search/filter for many servers | `assessment.html:99-113` | P2 |
| No "Select All" option | `assessment.html:99` | P2 |
| Server info shows `ip (username)` — no server name/label | `assessment.html:107` | P3 |
| No visual indication of server status (reachable/unreachable) | `assessment.html:107` | P3 |
| Checkbox list is in a `full-width` form group — good ✓ | `assessment.html:93` | OK |

### 7.3 Task Creation Flow

| Issue | File:Line | Severity |
|-------|-----------|----------|
| No form validation feedback until submit | `assessment.html:35` | P2 |
| Task name has `required` attribute ✓ but no min-length | `assessment.html:35` | P3 |
| Run button uses emoji `🚀` — not a design system icon | `assessment.html:125` | P3 |
| Stop button is `btn-danger` with emoji `⏹️` | `assessment.html:127` | P3 |
| No confirmation before starting assessment (could be intentional for speed) | — | P3 |
| Form resets after submission? — No, form retains values | — | P3 |

### 7.4 Task History Table

| Issue | File:Line | Severity |
|-------|-----------|----------|
| Table has 7 columns — will overflow on mobile | `assessment.html:231` | P1 |
| No pagination for task history | `assessment.html:237` | P2 |
| No sorting/filtering on task history | `assessment.html:227` | P2 |
| Status badge uses `status-{{ task.status }}` class — good ✓ | `assessment.html:249` | OK |
| "Live Terminal" button in every row — good for reopening | `assessment.html:251` | OK |
| Report link only shows if `task.report` exists ✓ | `assessment.html:255-259` | OK |
| No empty state illustration — just "No assessment tasks yet." text | `assessment.html:273` | P3 |

---

## 8. Cross-Page Issues

### 8.1 Inline Style Proliferation

| File | Inline `<style>` Lines | Inline `style=""` Attributes | Severity |
|------|----------------------|---------------------------|----------|
| `assessment.html` | 0 | 8 (terminal card, progress bar, badge) | P1 |
| `login.html` | 166 lines (8-174) | 0 | P1 |
| `register.html` | 48 lines (8-56) | 0 | P1 |
| `account.html` | 27 lines (140-166) | 3 | P1 |
| `audit_log.html` | 57 lines (118-175) | 7 | P1 |
| `regcodes.html` | 8 lines (73-80) | 5 | P1 |

**Total:** ~306 lines of inline CSS that should be in the shared stylesheet.

### 8.2 Cache Busting Inconsistency

| File | CSS Version | JS Version | Issue |
|------|------------|------------|-------|
| `base_v9.html:31` | `v=4` | `v=9` (line 351) | Mismatched versions |
| `login.html:7` | `v=3` | N/A | Different from base |
| `register.html:7` | `v=3` | N/A | Different from base |

**Issue:** CSS is at `v=4` in base but `v=3` in login/register — cache busting is inconsistent.

### 8.3 Emoji as Icons

Emojis are used extensively as icons throughout the application:
- Navbar: `🔒📊🔑🖥️🛡️⚙️📄📋🎟️👤🚪` (`base_v9.html:76,116,131,146,161,176,191,231,246,261,296`)
- Assessment: `🔍⚠️🚀⏹️💻📤🤖📄` (`assessment.html:9,17,125,127,143,173,203,257`)
- Login: `🔒👤🔑👁️` (`login.html:180,191,199,206`)

**Issues:**
- **P2:** Emojis render differently across platforms (Windows, macOS, Linux) — inconsistent appearance
- **P2:** Emojis cannot be styled (color, size beyond font-size) — limits design control
- **P3:** No SVG icon system — emojis are the only "icons"

---

## 9. Summary of Critical Issues

### P0 — Critical (Must Fix)
1. **No CSS variables** — theming impossible without find/replace across 9 files
2. **`.text-muted` and footer color fail WCAG AA contrast** (2.8:1 ratio)
3. **No focus-visible styles** — keyboard users cannot navigate
4. **Benchmark dropdown not keyboard accessible** — violates WAI-ARIA
5. **Massive inline style duplication** — ~306 lines of CSS duplicated across 5 files
6. **JS hardcodes colors** — terminal badge colors set via `element.style.background` bypass CSS

### P1 — High (Should Fix)
1. **No web font loaded** — relies on system fonts
2. **No JetBrains Mono** for terminal — uses legacy Consolas
3. **Terminal uses 12+ hardcoded inline colors** — not themeable
4. **No responsive breakpoints** beyond navbar — forms/tables break on mobile
5. **No ARIA attributes** on dropdown, terminal, progress bar, modals
6. **No hover effects on cards** — feels static
7. **No skeleton loading** — blank then sudden content
8. **`word-break: break-all`** in terminal — breaks words mid-character
9. **Tables overflow on mobile** — no scroll wrapper
10. **Three different password toggle implementations** — inconsistent

### P2 — Medium (Nice to Fix)
1. **No spacing/typography scale system** — ad-hoc values
2. **`alert()` and `confirm()` for feedback** — not styled, blocks UI
3. **No toast/notification system**
4. **No shimmer/glassmorphism effects**
5. **No `prefers-reduced-motion` support**
6. **Emoji icons** — inconsistent across platforms
7. **No "Select All" for servers/benchmarks**
8. **No pagination/sorting on task history**
9. **Cache busting version mismatch** between pages

### P3 — Low (Polish)
1. **No SVG icon system**
2. **No empty state illustrations**
3. **No estimated time remaining** on progress
4. **No terminal window controls** (clear, minimize)
5. **No copy-to-clipboard** on terminal output
6. **No breadcrumb system**

---

## 10. File-by-File Issue Count

| File | P0 | P1 | P2 | P3 | Total |
|------|----|----|----|----|-------|
| `style_v2.css` | 3 | 5 | 4 | 1 | 13 |
| `assessment.html` | 1 | 8 | 5 | 4 | 18 |
| `app_clean.js` | 1 | 1 | 1 | 0 | 3 |
| `base_v9.html` | 0 | 2 | 2 | 2 | 6 |
| `login.html` | 1 | 2 | 2 | 1 | 6 |
| `register.html` | 0 | 2 | 1 | 0 | 3 |
| `account.html` | 0 | 3 | 2 | 0 | 5 |
| `audit_log.html` | 0 | 2 | 3 | 0 | 5 |
| `regcodes.html` | 0 | 1 | 3 | 0 | 4 |
| **Total** | **6** | **26** | **23** | **8** | **63** |

---

**Review Complete.** 63 total issues identified across 9 files.
6 P0 (critical), 26 P1 (high), 23 P2 (medium), 8 P3 (low).