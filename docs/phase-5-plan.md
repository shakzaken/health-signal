# Phase 5 — React Frontend (replacing Gradio)

## Where We Are After Phase 4

The system is fully functional. All intelligence lives in the backend and ai-agent services:

| Capability | Status |
|---|---|
| Document upload + auto-classification | ✅ |
| Structured data extraction (labs, symptoms, supplements) | ✅ |
| Conversational Q&A with memory (session-based) | ✅ |
| Lab analysis, pattern detection, timeline, RAG agents | ✅ |
| Doctor visit report generation | ✅ |
| Gradio UI: Upload, Ask, Doctor Report tabs | ✅ (prototype) |

**What we are replacing:**

The Gradio app was always a prototype UI — fast to build, but not suitable for a real product. It looks like a developer tool, has no real design, and is hard to extend.

Phase 5 replaces Gradio with a proper **React + Vite + TypeScript** single-page application. No backend logic moves — only the UI layer changes.

---

## Why React (not Next.js)

- This is a personal health tool with no SEO requirements — server-side rendering adds complexity with zero benefit
- All data is user-specific and private — there is nothing to pre-render
- The app is simple: three views, two API targets — React with Vite is sufficient
- Next.js brings file-based routing, server components, and a build server we do not need
- Keeping it plain React matches the project principle: **do not over-engineer**

---

## What Phase 5 Builds

A React SPA that replaces the Gradio app entirely. Same three views, better UX:

1. **Upload** — upload a document, pick a date, see processing status
2. **Chat** — multi-turn conversation with full message history, session memory, source chunks
3. **Doctor Report** — generate a structured report, choose the period

The Gradio app stays in the repo during development but is retired once the React app is complete.

---

## Project Location and Setup

```
health-signal/
  frontend/           ← new React app (Vite)
    src/
      api/            ← all HTTP calls, one file per service
      components/     ← reusable UI components
      hooks/          ← custom hooks (only when they improve clarity)
      pages/          ← one component per view (Upload, Chat, Report)
      types/          ← shared TypeScript types
      App.tsx         ← root component with tab navigation
      main.tsx        ← Vite entry point
    index.html
    package.json
    tsconfig.json
    vite.config.ts
```

**Tooling:**
- **Vite** — build tool and dev server
- **TypeScript** — strict mode
- **React 18** — functional components only
- **React Router** — not needed (three tabs, no deep linking required)

**Styling:**
- **Tailwind CSS** — utility classes, no separate CSS files per component
- Keeps components readable without a heavy component library
- **Light mode only** — white/light grey backgrounds, dark text. No dark mode.

**HTTP:**
- Native `fetch` wrapped in thin api functions — no axios, no React Query yet (simple enough without it)

---

## API Layer (`src/api/`)

Two files — one per service. Each function is a plain async function that throws on non-2xx.

**`src/api/backend.ts`** — talks to the FastAPI backend (port 8000)
```typescript
uploadDocument(file: File, sourceDate?: string): Promise<DocumentResponse>
getDocumentStatus(id: string): Promise<DocumentResponse>
```

**`src/api/aiAgent.ts`** — talks to the AI agent (port 8001)
```typescript
sendQuery(question: string, sessionId: string, documentType?: string): Promise<QueryResponse>
generateReport(periodDays: number): Promise<ReportResponse>
```

**Shared types (`src/types/index.ts`):**
```typescript
interface DocumentResponse {
  id: string
  filename: string
  document_type: string
  processing_status: string
  uploaded_at: string
}

interface QueryResponse {
  answer: string
  sources: SourceChunk[]
}

interface SourceChunk {
  filename: string
  document_type: string
  source_date: string | null
  score: number
  text: string
}

interface ReportResponse {
  report: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
}
```

---

## Pages

### Upload Page (`src/pages/UploadPage.tsx`)

Replaces the Gradio Upload tab. Contains two sections:

**Section 1 — Upload a document**
- File picker (PDF or .txt)
- Optional date input (YYYY-MM-DD)
- "Upload & Ingest" button
- Status area showing result (success / duplicate / error)

**Section 2 — Check document status**
- Text input for document ID
- "Check status" button
- Status display

No state management needed beyond local `useState`. No session required.

---

### Chat Page (`src/pages/ChatPage.tsx`)

Replaces the Gradio Ask tab. This is the most important view.

**Layout:**
- Message list (scrollable, fills available height)
- Input bar at the bottom (text input + Send button)
- "New conversation" button (top right)
- Optional document type filter (dropdown)
- Collapsible "Source chunks" panel below the input

**Session management:**
- `sessionId` is a `useState` initialized to `crypto.randomUUID()`
- "New conversation" replaces `sessionId` with a fresh UUID and clears messages
- `sessionId` is passed to every query call — this is how memory works

**Message rendering:**
- User messages aligned right, assistant messages aligned left
- Auto-scroll to bottom on new message
- Streaming is out of scope for Phase 5 — show a loading indicator while waiting

**State:**
```typescript
const [messages, setMessages] = useState<Message[]>([])
const [sessionId, setSessionId] = useState(() => crypto.randomUUID())
const [isLoading, setIsLoading] = useState(false)
const [sources, setSources] = useState<SourceChunk[]>([])
```

---

### Doctor Report Page (`src/pages/ReportPage.tsx`)

Replaces the Gradio Doctor Report tab.

**Layout:**
- Period selector: a row of buttons (30d / 90d / 180d / 365d) — cleaner than a slider
- "Generate Report" button
- Loading state while generating
- Report rendered in a styled container (preserve line breaks, section headers bold)

**State:**
```typescript
const [periodDays, setPeriodDays] = useState(90)
const [report, setReport] = useState('')
const [isLoading, setIsLoading] = useState(false)
```

---

## Components

Keep components small. Only extract when a piece of UI is reused or the parent is getting too long.

| Component | Purpose |
|---|---|
| `Layout.tsx` | Outer shell: app title + tab navigation (Upload / Chat / Report) |
| `TabNav.tsx` | The three tab buttons, highlights active tab |
| `MessageBubble.tsx` | A single chat message (user or assistant, styled differently) |
| `MessageList.tsx` | Scrollable list of `MessageBubble`, auto-scrolls to bottom |
| `ChatInput.tsx` | Text input + Send button, handles Enter key |
| `SourcePanel.tsx` | Collapsible accordion showing source chunks |
| `StatusBadge.tsx` | Colored badge for document processing status |

No component needs props drilling more than 2 levels deep. No global state store needed.

---

## Hooks

Only two — and only because the logic is genuinely reused or complex enough to test independently.

**`useChat()`** — encapsulates chat state + send logic
```typescript
function useChat() {
  // manages: messages, sessionId, isLoading, sources
  // exposes: sendMessage(), newConversation()
}
```

**`useReport()`** — encapsulates report generation state
```typescript
function useReport() {
  // manages: report, isLoading, periodDays
  // exposes: generateReport(), setPeriodDays()
}
```

---

## App Shell (`src/App.tsx`)

Simple tab switcher — no router needed.

```typescript
type Tab = 'upload' | 'chat' | 'report'

function App() {
  const [tab, setTab] = useState<Tab>('chat')
  return (
    <Layout activeTab={tab} onTabChange={setTab}>
      {tab === 'upload' && <UploadPage />}
      {tab === 'chat'   && <ChatPage />}
      {tab === 'report' && <ReportPage />}
    </Layout>
  )
}
```

---

## Environment Configuration

```
frontend/.env.local
  VITE_BACKEND_URL=http://localhost:8000
  VITE_AI_AGENT_URL=http://localhost:8001
```

Accessed in code as `import.meta.env.VITE_BACKEND_URL`. This matches Vite's convention and keeps the URLs out of source code.

---

## Implementation Order

```
1. Scaffold: vite create, install tailwind, set up folder structure
2. API layer: backend.ts + aiAgent.ts + types
3. Layout + TabNav shell (renders placeholder content per tab)
4. UploadPage (simpler, good warmup)
5. ChatPage — useChat hook + MessageList + ChatInput + MessageBubble
6. SourcePanel (collapsible sources accordion)
7. ReportPage — useReport hook + period selector + report display
8. Polish: loading states, error handling, empty states, auto-scroll
```

---

## What Does NOT Change

| Service | Change |
|---|---|
| Backend (port 8000) | None — same API |
| AI Agent (port 8001) | None — same API |
| Database | None |
| Gradio app | Kept but no longer the primary UI |

The React app is purely a new consumer of the existing APIs. Zero backend changes needed.

---

## What We Are NOT Building in Phase 5

- Authentication / login
- Multiple users (still `user_id = "default"`)
- Streaming responses
- Dark mode (the app is light mode only)
- Mobile layout (desktop-only is fine for now)
- Deployment / Docker

These are all valid future phases. Phase 5 is about having a real, clean UI — not a production-ready product.
