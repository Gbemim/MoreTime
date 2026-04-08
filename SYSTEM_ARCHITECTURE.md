# MoreTime System Architecture - How Everything Works Together

This document explains how all the components interact with each other, the data flow, and the system architecture.

---

## 🏗️ System Overview

The MoreTime extension has **3 main layers**:

1. **Frontend (Extension)** - Chrome extension with popup UI and content scripts
2. **Backend (API Server)** - FastAPI server handling LLM operations
3. **AI Services** - Anthropic Claude and OpenAI APIs

```
┌─────────────────────────────────────────────────────────────┐
│                    CHROME EXTENSION                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Popup UI   │  │  Background  │  │   Content   │      │
│  │  (React)     │  │   Service    │  │   Scripts   │      │
│  │              │  │   Worker     │  │             │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                  │              │
│         └─────────────────┼──────────────────┘              │
│                           │                                │
└───────────────────────────┼────────────────────────────────┘
                            │
                            │ HTTP Requests
                            │
┌───────────────────────────▼────────────────────────────────┐
│              FASTAPI BACKEND SERVER                        │
│  ┌────────────────────────────────────────────────────┐    │
│  │  API Endpoints (main.py)                          │    │
│  │  - /generate-block-rules                          │    │
│  │  - /check-metadata                                │    │
│  └──────────────┬────────────────────────────────────┘    │
│                 │                                          │
│  ┌──────────────▼────────────────────────────────────┐    │
│  │  LLM Module (llm/)                                │    │
│  │  - generation.py (rule generation)                │    │
│  │  - matching.py (metadata matching)                 │    │
│  │  - embeddings.py (semantic similarity)             │    │
│  └──────────────┬────────────────────────────────────┘    │
└─────────────────┼──────────────────────────────────────────┘
                  │
                  │ API Calls
                  │
    ┌─────────────┴─────────────┐
    │                           │
┌───▼──────┐            ┌──────▼──────┐
│ Anthropic│            │   OpenAI    │
│  Claude  │            │ Embeddings  │
└──────────┘            └─────────────┘
```

---

## 🔄 Complete User Flows

### Flow 1: User Creates a Blocking Rule

**Step-by-step interaction:**

```
1. USER ACTION
   └─> Opens extension popup
       └─> Types description in DescriptionInput component
       └─> Selects schedule in ScheduleForm component
       └─> Clicks "Generate YouTube Block Rules" button

2. POPUP COMPONENT (PopupApp.tsx)
   └─> handleGenerate() function called
       └─> Sets isGenerating = true (shows loading state)
       └─> Sends message via chrome.runtime.sendMessage()
           Message: {
             type: 'GENERATE_RULES',
             description: "gaming videos and walkthroughs"
           }

3. BACKGROUND SERVICE WORKER (background.ts)
   └─> chrome.runtime.onMessage listener receives message
       └─> handleMessage() function called
           └─> Switch case: MESSAGE_TYPES.GENERATE_RULES
               └─> Calls generateRules() from api.ts

4. API CLIENT (background/api.ts)
   └─> generateRules() function
       └─> Makes HTTP POST request to backend
           URL: http://localhost:8000/generate-block-rules
           Body: { description: "gaming videos..." }
       └─> Returns Promise<GenerateRulesResponse>

5. BACKEND API (main.py)
   └─> POST /generate-block-rules endpoint
       └─> Validates request (checks description not empty)
       └─> Calls generate_block_rules() from llm module

6. LLM GENERATION (llm/generation.py)
   └─> generate_block_rules() function
       └─> Gets Anthropic API key (config.py)
       └─> Builds prompt (_build_generation_prompt())
       └─> Creates Anthropic client
       └─> Calls Claude API (async, in thread pool)
       └─> Extracts text from response
       └─> Parses JSON (llm/utils.py)
       └─> Returns GenerateRulesResponse

7. RESPONSE FLOW (backwards)
   └─> Backend returns JSON: { summary: "..." }
   └─> api.ts receives response
   └─> background.ts sends message response
   └─> PopupApp.tsx receives response
       └─> Updates state: setGeneratedRules(response.data)
       └─> Shows GeneratedRulesView component

8. USER SAVES RULE
   └─> User clicks "Save Rule" button
       └─> handleSaveRule() in PopupApp.tsx
           └─> Creates BlockRule object:
               {
                 id: timestamp,
                 userDescription: "...",
                 aiSummary: "...",
                 schedule: {...},
                 enabled: true
               }
           └─> Sends SAVE_RULE message to background

9. BACKGROUND STORAGE (background.ts)
   └─> Receives SAVE_RULE message
       └─> Gets current rules (storage.ts)
       └─> Adds new rule to array
       └─> Saves to chrome.storage.local (storage.ts)
       └─> Calls evaluateAndUpdateRules()
           └─> Filters active rules (utils.ts)
           └─> Applies blocking rules

10. STORAGE PERSISTENCE
    └─> chrome.storage.local.set({ rules: [...] })
        └─> Rules saved in browser storage
        └─> Persists across browser restarts
```

**Visual Flow:**
```
User Input → PopupApp → chrome.runtime.sendMessage → Background Worker
    → api.ts → HTTP POST → Backend API → LLM Generation → Anthropic API
    → Response → Backend → api.ts → Background → PopupApp → UI Update
    → Save → Background → Storage → Rules Saved
```

---

### Flow 2: User Visits YouTube Video (Blocking Detection)

**Step-by-step interaction:**

```
1. USER NAVIGATION
   └─> User navigates to youtube.com/watch?v=...
       └─> Chrome loads the page
       └─> Content script (metadata-checker.ts) injected

2. CONTENT SCRIPT INITIALIZATION (metadata-checker.ts)
   └─> Script runs on page load
       └─> checkPageAgainstRules() function called
           └─> Checks if YouTube video page (isYouTubeVideoPage())
           └─> Checks if extension/system page (skip if yes)
           └─> Sends GET_ACTIVE_RULES message to background

3. BACKGROUND RULE RETRIEVAL (background.ts)
   └─> Receives GET_ACTIVE_RULES message
       └─> Calls getActiveRules()
           └─> Gets all rules from storage (storage.ts)
           └─> Filters active rules (utils.ts)
               └─> Checks if rule enabled
               └─> Checks schedule (isDurationActive or isDailyActive)
           └─> Returns active rules array

4. CONTENT SCRIPT REQUEST PREP (metadata-checker.ts)
   └─> Receives active rules
       └─> Reads current watch URL
       └─> Forwards url + rule context to background

5. RULE MATCHING (metadata-checker.ts)
   └─> For each active rule:
       └─> Calls checkRuleMatch()
           └─> Sends CHECK_METADATA message to background
               Message: {
                 type: 'CHECK_METADATA',
                 user_description: rule.userDescription,
                 url: currentUrl
               }

6. BACKGROUND API CALL (background.ts)
   └─> Receives CHECK_METADATA message
       └─> Calls checkMetadata() from api.ts

7. API CLIENT (background/api.ts)
   └─> checkMetadata() function
       └─> Makes HTTP POST to backend
           URL: http://localhost:8000/check-metadata
           Body: {
             user_description: "...",
             metadata: {...},
             url: "..."
           }

8. BACKEND METADATA CHECK (main.py)
   └─> POST /check-metadata endpoint
       └─> Calls check_metadata_matches_rule_optimized()

9. OPTIMIZED MATCHING (llm/matching.py)
   └─> check_metadata_matches_rule_optimized()
      └─> Resolves metadata (oEmbed first, page-metadata fallback)
      └─> Formats metadata for embedding
       └─> Gets embeddings (embeddings.py)
           └─> get_embedding(user_description) → OpenAI API
           └─> get_embedding(metadata_text) → OpenAI API
       └─> Calculates cosine similarity
       └─> Decision tree:
           ├─> If similarity >= 0.80: Block immediately (high confidence)
           ├─> If similarity < 0.50: Don't block (low confidence)
           └─> If 0.50 <= similarity < 0.80: Use LLM for decision
               └─> Calls check_metadata_matches_rule()
                   └─> Builds prompt with rule + metadata
                   └─> Calls Anthropic Claude API
                   └─> Parses JSON response
                   └─> Returns CheckMetadataResponse

10. RESPONSE FLOW
    └─> Backend returns: { matches: true/false, confidence: 0.0-1.0, reasoning: "..." }
    └─> api.ts receives response
    └─> background.ts sends message response
    └─> metadata-checker.ts receives response

11. BLOCKING ACTION (metadata-checker.ts)
    └─> If matches === true AND confidence >= 0.5:
        └─> Calls handleBlocking()
            └─> Stops page loading (window.stop())
            └─> Sends REDIRECT_TO_BLOCKED message to background
                └─> Background calls redirectToBlocked()
                    └─> Builds blocked URL (url-builder.ts)
                    └─> Updates tab URL to blocked.html
                        └─> Shows blocked page with rule info
```

**Visual Flow:**
```
YouTube Page Load → Content Script → Check Active Rules → Background
    → Storage → Filter Active Rules → Content Script
    → Extract Metadata → Cache Check → DOM Query
    → For Each Rule: Check Match → Background → API Client
    → HTTP POST → Backend → Embeddings (OpenAI) → Similarity Check
    → [High/Low] → Return Result OR [Medium] → LLM (Anthropic)
    → Response → Background → Content Script
    → If Match: Block → Redirect to blocked.html
```

---

### Flow 3: Schedule Evaluation (Periodic Rule Activation)

**Step-by-step interaction:**

```
1. ALARM SETUP (background.ts - on script load)
   └─> chrome.alarms.create('evaluateRules', { periodInMinutes: 1 })
       └─> Creates alarm that fires every 1 minute

2. ALARM FIRES (background.ts)
   └─> chrome.alarms.onAlarm listener triggered
       └─> Checks if alarm.name === 'evaluateRules'
           └─> Calls evaluateAndUpdateRules()

3. RULE EVALUATION (background.ts)
   └─> evaluateAndUpdateRules()
       └─> Calls getActiveRules()
           └─> Gets all rules from storage
           └─> Calls filterActiveRules() (utils.ts)

4. SCHEDULE CHECKING (utils.ts)
   └─> filterActiveRules() loops through rules
       └─> For each rule:
           ├─> If not enabled: skip
           ├─> If schedule.type === 'duration':
           │   └─> Calls isDurationActive()
           │       └─> Gets current time (Date.now())
           │       └─> Calculates endTime = startTime + duration
           │       └─> Returns: now >= startTime && now < endTime
           └─> If schedule.type === 'daily':
               └─> Calls isDailyActive()
                   └─> Gets current day (0-6) and time (minutes)
                   └─> Checks if current day in daysOfWeek array
                   └─> Parses startTime and endTime to minutes
                   └─> Handles midnight-spanning schedules
                   └─> Returns: currentTime in range

5. RULE APPLICATION (background.ts)
   └─> applyBlockingRules(activeRules)
       └─> Cleans up legacy URL-based rules
       └─> Logs active rule count
       └─> (Actual blocking happens in content scripts)

6. CONTENT SCRIPT USES ACTIVE RULES
   └─> When content script checks rules (Flow 2)
       └─> Only sees rules that are currently active
       └─> Rules automatically activate/deactivate based on schedule
```

**Visual Flow:**
```
Alarm (every 1 min) → Background → Get All Rules → Filter by Schedule
    → Check Duration: Is current time in range?
    → Check Daily: Is today in days? Is current time in range?
    → Return Active Rules → Apply Blocking Rules
    → Content Scripts Use Active Rules for Blocking
```

---

## 🔌 Component Interactions

### 1. Popup ↔ Background Communication

**Communication Method:** `chrome.runtime.sendMessage()`

```typescript
// Popup sends message
chrome.runtime.sendMessage(
  { type: 'GENERATE_RULES', description: '...' },
  (response) => {
    // Handle response
  }
);

// Background receives message
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // Handle message
  sendResponse({ success: true, data: ... });
  return true; // Indicates async response
});
```

**Message Types:**
- `GENERATE_RULES` - Generate AI rules
- `GET_RULES` - Get all saved rules
- `GET_ACTIVE_RULES` - Get currently active rules
- `SAVE_RULE` - Save a new rule
- `TOGGLE_RULE` - Enable/disable a rule
- `DELETE_RULE` - Delete a rule

---

### 2. Content Script ↔ Background Communication

**Communication Method:** `chrome.runtime.sendMessage()`

```typescript
// Content script sends message
const response = await chrome.runtime.sendMessage({
  type: 'CHECK_METADATA',
  user_description: '...',
  metadata: {...},
  url: '...'
});

// Background handles and forwards to backend
```

**Why Content Scripts Can't Call Backend Directly:**
- Content scripts run in page context
- CORS restrictions prevent direct API calls
- Background script acts as proxy

---

### 3. Background ↔ Backend Communication

**Communication Method:** HTTP Fetch API

```typescript
// Background makes HTTP request
const response = await fetch('http://localhost:8000/generate-block-rules', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ description: '...' })
});
```

**Endpoints:**
- `POST /generate-block-rules` - Generate blocking rules
- `POST /check-metadata` - Check if metadata matches rule

---

### 4. Backend ↔ AI Services

**Communication Method:** API SDKs

```python
# Anthropic Claude
client = Anthropic(api_key=api_key)
response = client.messages.create(
    model="claude-3-haiku-20240307",
    messages=[{"role": "user", "content": prompt}]
)

# OpenAI Embeddings
client = OpenAI(api_key=api_key)
response = client.embeddings.create(
    model="text-embedding-3-small",
    input=text
)
```

---

## 📊 Data Structures & State Management

### 1. Rule Storage (Chrome Storage)

```typescript
// Stored in chrome.storage.local
{
  rules: [
    {
      id: "1234567890",
      userDescription: "gaming videos",
      aiSummary: "Will block gaming videos...",
      patterns: [], // Legacy, not used
      schedule: {
        type: "duration",
        durationMinutes: 120,
        startTime: 1234567890000
      },
      enabled: true,
      createdAt: 1234567890000
    }
  ]
}
```

**Access Pattern:**
- Read: `chrome.storage.local.get(['rules'])`
- Write: `chrome.storage.local.set({ rules: [...] })`
- Persists across browser restarts

---

### 2. Metadata Cache (In-Memory)

```typescript
// Stored in content script memory
const metadataCache = new Map<string, {
  metadata: YouTubeVideoMetadata,
  timestamp: number
}>();

// Key: "domain-url"
// Value: { metadata, timestamp }
// TTL: 5 minutes
```

**Why Cache:**
- Avoids re-extracting metadata on every check
- Reduces DOM queries
- Improves performance

---

### 3. Component State (React)

```typescript
// PopupApp.tsx state
const [description, setDescription] = useState('');
const [schedule, setSchedule] = useState<Schedule | null>(null);
const [generatedRules, setGeneratedRules] = useState<GenerateRulesResponse | null>(null);
const [savedRules, setSavedRules] = useState<BlockRule[]>([]);
const [isGenerating, setIsGenerating] = useState(false);
```

**State Flow:**
- User input → state update → UI re-render
- API response → state update → UI update
- Save action → state update + storage update

---

## 🎯 Key Design Patterns

### 1. **Message Passing Pattern**
- Used for: Popup ↔ Background, Content Script ↔ Background
- Why: Chrome extension architecture requirement
- Implementation: `chrome.runtime.sendMessage()`

### 2. **Hybrid Matching Pattern**
- Used for: Metadata matching optimization
- Why: Embeddings are fast but less accurate, LLM is slow but accurate
- Implementation: Use embeddings first, LLM only when needed

### 3. **Metadata Source Resolution Pattern**
- Used for: YouTube metadata retrieval
- Why: Prefer reliable oEmbed metadata and fallback when unavailable
- Implementation: oEmbed-first resolution with backend page-metadata fallback

### 4. **Schedule Evaluation Pattern**
- Used for: Rule activation/deactivation
- Why: Rules should only be active during specified times
- Implementation: Periodic alarm + schedule checking functions

### 5. **Error Handling Pattern**
- Used for: All async operations
- Why: Graceful degradation
- Implementation: Try-catch with logging and user feedback

---

## 🔐 Security & Privacy

### 1. **API Keys**
- Stored in: Backend `.env` file (never in extension)
- Access: Backend only (extension never sees keys)
- Why: Prevents key exposure in client-side code

### 2. **CORS**
- Backend allows: All origins (dev only)
- Production: Should restrict to extension origin
- Why: Prevents unauthorized API access

### 3. **Storage**
- Location: Chrome storage (local to user's browser)
- Access: Extension only
- Why: User data stays on device

---

## 🚀 Performance Optimizations

### 1. **Embedding Pre-filter**
- Checks similarity first (fast)
- Only uses LLM when similarity is ambiguous
- Reduces LLM API calls by ~70%

### 2. **Metadata Caching**
- Caches extracted metadata for 5 minutes
- Avoids redundant DOM queries
- Reduces page load impact

### 3. **Async Operations**
- All API calls are async
- Non-blocking UI updates
- Parallel rule checking

### 4. **Schedule Evaluation**
- Runs every 1 minute (not on every page load)
- Cached active rules
- Efficient filtering algorithm

---

## 🐛 Error Handling Flow

```
1. User Action
   └─> Try operation
       ├─> Success → Update UI
       └─> Error → Catch
           ├─> Log error (console.error)
           ├─> Show user-friendly message (alert)
           └─> Graceful degradation (continue with other rules)
```

**Error Types:**
- **Network Errors**: Backend unreachable → Show error, don't block
- **API Errors**: Invalid response → Log, show error
- **Validation Errors**: Invalid input → Show validation message
- **Storage Errors**: Can't save → Show error, keep in memory

---

## 📈 Scalability Considerations

### Current Limitations:
1. **Single Backend**: One FastAPI server
2. **No Rate Limiting**: Could be overwhelmed
3. **No Database**: Rules stored in browser only
4. **No User Accounts**: Rules are device-specific

### Future Improvements:
1. **Multiple Backends**: Load balancing
2. **Rate Limiting**: Protect API
3. **Database**: Centralized rule storage
4. **User Accounts**: Sync rules across devices
5. **Caching Layer**: Redis for embeddings
6. **Queue System**: For high-volume matching

---

## 🔄 Complete System Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                         USER                                  │
└───────────────┬──────────────────────────────────────────────┘
                │
                │ 1. Opens Extension Popup
                ▼
┌──────────────────────────────────────────────────────────────┐
│                    POPUP UI (React)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Description  │  │  Schedule    │  │   Generate   │      │
│  │   Input       │  │   Form       │  │   Button     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                  │              │
│         └─────────────────┼──────────────────┘              │
│                           │                                │
│                           │ 2. chrome.runtime.sendMessage  │
└──────────────────────────┼──────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│              BACKGROUND SERVICE WORKER                      │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Message Handler                                    │    │
│  │  - Receives messages from popup/content             │    │
│  │  - Routes to appropriate handler                   │    │
│  └──────────────┬────────────────────────────────────┘    │
│                 │                                          │
│  ┌──────────────▼────────────────────────────────────┐    │
│  │  Storage Manager                                    │    │
│  │  - getRules() / saveRules()                         │    │
│  │  - chrome.storage.local                            │    │
│  └──────────────┬────────────────────────────────────┘    │
│                 │                                          │
│  ┌──────────────▼────────────────────────────────────┐    │
│  │  Schedule Evaluator                                 │    │
│  │  - filterActiveRules()                              │    │
│  │  - isDurationActive() / isDailyActive()             │    │
│  └──────────────┬────────────────────────────────────┘    │
│                 │                                          │
│  ┌──────────────▼────────────────────────────────────┐    │
│  │  API Client                                         │    │
│  │  - generateRules() → Backend                        │    │
│  │  - checkMetadata() → Backend                        │    │
│  └──────────────┬────────────────────────────────────┘    │
└─────────────────┼──────────────────────────────────────────┘
                  │
                  │ 3. HTTP POST
                  ▼
┌──────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                            │
│  ┌────────────────────────────────────────────────────┐    │
│  │  /generate-block-rules                              │    │
│  │  /check-metadata                                    │    │
│  └──────────────┬────────────────────────────────────┘    │
│                 │                                          │
│  ┌──────────────▼────────────────────────────────────┐    │
│  │  LLM Module                                        │    │
│  │  - generation.py → Anthropic                      │    │
│  │  - matching.py → Anthropic + OpenAI                │    │
│  │  - embeddings.py → OpenAI                         │    │
│  └──────────────┬────────────────────────────────────┘    │
└─────────────────┼──────────────────────────────────────────┘
                  │
                  │ 4. API Calls
                  ▼
        ┌─────────┴─────────┐
        │                    │
   ┌────▼────┐         ┌─────▼─────┐
   │Anthropic│         │  OpenAI   │
   │ Claude  │         │Embeddings │
   └─────────┘         └───────────┘
                  │
                  │ 5. Response
                  ▼
        (Backwards through same path)
                  │
                  │ 6. User sees result
                  ▼
┌──────────────────────────────────────────────────────────────┐
│                    YOUTUBE PAGE                               │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Content Script (metadata-checker.ts)              │    │
│  │  - Detects YouTube video                           │    │
│  │  - Extracts metadata                               │    │
│  │  - Checks against active rules                     │    │
│  │  - Blocks if match                                 │    │
│  └────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

---

## 🎓 Key Takeaways

1. **Separation of Concerns**: Each component has a single responsibility
2. **Message Passing**: Extension components communicate via messages
3. **Async Everywhere**: All I/O operations are async for performance
4. **Hybrid Approach**: Fast embeddings + accurate LLM for optimal performance
5. **Caching**: Multiple layers of caching for performance
6. **Error Resilience**: Graceful error handling at every level
7. **State Management**: React state for UI, Chrome storage for persistence
8. **Schedule-Based**: Rules activate/deactivate automatically based on time

This architecture ensures the system is maintainable, performant, and scalable!

