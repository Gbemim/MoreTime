# MoreTime - AI-Powered Website Blocker

A Chrome extension (Manifest V3) that uses AI to generate website blocking rules based on natural language descriptions. Includes a Python FastAPI backend that integrates with Anthropic's Claude API.

## Project Structure

```
MoreTime/
├── extension/          # Chrome extension (React + TypeScript)
│   ├── src/
│   │   ├── popup/      # React popup UI components
│   │   ├── background/ # Service worker for messaging & storage
│   │   └── types.ts    # TypeScript type definitions
│   ├── manifest.json   # Chrome extension manifest
│   ├── popup.html      # Popup entry point
│   └── package.json    # Node.js dependencies
│
└── backend/            # FastAPI Python server
    ├── main.py         # FastAPI app and routes
    ├── schemas.py      # Pydantic models
    ├── llm.py          # Anthropic/Claude integration
    ├── config.py       # Environment variable management
    └── requirements.txt
```

## Features (V1)

- **Natural Language Input**: Describe what websites you want to block
- **AI-Generated Rules**: Claude generates domain/pattern suggestions
- **Flexible Scheduling**:
  - Duration-based: Block for N minutes/hours starting now
  - Daily schedule: Choose days of week + start/end times
- **Rule Management**: Save, enable/disable, and delete blocking rules
- **Schedule Evaluation**: Automatic activation/deactivation based on time

## Setup

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in `backend/` (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```

5. Add your Anthropic API key to `backend/.env`:
   ```
   ANTHROPIC_API_KEY=your_api_key_here
   ```

6. Start the FastAPI server:
   ```bash
   python main.py
   # Or: uvicorn main:app --reload
   ```

   The server will run on `http://localhost:8000`. The API key is read only from `backend/.env`.


### Extension Setup

1. Navigate to the extension directory:
   ```bash
   cd extension
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Build the extension:
   ```bash
   npm run build
   ```

4. Load the extension in Chrome:
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode" (toggle in top right)
   - Click "Load unpacked"
   - Select the `extension/dist` directory

5. **Chrome Web Store:** Upload a package whose **root** is the contents of `extension/dist` (not the raw `extension/` source tree). After `npm run build`, confirm `extension/dist/content/metadata-checker.js` exists next to `manifest.json`. To build and zip in one step: `npm run pack:store` (requires the `zip` CLI; writes `extension/moretime-extension-store.zip`).

6. The extension uses `http://localhost:8000` by default. To use a different backend, edit `BACKEND_URL` in `extension/src/constants.ts` and rebuild.

## Usage

1. Click the extension icon to open the popup
2. Enter a description of websites you want to block (e.g., "Social media sites like Facebook and Twitter")
3. Choose a schedule:
   - **Duration**: Block for a specific time period starting now
   - **Daily**: Block on specific days of the week during certain hours
4. Click "Generate Block Rules"
5. Review the AI-generated summary and example domains
6. Click "Save Rule" to add it to your list
7. Toggle rules on/off or delete them as needed

## Architecture

### Frontend (Chrome Extension)

- **Popup UI**: React components for user interaction
- **Background Service Worker**: Handles messaging, storage, and schedule evaluation
- **Storage**: Uses `chrome.storage.local` to persist rules
- **Scheduling**: Uses `chrome.alarms` for periodic schedule evaluation

### Backend (FastAPI)

- **API Endpoint**: `POST /generate-block-rules`
- **LLM Integration**: Uses Anthropic Claude to generate structured blocking rules
- **Response Format**: JSON with summary and list of domain/URL patterns

## Implementation Notes

### Blocking Logic (Stub)

The actual blocking implementation using `chrome.declarativeNetRequest` is currently a stub in `src/background/background.ts`:

```typescript
async function applyBlockingRules(activeRules: BlockRule[]): Promise<void> {
  // TODO: Implement actual blocking using chrome.declarativeNetRequest
}
```

This will be implemented in a future update.

### Schedule Evaluation

- Duration schedules: Active from `startTime` until `startTime + durationMinutes`
- Daily schedules: Active on specified days of week between `startTime` and `endTime`
- Evaluation runs every minute via `chrome.alarms`
- Rules are automatically activated/deactivated based on current time

## Development

### Extension Development

- Watch mode: `npm run dev` (rebuilds on file changes)
- Type checking: `npm run type-check`

### Backend Development

- Run with auto-reload: `uvicorn main:app --reload`
- API docs available at: `http://localhost:8000/docs`

## Future Enhancements

- Implement actual blocking using `chrome.declarativeNetRequest`
- Add rule editing capabilities
- Support for more complex schedules (weekly, monthly, etc.)
- Export/import rules
- Statistics and usage tracking

## License

MIT



