# Privacy Policy for MoreTime YouTube Blocker

**Last Updated:** [Date]

## Introduction

MoreTime YouTube Blocker ("we," "our," or "the Extension") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, and share information when you use our Chrome extension.

## Information We Collect

### 1. Personally Identifiable Information

We may collect personally identifiable information that you voluntarily provide when creating blocking rules, including:
- User descriptions and preferences you enter when creating blocking rules
- Any personal information you include in rule descriptions (e.g., names, email addresses, or other identifiers)

**How we use it:** This information is used solely to generate and manage your blocking rules. User descriptions are sent to our backend server for AI-powered rule generation and matching.

### 2. Web History

We collect information about the web pages you visit, specifically:
- URLs of YouTube video pages you visit (e.g., `https://www.youtube.com/watch?v=...`)
- Page titles and associated metadata
- Time of visit (for schedule evaluation)

**How we use it:** We use this information to determine if visited YouTube videos match your blocking rules and to evaluate schedule-based blocking rules.

### 3. User Activity

We monitor user activity on YouTube pages, including:
- Navigation to YouTube video pages
- Page load events
- Redirect actions when videos match blocking rules

**How we use it:** This activity monitoring is necessary to detect when you visit YouTube videos and apply blocking rules in real-time.

### 4. Website Content

We extract and analyze website content from YouTube pages, including:
- Text content (video titles, descriptions)
- Open Graph Protocol (OGP) metadata (og:title, og:description, og:type, og:site_name)
- Video IDs and URLs
- Hyperlinks and page structure

**How we use it:** This content is analyzed using AI to determine if videos match your blocking rules. The metadata is sent to our backend server for processing.

## How We Use Your Information

We use the collected information to:
1. **Generate Blocking Rules:** Your rule descriptions are processed by AI services to generate domain and pattern suggestions
2. **Match Videos:** Video metadata is analyzed against your rules to determine if content should be blocked
3. **Evaluate Schedules:** We check current time against your rule schedules to activate or deactivate blocking
4. **Store Preferences:** Your blocking rules and settings are stored locally in your browser

## Data Storage

- **Local Storage:** Your blocking rules and preferences are stored locally in your browser using Chrome's storage API (`chrome.storage.local`). This data never leaves your device.
- **Backend Processing:** When you create rules or visit YouTube videos, relevant data (descriptions, metadata, URLs) is temporarily sent to our backend server for AI processing.

## Data Sharing

We share your information with the following third parties:

1. **Backend Server:** User descriptions, video metadata, and URLs are sent to our backend server (hosted by you or a service provider) for AI-powered rule generation and matching.

2. **Anthropic (Claude API):** Your rule descriptions and video metadata are sent to Anthropic's Claude API to generate blocking rules and determine if videos match your rules.

3. **OpenAI (Embeddings API):** Video metadata and rule descriptions are processed through OpenAI's embeddings API to calculate similarity scores for efficient matching.

**Important:** We do not sell your personal information. Data is shared only with the third-party services listed above, which are necessary for the Extension's core functionality.

## Data Retention

- **Local Data:** Your blocking rules are stored locally in your browser until you delete them or uninstall the extension.
- **Backend Data:** Data sent to our backend server is processed in real-time and is not permanently stored. However, your backend server may log requests for debugging purposes.
- **Third-Party Services:** Data sent to Anthropic and OpenAI is subject to their respective privacy policies and data retention practices.

## Your Rights and Choices

You have the following rights regarding your data:

1. **Access:** You can view all your blocking rules through the extension popup
2. **Delete:** You can delete individual rules or uninstall the extension to remove all stored data
3. **Modify:** You can enable, disable, or edit your blocking rules at any time
4. **Opt-Out:** You can stop using the extension at any time, which will prevent further data collection

## Security

We implement reasonable security measures to protect your information:
- Data is stored locally in your browser using Chrome's secure storage API
- Communication with our backend server uses HTTPS encryption
- We do not store API keys or sensitive credentials in the extension

However, no method of transmission over the internet is 100% secure, and we cannot guarantee absolute security.

## Children's Privacy

Our Extension is not intended for users under the age of 13. We do not knowingly collect personal information from children under 13. If you believe we have collected information from a child under 13, please contact us immediately.

## Changes to This Privacy Policy

We may update this Privacy Policy from time to time. We will notify you of any changes by updating the "Last Updated" date at the top of this policy. Your continued use of the Extension after any changes constitutes acceptance of the updated policy.

## Third-Party Privacy Policies

This Extension uses third-party services that have their own privacy policies:
- [Anthropic Privacy Policy](https://www.anthropic.com/privacy)
- [OpenAI Privacy Policy](https://openai.com/policies/privacy-policy)

We encourage you to review these policies to understand how these services handle your data.

## Contact Us

If you have questions about this Privacy Policy or our data practices, please contact us at:
- Email: [Your Email Address]
- Website: [Your Website URL]

## Compliance

This Privacy Policy complies with:
- Chrome Web Store Program Policies
- General Data Protection Regulation (GDPR) requirements
- California Consumer Privacy Act (CCPA) requirements

---

**Note:** This Extension requires a backend server to function. If you are self-hosting the backend, you are responsible for ensuring your server complies with applicable privacy laws and regulations.

