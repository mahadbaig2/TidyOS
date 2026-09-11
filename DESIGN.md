# DESIGN.md

# TidyOS UI Design System

## 1. Design Goal

TidyOS should feel like a polished native productivity utility, not an AI chatbot wrapped in a desktop window.

The interface must communicate three things immediately:

1. **Calm control** — the filesystem is being handled.
2. **Intelligence** — TidyOS understands content and structure.
3. **Trust** — the user can see, review, and undo what agents do.

Avoid sci-fi AI visual clichés. Do not use glowing brains, robot illustrations, excessive gradients, animated neural networks, or chat bubbles as the primary interface.

The product is closer in spirit to a premium system utility, command palette, file manager intelligence layer, or modern developer tool.

---

## 2. Visual Direction

### Overall
- Minimal
- Desktop-native
- Dense enough to feel powerful
- Spacious enough to remain calm
- Strong hierarchy
- Primarily neutral palette
- Subtle borders
- Restrained shadows
- Crisp typography
- Very limited animation

### Theme
Build **dark mode first** for the hackathon demo.

Suggested palette:

```text
App background        #0B0C0E
Sidebar/background    #101114
Surface               #15171B
Raised surface        #1B1E23
Border                #272A31
Primary text          #F4F4F5
Secondary text        #A1A1AA
Muted text            #71717A
Accent                #F4F4F5 / near-white
Success               restrained green
Warning               restrained amber
Danger                restrained red
Protected             cool blue/indigo
```

Do not oversaturate status colors.

Use status colors for meaning, not decoration.

---

## 3. Typography

Use a clean sans-serif available for redistribution or a reliable system font.

Preferred:
- Inter if bundled/licensed appropriately
- Segoe UI as Windows-native fallback

Hierarchy:

```text
Display / hero      28-34px equivalent
Page title          22-26px
Section title       15-18px semibold
Body                13-14px
Metadata            11-12px
Monospace/path      11-12px
```

Use monospaced styling selectively for:
- filesystem paths;
- filenames when useful;
- technical project markers.

Do not use giant marketing typography inside the actual application.

---

## 4. Window Structure

Recommended minimum demo window:
- approximately 1200x760
- responsive down to approximately 1000x650

Structure:

```text
┌───────────────────────────────────────────────────────────────┐
│ Optional slim title/top bar                                  │
├──────────────┬────────────────────────────────────────────────┤
│              │                                                │
│ Sidebar      │ Main Content                                   │
│              │                                                │
│ Home         │                                                │
│ Search       │                                                │
│ Organize     │                                                │
│ Review       │                                                │
│ Activity     │                                                │
│              │                                                │
│ Settings     │                                                │
│              │                                                │
│ ● Watching  │                                                │
└──────────────┴────────────────────────────────────────────────┘
```

Sidebar width: approximately 190-220px.

Main content should use a max readable width where appropriate but allow tables/lists to stretch.

---

## 5. Navigation

Primary navigation:
- Home
- Search
- Organize
- Review
- Activity

Settings anchored near bottom.

Bottom status:
- green dot + `Watching`
- paused state
- offline/AI unavailable state if applicable

Use simple line icons.

Active navigation:
- subtle raised background;
- high-contrast label;
- no large accent pill.

---

# 6. Home Screen

Purpose:
Give immediate confidence that TidyOS is active and the filesystem is under control.

Suggested layout:

```text
Good evening.

Your filesystem is under control.                   ● Watching

┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌───────────────┐
│ 12,491         │ │ 128            │ │ 14             │ │ 3             │
│ Files indexed  │ │ Organized      │ │ Protected      │ │ Need review   │
└────────────────┘ └────────────────┘ └────────────────┘ └───────────────┘

Recent activity
────────────────────────────────────────────────────────────────────────
✓ Vercel_Invoice_Sep_2026.pdf
  Downloads → Finance / Software / Vercel
  Organized 2m ago                                      Why?    Undo

🛡 mahad-ai-portfolio
   Protected Next.js project
   TidyOS will index this project but never reorganize its structure.

✓ FastAPI_CORS_Error.png
  Screenshots → Development / Errors
```

Do not fill the dashboard with charts merely to make it look analytical.

---

# 7. Search Screen — Hero Experience

This is one of the most important screens and a hackathon wow moment.

The search field should dominate the initial state.

```text
Find anything.

┌─────────────────────────────────────────────────────────────────┐
│  the PDF about the agent hackathon I downloaded yesterday   ⌘K │
└─────────────────────────────────────────────────────────────────┘

Try:
"my latest AI resume"
"the screenshot with the FastAPI error"
"Vercel invoice from last month"
```

After search:

```text
3 results for "the PDF about the agent hackathon"

┌─────────────────────────────────────────────────────────────────┐
│ PDF                                                             │
│ AI_Tinkerers_Agents_Everywhere_Handbook.pdf                    │
│ Projects / Hackathons / AI Tinkerers                           │
│                                                                 │
│ 94% match                                                       │
│ Hackathon handbook covering agent requirements, judging...      │
│                                                                 │
│ Matched: agent hackathon · PDF · downloaded yesterday           │
│                                                   Open  Show     │
└─────────────────────────────────────────────────────────────────┘
```

### Search result requirements
Each result should show:
- icon/type;
- filename;
- path;
- semantic match confidence;
- short summary/snippet;
- why it matched;
- Open;
- Show in Folder.

Do not show raw embedding scores without a human-readable explanation.

Search must feel instantaneous for already indexed files.

---

# 8. Organize Screen

Purpose:
Preview first-run cleanup and bulk organization.

Header:

```text
Organize

TidyOS analyzed 1,284 files.
211 can be safely organized.
14 structured projects are protected.
16 need your review.
```

Use segmented filters:
- All
- Ready
- Protected
- Review

Proposal row/card:

```text
PDF     document(17).pdf                              97%

        Downloads/document(17).pdf
        ↓
        Finance/Software/Vercel/Vercel_Invoice_Sep_2026.pdf

        Vercel invoice for September 2026.

        [Approve] [Reject] [Change]
```

Bulk action:
`Approve 38 safe changes`

Never make the destructive/autonomous button visually reckless. The interface should reinforce review and control.

---

# 9. Protected Project UX

Protected structure is a product feature and should be visually impressive.

Example:

```text
🛡 Protected structure

mahad-ai-portfolio
Next.js + Git repository

Detected:
package.json
next.config.ts
tsconfig.json
.git/
pnpm-lock.yaml

TidyOS understands that this directory's structure is required by the application.
It will not rename, move, or reorganize files inside it.

[Indexed for Search ✓]
```

Use a subtle blue/indigo shield treatment.

Do not make protected projects look like errors.

---

# 10. Review Screen

Purpose:
Resolve uncertainty without forcing the user into a file manager.

```text
Needs your attention                                      3

report-final.pdf
TidyOS thinks this may be:
Research / AI

Confidence: 72%

Suggested destination
[ Research / AI                         v ]

[Approve] [Leave where it is]
```

Provide concise rationale.

Do not expose raw chain-of-thought.

---

# 11. Activity Screen

This is the trust/audit screen.

Use chronological activity.

```text
Today

18:42
✓ Organized
document(17).pdf
→ Finance/Software/Vercel/Vercel_Invoice_Sep_2026.pdf
97% confidence

Why?
"This document is a September 2026 Vercel invoice..."

[Undo]

18:31
🛡 Protected
mahad-ai-portfolio
Next.js project detected
No files changed.
```

Activity types:
- Organized
- Renamed
- Moved
- Protected
- Indexed
- Review requested
- Undone
- Failed safely

---

# 12. Settings

Keep settings simple.

Sections:

### Managed Folders
Rows with:
- path
- Auto / Review
- enabled
- remove

### Exclusions
Paths TidyOS never analyzes.

### Automation
- confidence threshold
- auto-organize toggle
- pause watching

### AI
- API key status
- connection status

### Search
- indexing status
- reindex button

Do not create dozens of configuration toggles for the MVP.

---

# 13. Onboarding

Onboarding should be 3-4 steps maximum.

### Step 1
**Meet TidyOS**

> Your files organize themselves, and you never have to remember where anything is again.

### Step 2
**Choose where TidyOS can work**

Folder picker.

Explain:
> TidyOS only accesses folders you approve.

### Step 3
**You're always in control**

Three trust cards:
- Structured projects are protected
- Uncertain actions require review
- Every move can be undone

### Step 4
**Understand my files**

Primary button starts initial scan.

---

# 14. Components

Build reusable components/widgets for:

- Navigation item
- Metric card
- File type icon
- File result card
- Organization proposal
- Protected project card
- Confidence badge
- Status badge
- Activity item
- Empty state
- Loading/indexing state
- Search field
- Path breadcrumb
- Primary button
- Secondary button
- Destructive/deny button
- Toast/notification

---

# 15. Status Language

Use human language.

Prefer:
- `Protected`
- `Ready to organize`
- `Needs review`
- `Watching`
- `Indexed`
- `Organized`
- `Undone`

Avoid exposing internal jargon such as:
- vectorized
- graph node
- LLM decision
- embedding generated
- state transition

Technical detail may appear in an optional "Details" area, not the default UI.

---

# 16. Confidence

Do not overuse percentages.

Use them where they help review:
- 97% confidence
- 72% confidence

For obvious successful activity, status is more important than percentage.

Recommended visual levels:
- High: 90%+
- Medium: 70-89%
- Low: under 70%, generally review

These thresholds are product defaults, not absolute truth.

---

# 17. Motion

Use very restrained animation:
- 120-200ms fades;
- subtle row insertion;
- progress transition;
- search result appearance;
- scan status.

No bouncing AI or decorative loading animations.

For the demo, one useful moment is a new file appearing in Activity after Watch Mode processes it.

---

# 18. Empty States

Search:
> Search by what you remember, not by filename.

Review:
> Nothing needs your attention.

Activity:
> TidyOS hasn't changed anything yet.

Protected:
> Structured projects TidyOS protects will appear here.

---

# 19. Error States

Errors should emphasize safe failure.

Example:

```text
Couldn't organize this file

The destination was inside a protected project, so TidyOS left the original file untouched.

[Review]
```

Never use frightening generic errors when safety logic successfully prevented an operation.

Offline:

```text
AI understanding is temporarily unavailable.
Local search and existing indexes still work.
```

---

# 20. PySide6 Implementation Guidance

Use Qt layouts rather than fixed absolute positioning.

Recommended:
- `QMainWindow`
- `QStackedWidget` for pages
- `QFrame` for cards
- `QScrollArea` for long lists
- `QListView/QTableView` where large datasets require virtualization
- custom widgets for proposal/result/activity rows
- `QThreadPool` workers
- Qt signals for state updates
- `QSystemTrayIcon` for tray behavior

Centralize styling in one QSS/theme module.

Do not scatter inline styles across every widget.

Create design tokens in Python:

```python
SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
    "xxl": 32,
}
```

Likewise centralize colors, radii, typography, and icon sizing.

---

# 21. Accessibility and Usability

- keyboard-accessible navigation;
- visible focus states;
- sufficient contrast;
- do not encode status by color alone;
- buttons must have text/tooltips where icons may be ambiguous;
- filenames/paths should support copy;
- long paths should elide gracefully but reveal full path on hover;
- confirmation/review must be clear before bulk actions.

---

# 22. Demo-Specific UI Priorities

If time becomes constrained, polish in this order:

1. Search screen
2. Home/recent activity
3. Organize cleanup plan
4. Protected project card
5. Activity/Undo
6. Review
7. Settings
8. Onboarding polish

The demo must make these moments visually obvious:
- TidyOS recognized a Next.js project and intentionally protected it.
- A newly downloaded badly named file was autonomously handled.
- A natural-language query found a file by meaning.
- The user can understand and undo agent actions.

---

# 23. Final Design Test

Before declaring UI complete, answer yes to:

- Does this look like a desktop product rather than a hackathon webpage?
- Is Search visually important enough?
- Can a judge understand the product within 10 seconds?
- Is protection visible?
- Is autonomy visible?
- Is user control visible?
- Are paths and filenames readable?
- Does the UI remain calm even with many files?
- Can the full demo be performed without opening a terminal?
