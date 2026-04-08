# Permission Justifications for MoreTime YouTube Blocker

## Chrome Web Store review / appeals

If review flags **`storage`** or **`alarms`** as unused, that is incorrect for this extension: both are used only in the **background service worker** (MV3), not in content scripts or the popup bundle. Automated checks sometimes miss API usage behind bundling or failed validation when the uploaded package omitted built files (e.g. missing `content/metadata-checker.js`). Cite the implementation references below and confirm the submission ZIP was produced from `extension/dist` after `npm run build` (or `npm run pack:store`).

## 1. storage justification

**Implementation:** `chrome.storage.local` — [extension/src/background/storage.ts](extension/src/background/storage.ts) (`getRules` at line 14, `saveRules` at line 24). Loaded by the service worker via [extension/src/background/background.ts](extension/src/background/background.ts) (`import { getRules, saveRules } from './storage'`).

The storage permission is required to persist user-created blocking rules and their associated schedules. The extension allows users to create multiple blocking rules with duration-based or daily schedules, and these rules must be saved locally using chrome.storage.local. Without this permission, users would lose their blocking rules every time they close the browser, making the extension's core functionality unusable. The storage is used to save, retrieve, and manage blocking rules that define which YouTube videos should be blocked based on AI-generated metadata matching.

## 2. alarms justification

**Implementation:** `chrome.alarms.create` and `chrome.alarms.onAlarm` — [extension/src/background/background.ts](extension/src/background/background.ts) (lines 180–186).

The alarms permission is essential for the extension's scheduled blocking feature. The extension evaluates blocking rules every minute using chrome.alarms to determine if rules should be activated or deactivated based on their schedules (duration-based or daily recurring schedules). This periodic evaluation ensures that blocking rules automatically start and stop at the correct times without requiring user intervention. Without this permission, scheduled blocking would not function, as the extension needs to continuously monitor the current time against rule schedules.

## 3. tabs justification

The tabs permission is required to redirect YouTube video pages to the extension's blocked page when a video matches a user's blocking rule. When the content script detects that a YouTube video should be blocked based on metadata analysis, it communicates with the background service worker, which then uses chrome.tabs.update() to redirect the tab to the blocked.html page. This permission is necessary because content scripts cannot directly navigate to chrome-extension:// URLs - only the background script with tabs permission can perform this redirect operation.

## 4. declarativeNetRequest justification

The declarativeNetRequest permission is used to manage dynamic blocking rules for potential URL-based blocking functionality. While the extension primarily uses metadata-based blocking via content scripts, this permission allows the extension to clean up any legacy URL-based blocking rules and provides the foundation for future enhancements. The extension uses chrome.declarativeNetRequest.getDynamicRules() and chrome.declarativeNetRequest.updateDynamicRules() to maintain a clean state of blocking rules.

## 5. declarativeNetRequestWithHostAccess justification

The declarativeNetRequestWithHostAccess permission is required when using declarativeNetRequest API in conjunction with host permissions. Since the extension uses declarativeNetRequest API and has specific host permissions (https://www.youtube.com/* and https://moretime-production.up.railway.app/*), this permission is mandatory per Chrome's Manifest V3 requirements. It enables the declarativeNetRequest API to work with the specified host permissions, allowing the extension to manage blocking rules that may target specific domains or URL patterns.

## 6. Host permission justification

The extension uses specific host permissions instead of broad permissions for better security and faster review times:

1. **"https://www.youtube.com/*"** - Required to:
   - Access YouTube video pages where content scripts extract video metadata
   - Enable declarativeNetRequest API to work with YouTube URLs (required by declarativeNetRequestWithHostAccess)
   - Redirect YouTube video pages to the extension's blocked page when videos match blocking rules

2. **"https://moretime-production.up.railway.app/*"** - Required to:
   - Make API calls to the backend server to check if video metadata matches blocking rules using AI analysis
   - Generate blocking rules based on user descriptions via the backend API

The extension specifically targets YouTube video pages and uses AI-powered metadata analysis to determine if videos match user-defined blocking rules. These specific host permissions are more secure than broad permissions and allow the extension to function while minimizing privacy concerns and review delays.

