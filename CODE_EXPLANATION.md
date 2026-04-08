# Complete Code Explanation - MoreTime Extension & Backend

This document explains how every file works and what each line of code does.

---

## BACKEND FILES

### `backend/main.py` - FastAPI Server Entry Point

**Purpose**: Main FastAPI application that handles HTTP requests from the extension.

**Line-by-line explanation**:

```python
1-4: Module docstring explaining this is the FastAPI backend server
6: Import logging for application logging
7: Import FastAPI framework and HTTPException for error handling
8: Import CORSMiddleware to allow cross-origin requests from the extension
9: Import load_dotenv to load environment variables from .env file
11-16: Import request/response models (Pydantic schemas) for API validation
17: Import LLM functions from the llm module
18-23: Import constants for configuration
25-26: Load environment variables from .env file into os.environ
28-32: Configure Python logging - set level to INFO and format log messages with timestamp, name, level, and message
33: Create a logger instance for this module
35: Create FastAPI app instance with title and version
37-44: Add CORS middleware to allow requests from Chrome extension (allows all origins in dev, should restrict in production)
47-76: POST endpoint `/generate-block-rules`
  - Line 47: Decorator that creates POST route with response model validation
  - Line 48: Async function that takes GenerateRulesRequest and returns GenerateRulesResponse
  - Line 61: Create preview of description (first 100 chars) for logging
  - Line 62: Log the incoming request
  - Line 64-65: Validate that description is not empty, raise 400 error if empty
  - Line 67-70: Try to generate rules using LLM, log success, return result
  - Line 71-73: Catch ValueError (validation errors) and return 400 status
  - Line 74-76: Catch any other exceptions and return 500 status with error message
79-112: POST endpoint `/check-metadata`
  - Line 79: Decorator for POST route with response model
  - Line 80: Async function to check if metadata matches a rule
  - Line 93-94: Log the incoming request details
  - Line 97-101: Call optimized matching function with user description, metadata, and URL
  - Line 102-105: Log the result (matches and confidence score)
  - Line 107-109: Handle validation errors (400 status)
  - Line 110-112: Handle other errors (500 status)
115-126: GET endpoint `/` (root)
  - Line 115: Decorator for GET route
  - Line 116: Async function returning API information
  - Line 118-125: Return JSON with API message, version, and available endpoints
129-132: GET endpoint `/health`
  - Line 129: Decorator for health check endpoint
  - Line 130: Async function for health checks
  - Line 132: Return simple {"status": "ok"} response
135-137: Main entry point
  - Line 135: Only run if script is executed directly (not imported)
  - Line 136: Import uvicorn ASGI server
  - Line 137: Run the FastAPI app on default host and port
```

---

### `backend/config.py` - Environment Variable Configuration

**Purpose**: Manages API keys and environment variables safely.

**Line-by-line explanation**:

```python
1-3: Module docstring
5: Import os module to access environment variables
6: Import Optional type hint from typing
9-16: Function get_anthropic_api_key()
  - Line 9: Function that returns Optional[str] (string or None)
  - Line 16: Get ANTHROPIC_API_KEY from environment, returns None if not set
19-26: Function get_openai_api_key()
  - Line 19: Function that returns Optional[str]
  - Line 26: Get OPENAI_API_KEY from environment, returns None if not set
29-43: Function require_anthropic_api_key()
  - Line 29: Function that returns str (guaranteed, not Optional)
  - Line 39: Get the API key using the getter function
  - Line 40-42: If key is None, import error constant and raise ValueError
  - Line 43: Return the key if it exists
46-60: Function require_openai_api_key()
  - Same pattern as require_anthropic_api_key but for OpenAI
```

---

### `backend/constants.py` - Application Constants

**Purpose**: Centralizes all magic numbers, strings, and configuration values.

**Line-by-line explanation**:

```python
1-3: Module docstring
5-8: API Configuration
  - Line 6: CORS allowed origins (["*"] allows all, should restrict in production)
  - Line 7: Default host to bind server to (0.0.0.0 means all interfaces)
  - Line 8: Default port number (8000)
10-14: LLM Configuration
  - Line 11: Anthropic Claude model name
  - Line 12: OpenAI embedding model name
  - Line 13: Max tokens for generation endpoint (2000)
  - Line 14: Max tokens for matching endpoint (500)
16-19: Similarity Thresholds
  - Line 17: High similarity threshold (0.80) - if similarity >= this, block immediately
  - Line 18: Low similarity threshold (0.50) - if similarity < this, don't block
  - Line 19: Confidence threshold for blocking (0.5)
21-27: Error Messages
  - Centralized error message strings to avoid duplication and enable easy updates
```

---

### `backend/schemas.py` - Pydantic Data Models

**Purpose**: Defines request/response models with validation.

**Line-by-line explanation**:

```python
1-3: Module docstring
5: Import BaseModel (base class for Pydantic models) and Field (for field validation)
6: Import List type hint (not used but kept for consistency)
9-11: GenerateRulesRequest class
  - Line 9: Class inheriting from BaseModel
  - Line 11: description field - required (Field(...)), minimum length 1, with description
14-16: GenerateRulesResponse class
  - Line 14: Response model class
  - Line 16: summary field - required string with description
19-23: CheckMetadataRequest class
  - Line 19: Request model for metadata checking
  - Line 21: user_description - required string
  - Line 22: metadata - required dict (website metadata)
  - Line 23: url - required string (website URL)
26-30: CheckMetadataResponse class
  - Line 26: Response model for metadata check
  - Line 28: matches - required boolean (whether it matches)
  - Line 29: confidence - required float between 0.0 and 1.0 (ge=0.0, le=1.0)
  - Line 30: reasoning - required string (explanation)
```

---

### `backend/llm/__init__.py` - LLM Module Exports

**Purpose**: Makes the LLM module functions available for import.

**Line-by-line explanation**:

```python
1-3: Module docstring
5: Import generate_block_rules from generation module
6: Import check_metadata_matches_rule_optimized from matching module
8: Define __all__ to control what gets exported when using "from llm import *"
```

---

### `backend/llm/embeddings.py` - Embedding Utilities

**Purpose**: Handles text embeddings for semantic similarity calculations.

**Line-by-line explanation**:

```python
1-3: Module docstring
5: Import asyncio for async operations
6: Import logging
7: Import List type hint
9: Import numpy for vector operations
10: Import OpenAI client
12: Import require_openai_api_key (raises error if key missing)
13: Import embedding model constant
15: Create logger for this module
18-43: Function get_embedding()
  - Line 18: Async function that takes text and returns List[float] (embedding vector)
  - Line 31: Get API key (will raise error if not set)
  - Line 33: Create OpenAI client with API key
  - Line 34-39: Try to create embedding in thread pool (to avoid blocking)
    - Line 35: Run client.embeddings.create in thread pool
    - Line 36: Use model from constants
    - Line 37: Input is the text to embed
  - Line 40: Return the embedding vector (first item in data array)
  - Line 41-43: Catch exceptions, log error, raise ValueError with error message
46-59: Function cosine_similarity()
  - Line 46: Function that takes two vectors and returns float (similarity score)
  - Line 57: Convert lists to numpy arrays for vector operations
  - Line 58: Convert second list to numpy array
  - Line 59: Calculate cosine similarity: dot product divided by product of norms
    - np.dot: dot product of vectors
    - np.linalg.norm: magnitude/length of vector
    - Result is between -1 and 1, but typically 0-1 for normalized embeddings
```

---

### `backend/llm/generation.py` - Rule Generation

**Purpose**: Generates blocking rules using Anthropic Claude API.

**Line-by-line explanation**:

```python
1-3: Module docstring
5: Import asyncio for async operations
6: Import logging
7: Import Callable type hint
9: Import Anthropic client
10: Import TextBlock type for response parsing
12: Import response model
13: Import API key getter
14-18: Import constants
19: Import JSON extraction utility
21: Create logger
24-49: Function _build_generation_prompt()
  - Line 24: Private function (starts with _) to build prompt string
  - Line 34-49: Multi-line f-string that creates the prompt
    - Explains the task to Claude
    - Includes user's description
    - Explains metadata matching expectations
    - Asks for summary with examples
    - Specifies JSON response format
52-62: Function _create_anthropic_client()
  - Line 52: Private function to create Anthropic client
  - Line 62: Return new Anthropic client instance with API key
65-83: Function _call_anthropic_api()
  - Line 65: Returns a Callable function
  - Line 76-82: Inner function that makes the API call
    - Line 77: Create client
    - Line 78-81: Call messages.create with model, max tokens, and messages
  - Line 83: Return the callable function
86-130: Function generate_block_rules()
  - Line 86: Main async function to generate rules
  - Line 99: Get API key (raises error if missing)
  - Line 100: Build the prompt
  - Line 102-130: Try-except block
    - Line 103: Create description preview for logging
    - Line 104: Log the generation request
    - Line 106: Create the API call function
    - Line 107: Execute API call in thread pool (non-blocking)
    - Line 110: Extract text from response
    - Line 112: Log raw response
    - Line 115: Parse JSON from response
    - Line 118: Get summary and strip whitespace
    - Line 120-121: Validate summary is not empty
    - Line 123: Log final summary
    - Line 124: Return GenerateRulesResponse with summary
    - Line 126-127: Re-raise ValueError (validation errors)
    - Line 128-130: Catch other exceptions, log, raise with error message
133-148: Function _extract_text_from_response()
  - Line 133: Private function to extract text from Anthropic response
  - Line 143: Initialize empty content string
  - Line 144: Check if message has content
  - Line 145-147: Loop through content blocks, if TextBlock, append text
  - Line 148: Return concatenated text
```

---

### `backend/llm/matching.py` - Metadata Matching

**Purpose**: Checks if website metadata matches blocking rules using hybrid approach (embeddings + LLM).

**Line-by-line explanation**:

```python
1-3: Module docstring
5-8: Imports (json, asyncio, logging, typing)
10-11: Anthropic imports
13: Response model import
14: API key getter
15-21: Constants imports
22-23: Utility imports
25: Logger creation
28-38: Function _create_anthropic_client()
  - Creates Anthropic client instance
41-56: Function _extract_text_from_response()
  - Extracts text from Anthropic API response blocks
59-79: Function _format_metadata_string()
  - Line 59: Formats metadata dict into readable string
  - Line 70-78: Creates formatted string with URL, video ID, and OGP properties
82-120: Function _build_matching_prompt()
  - Line 82: Builds prompt for LLM to check if video matches rule
  - Line 93-120: Multi-line prompt explaining:
    - User's blocking rule
    - Video metadata
    - What to consider
    - JSON response format
    - Important instructions (be strict, confidence requirements)
123-186: Function check_metadata_matches_rule()
  - Line 123: Main function using LLM to check match
  - Line 142: Get API key
  - Line 143: Format metadata string
  - Line 144: Build prompt
  - Line 146-152: Inner function to call Anthropic API
  - Line 154-180: Try-except block
    - Line 155-157: Log request details
    - Line 159: Call API in thread pool
    - Line 160: Extract text from response
    - Line 162: Log raw response
    - Line 165: Parse JSON
    - Line 167-169: Extract matches, confidence, reasoning with defaults
    - Line 171-174: Log result
    - Line 176-180: Return CheckMetadataResponse
    - Line 182-186: Error handling
189-204: Function _format_metadata_for_embedding()
  - Line 189: Formats metadata for embedding (simpler format)
  - Line 199: Start with video title
  - Line 200-201: Add description if exists
  - Line 202-203: Add site name if exists
207-270: Function check_metadata_matches_rule_optimized()
  - Line 207: Hybrid approach: embeddings first, LLM if needed
  - Line 223-224: Log checking start
  - Line 226: Format metadata for embedding
  - Line 229-265: Try-except for embedding check
    - Line 230: Log computing embeddings
    - Line 231-232: Get embeddings for rule description and metadata
    - Line 233: Calculate cosine similarity
    - Line 235: Log similarity score
    - Line 238-247: High similarity (>=0.80) - block immediately without LLM
    - Line 250-258: Low similarity (<0.50) - don't block
    - Line 261-265: Medium similarity (0.50-0.80) - use LLM for accurate decision
  - Line 267-270: Fallback to LLM if embeddings fail
```

---

### `backend/llm/utils.py` - JSON Parsing Utilities

**Purpose**: Parses JSON from LLM responses, handling markdown code blocks.

**Line-by-line explanation**:

```python
1-3: Module docstring
5-7: Imports (json, re, logging)
9: Import error constant
11: Logger creation
14-44: Function _remove_markdown_code_blocks()
  - Line 14: Removes markdown code blocks from content
  - Line 24: If content doesn't start with ```, return as-is
  - Line 27: Split content into lines
  - Line 28-29: Initialize start/end indices
  - Line 31-37: Find first ``` (start) and second ``` (end)
  - Line 39-42: Extract content between code block markers
47-65: Function _extract_json_with_regex()
  - Line 47: Extracts JSON using regex as fallback
  - Line 60: Search for JSON object pattern {.*} with DOTALL flag
  - Line 61-64: If found, parse and return
  - Line 65: Raise error if not found
68-96: Function extract_json_from_response()
  - Line 68: Main function to extract JSON from LLM response
  - Line 81: Remove markdown code blocks and strip whitespace
  - Line 84-87: Try to parse JSON directly
  - Line 88: If JSONDecodeError, try regex extraction
  - Line 90-91: Try regex extraction
  - Line 92-96: If both fail, log error and raise ValueError
```

---

## EXTENSION FILES

### `extension/src/constants.ts` - Extension Constants

**Purpose**: Centralizes all constants used throughout the extension.

**Line-by-line explanation**:

```typescript
1-3: JSDoc comment
5-6: Backend URL constant (localhost:8000 for development)
8-9: Cache TTL constant (5 minutes in milliseconds)
11-12: Confidence threshold for blocking (0.5)
14-24: Message types object
  - All message types used for chrome.runtime.sendMessage
  - as const makes it readonly
26-29: Alarm names for chrome.alarms
31-34: Storage keys for chrome.storage.local
36-38: YouTube detection constants
40-41: Day names array (Sunday to Saturday)
43-44: Navigation check delay for SPAs (1 second)
```

---

### `extension/src/types.ts` - TypeScript Type Definitions

**Purpose**: Defines all TypeScript interfaces and types.

**Line-by-line explanation**:

```typescript
1-3: JSDoc comment
5: Type alias for schedule type ('duration' | 'daily')
7-11: DurationSchedule interface
  - Line 7: Interface for duration-based schedules
  - Line 8: Discriminator field (type: 'duration')
  - Line 9: Duration in minutes
  - Line 10: Start time as Unix timestamp
13-18: DailySchedule interface
  - Line 13: Interface for daily recurring schedules
  - Line 14: Discriminator field
  - Line 15: Array of day numbers (0=Sunday, 6=Saturday)
  - Line 16-17: Start and end times in "HH:MM" format
20: Union type for Schedule (either DurationSchedule or DailySchedule)
22-33: BlockRule interface
  - Line 22: Main rule interface
  - Line 23: Unique identifier (string)
  - Line 24: User's description of what to block
  - Line 25: AI-generated summary
  - Line 26-29: Patterns array (currently empty, legacy)
  - Line 30: Schedule object
  - Line 31: Whether rule is enabled
  - Line 32: Creation timestamp
35-37: GenerateRulesRequest interface (matches backend schema)
39-41: GenerateRulesResponse interface (matches backend schema)
```

---

### `extension/src/background/api.ts` - Backend API Client

**Purpose**: Handles HTTP requests to the backend server.

**Line-by-line explanation**:

```typescript
1-3: JSDoc comment
5: Import response type
6: Import backend URL constant
8-12: CheckMetadataResult interface
  - Matches backend CheckMetadataResponse
14-43: Function generateRules()
  - Line 14: JSDoc with parameter and return types
  - Line 21: Async function that returns Promise<GenerateRulesResponse>
  - Line 22-29: Try block
    - Line 23: Fetch POST request to /generate-block-rules
    - Line 24: Method is POST
    - Line 25-27: Set Content-Type header
    - Line 28: Stringify request body with description
    - Line 31-34: If response not ok, get error text and throw Error
    - Line 36: Parse and return JSON response
  - Line 37-42: Catch block - handle errors and re-throw with proper type
45-91: Function checkMetadata()
  - Line 45: JSDoc
  - Line 55: Async function with typed parameters
  - Line 60-61: Log the check request
  - Line 63-74: Try block
    - Line 64: Fetch POST to /check-metadata
    - Line 69-73: Stringify request with user_description, metadata, url
    - Line 76-79: Handle non-ok responses
    - Line 82-84: Parse and return result
  - Line 85-90: Error handling
```

---

### `extension/src/background/background.ts` - Service Worker

**Purpose**: Main background script that handles messaging, storage, and rule management.

**Line-by-line explanation**:

```typescript
1-5: JSDoc comment
7: Import BlockRule type
8: Import constants
9-12: Import utility functions
15-21: Function getActiveRules()
  - Line 15: JSDoc
  - Line 18: Get all rules from storage
  - Line 20: Filter to only active rules (based on schedule)
23-50: Function applyBlockingRules()
  - Line 23: JSDoc
  - Line 27: Try block
    - Line 30: Get existing declarativeNetRequest rules (legacy URL-based)
    - Line 31: Extract rule IDs
    - Line 34-37: Remove all legacy rules (we use metadata analysis now)
    - Line 42-45: Log active rule count
  - Line 47-49: Error handling
52-59: Function evaluateAndUpdateRules()
  - Line 52: JSDoc
  - Line 57: Get active rules
  - Line 58: Apply blocking rules
61-144: Function handleMessage()
  - Line 61: JSDoc
  - Line 64: Async function with message and sender parameters
  - Line 68: Switch on message.type
    - Line 69-72: GENERATE_RULES - call generateRules and return result
    - Line 74-77: GET_RULES - get all rules from storage
    - Line 79-82: GET_ACTIVE_RULES - get filtered active rules
    - Line 84-89: SAVE_RULE - add rule to storage and update
    - Line 92-101: TOGGLE_RULE - find rule, update enabled, save
    - Line 104-109: DELETE_RULE - filter out rule, save
    - Line 112-118: CHECK_METADATA - call checkMetadata and return result
    - Line 121-138: REDIRECT_TO_BLOCKED - redirect tab to blocked page
    - Line 141-142: Default - unknown message type
146-163: Message listener
  - Line 149: chrome.runtime.onMessage.addListener
  - Line 150-159: Async IIFE to handle message
    - Line 152: Call handleMessage
    - Line 153: Send response
    - Line 154-158: Error handling
  - Line 162: Return true (indicates async response)
165-175: Alarm setup
  - Line 169: Create periodic alarm (every 1 minute)
  - Line 171-174: Alarm listener - evaluate rules when alarm fires
177-186: Startup/install listeners
  - Line 180-181: Evaluate rules on browser startup
  - Line 184-185: Evaluate rules on extension install
189: Initial evaluation on script load
```

---

### `extension/src/background/storage.ts` - Storage Utilities

**Purpose**: Manages Chrome storage for rules.

**Line-by-line explanation**:

```typescript
1-3: JSDoc comment
5: Import BlockRule type
6: Import storage key constant
8-16: Function getRules()
  - Line 8: JSDoc
  - Line 13: Async function returning Promise<BlockRule[]>
  - Line 14: Get 'rules' from chrome.storage.local
  - Line 15: Return rules array or empty array if undefined
18-25: Function saveRules()
  - Line 18: JSDoc
  - Line 23: Async function that saves rules
  - Line 24: Set 'rules' in chrome.storage.local
```

---

### `extension/src/background/utils.ts` - Schedule Utilities

**Purpose**: Functions for evaluating schedule activity.

**Line-by-line explanation**:

```typescript
1-3: JSDoc comment
5: Import types
7-17: Function isDurationActive()
  - Line 7: JSDoc
  - Line 13: Function checking if duration schedule is active
  - Line 14: Get current timestamp
  - Line 15: Calculate end time (start + duration in milliseconds)
  - Line 16: Return true if now is between start and end
19-28: Function parseTimeToMinutes()
  - Line 19: JSDoc
  - Line 25: Private function to parse "HH:MM" to minutes
  - Line 26: Split by ':', convert to numbers
  - Line 27: Return hours * 60 + minutes
30-56: Function isDailyActive()
  - Line 30: JSDoc
  - Line 36: Function checking if daily schedule is active
  - Line 37: Get current date
  - Line 38: Get current day of week (0=Sunday, 6=Saturday)
  - Line 39: Get current time in minutes since midnight
  - Line 42-44: Check if today is in schedule's daysOfWeek
  - Line 47-48: Parse start and end times to minutes
  - Line 51-52: Handle schedules spanning midnight (end < start)
  - Line 55: Normal case - check if current time is in range
58-76: Function filterActiveRules()
  - Line 58: JSDoc
  - Line 64: Function filtering rules to only active ones
  - Line 65: Filter rules array
  - Line 66-68: Return false if rule not enabled
  - Line 70-71: Check duration schedule if type is 'duration'
  - Line 74: Otherwise check daily schedule
```

---

### `extension/src/background/redirect.ts` - Redirect Utilities

**Purpose**: Handles redirecting tabs to blocked page.

**Line-by-line explanation**:

```typescript
1-3: JSDoc comment
5: Import buildBlockedUrl utility
7-12: RedirectParams interface
  - Parameters for blocked page URL
14-27: Function redirectToBlocked()
  - Line 14: JSDoc
  - Line 20: Async function
  - Line 24: Build blocked URL with params
  - Line 25: Log redirect action
  - Line 26: Update tab URL to blocked page
```

---

### `extension/src/utils/url-builder.ts` - URL Builder

**Purpose**: Builds blocked page URLs with query parameters.

**Line-by-line explanation**:

```typescript
1-3: JSDoc comment
5-23: Function buildBlockedUrl()
  - Line 5: JSDoc
  - Line 8: Function with params object
  - Line 14: Get extension URL for blocked.html
  - Line 15-20: Create URLSearchParams with rule, scheduleType, timeRemaining, description
  - Line 22: Return URL with query string
```

---

### `extension/src/content/metadata-extractor.ts` - Metadata Extraction

**Purpose**: Extracts normalized metadata from YouTube pages.

**Line-by-line explanation**:

```typescript
1-5: JSDoc comment
7-17: YouTubeVideoMetadata interface
  - Defines structure of extracted metadata
  - title, content_type, description, site_name (normalized fields)
  - url, video_id (additional metadata)
19-25: Function getMetaPropertyContent()
  - Line 19: JSDoc
  - Line 22: Function to get a metadata property content value
  - Line 23: Query selector for meta[property="..."]
  - Line 24: Return content attribute or null
27-33: Function extractVideoId()
  - Line 27: JSDoc
  - Line 30: Function to extract video ID from URL
  - Line 31: Regex match for youtube.com/watch?v= or youtu.be/
  - Line 32: Return matched video ID or null
35-61: Function extractPageMetadata()
  - Line 35: JSDoc
  - Line 39: Main function to extract all metadata
  - Line 41: Get title from metadata property fallback to document.title
  - Line 42-44: Get other metadata properties
  - Line 45: Get current URL
  - Line 46: Extract video ID
  - Line 48-60: Return metadata object
```

---

### `extension/src/content/metadata-checker.ts` - Content Script

**Purpose**: Checks YouTube videos against blocking rules and blocks if match.

**Line-by-line explanation**:

```typescript
1-5: JSDoc comment
7-17: Imports (extractor, types, utilities, constants)
19-20: Metadata cache Map (key: domain-url, value: {metadata, timestamp})
22-30: Function isYouTubeVideoPage()
  - Checks if current page is YouTube video page
  - Compares hostname and pathname
32-45: Function isExtensionOrSystemPage()
  - Checks if URL is extension or system page (should be ignored)
47-66: Function getMetadata()
  - Gets metadata from cache or extracts it
  - Checks cache TTL before using cached data
68-76: Function getScheduleTypeDisplay()
  - Converts schedule type to display string
78-114: Function handleBlocking()
  - Line 78: JSDoc
  - Line 84: Async function to handle blocking
  - Line 85: Log blocking action
  - Line 88: Stop page loading
  - Line 90-91: Get schedule type and description
  - Line 94-101: Try to redirect via background script
  - Line 103-112: Fallback to direct redirect if background fails
116-166: Function checkRuleMatch()
  - Line 116: JSDoc
  - Line 124: Async function to check if video matches rule
  - Line 129: Log checking action
  - Line 132-137: Send message to background to check metadata
  - Line 139-142: Handle error response
  - Line 144-149: Log result
  - Line 152-154: Block if matches and confidence >= threshold
  - Line 157-160: Log non-match
  - Line 162-164: Error handling
168-218: Function checkPageAgainstRules()
  - Line 168: JSDoc
  - Line 171: Main async function
  - Line 174-176: Early return if not YouTube video page
  - Line 179-181: Early return if extension/system page
  - Line 183: Log checking start
  - Line 186-188: Get active rules from background
  - Line 190-193: Early return if no active rules
  - Line 195-200: Get rules, URL, domain, log details
  - Line 203-204: Get metadata (cached or extracted)
  - Line 207-212: Check each rule, stop if blocked
  - Line 214: Log completion
  - Line 215-217: Error handling
220-225: Initial check on page load
  - Line 221: If document still loading, wait for DOMContentLoaded
  - Line 223: Otherwise run immediately
227-235: SPA navigation detection
  - Line 228: Track last URL
  - Line 229: MutationObserver watches for DOM changes
  - Line 230-234: If URL changed, wait 1 second then check again
```

---

### `extension/src/popup/PopupApp.tsx` - Main Popup Component

**Purpose**: Main React component for the extension popup UI.

**Line-by-line explanation**:

```typescript
1: Import React hooks (useState, useEffect)
2-5: Import child components
6: Import types
7: Import constants
8: Import styles
10: PopupApp functional component
11-15: State declarations
  - Line 11: description - user input text
  - Line 12: schedule - selected schedule or null
  - Line 13: generatedRules - AI response or null
  - Line 14: savedRules - array of saved rules
  - Line 15: isGenerating - loading state
17-24: useEffect hook
  - Line 18: Run on component mount
  - Line 19: Send GET_RULES message
  - Line 20-22: Update savedRules state with response
26-50: handleGenerate function
  - Line 26: Async function
  - Line 27-30: Validate description and schedule
  - Line 32: Set loading state
  - Line 33-37: Send GENERATE_RULES message
  - Line 39-40: If success, update generatedRules state
  - Line 42: Otherwise show error alert
  - Line 44-46: Catch and show error
  - Line 48: Reset loading state
52-80: handleSaveRule function
  - Line 52: Function to save generated rule
  - Line 53-55: Validate generatedRules and schedule
  - Line 57-65: Create new BlockRule object
  - Line 67-79: Send SAVE_RULE message
  - Line 70-74: If success, update state and clear form
  - Line 76: Otherwise show error
82-93: handleToggleRule function
  - Line 82: Function to toggle rule enabled state
  - Line 83-85: Send TOGGLE_RULE message
  - Line 86-89: If success, update savedRules state
95-104: handleDeleteRule function
  - Line 95: Function to delete rule
  - Line 96-98: Send DELETE_RULE message
  - Line 99-101: If success, filter out deleted rule
106-140: Return JSX
  - Line 107: Container div with styles
  - Line 108: Heading
  - Line 110: DescriptionInput component
  - Line 112: ScheduleForm component
  - Line 114-123: Generate button (disabled when loading or invalid)
  - Line 125-131: GeneratedRulesView (conditional render)
  - Line 133-137: SavedRulesList component
```

---

### `extension/src/popup/DescriptionInput.tsx` - Description Input Component

**Purpose**: Textarea component for user to describe videos to block.

**Line-by-line explanation**:

```typescript
1: Import React
2: Import styles
4-7: DescriptionInputProps interface
  - value: current text
  - onChange: callback function
9: DescriptionInput component
10-23: Return JSX
  - Line 11: Container div
  - Line 12-14: Label with styles
  - Line 15-21: Textarea
    - Line 16: id for label association
    - Line 17: Controlled input (value prop)
    - Line 18: onChange handler calls onChange prop
    - Line 19: Placeholder text
    - Line 20: Apply textarea styles
```

---

### `extension/src/popup/ScheduleForm.tsx` - Schedule Form Component

**Purpose**: Form component for selecting schedule type and configuration.

**Line-by-line explanation**:

```typescript
1: Import React hooks
2: Import types
3: Import constants
4: Import styles
6-9: ScheduleFormProps interface
11: DAYS_OF_WEEK constant (mapped from DAY_NAMES)
13-16: ScheduleForm component
  - Line 13: Component with props
  - Line 14: Destructure schedule (unused, prefixed with _)
17-22: State declarations
  - scheduleType: 'duration' | 'daily'
  - durationHours, durationMinutes: number inputs
  - selectedDays: array of selected day numbers
  - startTime, endTime: time strings
24-27: handleScheduleTypeChange
  - Updates scheduleType and clears schedule
29-39: createDurationSchedule
  - Creates DurationSchedule object if valid
41-51: createDailySchedule
  - Creates DailySchedule object if valid
53-58: toggleDay
  - Toggles day selection in selectedDays array
60-68: useEffect
  - Recreates schedule when inputs change
  - Calls onScheduleChange with new schedule
70-82: Style objects for inputs
84-179: Return JSX
  - Line 86: Container
  - Line 88-107: Radio buttons for schedule type
  - Line 109-129: Duration inputs (if duration selected)
  - Line 130-177: Daily schedule inputs (if daily selected)
    - Line 132-154: Day selection buttons
    - Line 156-175: Time inputs
```

---

### `extension/src/popup/GeneratedRulesView.tsx` - Generated Rules Display

**Purpose**: Displays AI-generated rules and allows saving.

**Line-by-line explanation**:

```typescript
1: Import React
2: Import types
3: Import constants
4: Import styles
6-10: GeneratedRulesViewProps interface
12-26: formatSchedule function
  - Line 12: JSDoc
  - Line 15: Function to format schedule for display
  - Line 16: Return 'No schedule' if null
  - Line 18-22: Format duration schedule (hours and minutes)
  - Line 24-25: Format daily schedule (days and times)
28-52: GeneratedRulesView component
  - Line 28: Component with props
  - Line 33-50: Return JSX
    - Line 34: Card container with styles
    - Line 35: Heading
    - Line 37-40: Summary section
    - Line 42-45: Schedule section
    - Line 47-49: Save button
```

---

### `extension/src/popup/SavedRulesList.tsx` - Saved Rules List Component

**Purpose**: Displays list of saved rules with toggle/delete actions.

**Line-by-line explanation**:

```typescript
1: Import React
2: Import types
3: Import constants
4: Import styles
6-10: SavedRulesListProps interface
12-30: formatSchedule function
  - Line 12: JSDoc
  - Line 15: Function to format schedule
  - Line 16-25: Format duration (check if expired)
  - Line 28-29: Format daily schedule
32-84: SavedRulesList component
  - Line 32: Component with props
  - Line 37-42: Empty state if no rules
  - Line 45-82: Rules list
    - Line 48: Map over rules array
    - Line 49-80: Rule card
      - Line 51: Key for React
      - Line 52-54: Apply styles based on enabled state
      - Line 56-64: Rule info (description, summary, schedule)
      - Line 65-78: Actions (toggle checkbox, delete button)
```

---

### `extension/src/popup/styles.ts` - Shared Styles

**Purpose**: Centralized style objects for popup components.

**Line-by-line explanation**:

```typescript
1-3: JSDoc comment
5-165: styles object
  - All style objects use 'as const' for type safety
  - container: Main container padding and font
  - heading, heading2, heading3: Heading styles
  - label: Form label styles
  - textarea: Textarea input styles
  - button, buttonDisabled, buttonSecondary, buttonDelete: Button variants
  - card, ruleCard, ruleCardActive, ruleCardInactive: Card styles
  - emptyState: Empty state message styles
  - text, textSmall, textTiny, textMuted: Text size/color variants
  - flexRow, flexColumn, flexBetween: Flexbox layouts
  - checkbox, checkboxLabel: Checkbox styles
```

---

### `extension/src/popup/index.tsx` - Popup Entry Point

**Purpose**: React app initialization and mounting.

**Line-by-line explanation**:

```typescript
1: Import React
2: Import createRoot from react-dom/client (React 18 API)
3: Import PopupApp component
5: Get root container element
6-12: If container exists
  - Line 7: Create React root
  - Line 8-11: Render PopupApp in StrictMode
    - StrictMode enables additional checks in development
```

---

## DATA FLOW SUMMARY

1. **User creates rule**:
   - PopupApp → DescriptionInput + ScheduleForm → handleGenerate → background.ts → api.ts → backend/main.py → llm/generation.py → Anthropic API

2. **User visits YouTube**:
   - metadata-checker.ts detects YouTube page → extracts metadata → sends to background → api.ts → backend → llm/matching.py → checks embeddings/LLM → returns match result → blocks if matches

3. **Rule evaluation**:
   - background.ts → utils.ts → checks schedules → filters active rules → applies blocking

This architecture separates concerns: backend handles AI/LLM, extension handles UI/storage/blocking, content scripts handle page detection.

