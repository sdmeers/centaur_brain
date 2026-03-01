# Project Specification: Centaur Notes (AI Knowledge Capture -> Notion)

## 1. Project Overview
**Centaur Notes** is a personal knowledge management system designed to capture articles, YouTube videos, and books with zero maintenance. It uses a Chrome Extension to clip web content and Notion Database Webhooks to process physical/e-books. A serverless Google Cloud Run backend handles all requests, dynamically fetches existing tags to maintain a stable taxonomy, and uses Vertex AI to summarize the content before saving it into a Notion Intelligence Hub.

## 2. Tech Stack & Architecture
* **Frontend (Capture):** Centaur Notes Chrome Extension (Manifest V3).
    * `Readability.js`: Extracts main article text, stripping ads/navbars.
    * `Turndown.js`: Converts HTML to Markdown to save AI tokens.
    * `youtube-transcript` (or similar): Fetches closed captions for YouTube URLs to avoid audio processing costs.
* **Backend API:** Existing Python 3.12 app using `functions-framework` and `uv` for dependency management.
* **AI Engine:** Google Cloud Vertex AI (Model: `gemini-2.5-flash`).
* **Database & UI:** Notion (via the Official Notion API & Notion Webhook Buttons).

## 3. Notion Database Schema
A Notion Database (The "Centaur Intelligence Hub") must be created with the following properties:
* **Name** (Title property): The title of the article, video, or book.
* **URL** (URL property): The link to the original source.
* **Categories** (Multi-select property): E.g., Defence, AI, Technology. (The backend will dynamically read and append to this list).
* **Top 3 Points** (Text/Rich Text property): A bulleted list of the core takeaways.
* **Date Added** (Date property): Automatically set to the day it was captured.
* **Generate AI Summary** (Button property): Configured to "Send Webhook" to the Cloud Run URL, passing the `Name` and `page_id`.

*Note: The detailed 200-400 word AI summary will be injected into the actual **Page Body** (the content inside the Notion card).*

## 4. Core Workflows

### A. Route 1: Chrome Extension (Web Articles & YouTube)
1. **Trigger:** User clicks the Centaur Notes extension icon on a webpage.
2. **Extraction:**
   * *If standard web page:* Extension uses `Readability.js` and `Turndown.js` to extract and convert text.
   * *If YouTube:* Extension intercepts and fetches the video's auto-generated transcript to bypass audio token costs.
3. **Send:** Extension sends POST request to Cloud Run: `{ source: "extension", url, markdownText: extracted_text_or_transcript }`.
4. **Process:** * Cloud Run queries Notion API to fetch existing "Categories" options.
   * Cloud Run calls Vertex AI to summarize the `markdownText`.
   * Cloud Run calls `notion.pages.create()` to build a new card, passing the new tags, Top 3 points, and injecting the Markdown summary into the page children.

### B. Route 2: Notion Webhook Button (Books)
1. **Trigger:** User types a book title (e.g., "Army of None") in Notion and clicks the "Generate AI Summary" button.
2. **Send:** Notion sends a POST webhook to Cloud Run: `{ source: "notion_button", page_id, title }`.
3. **Process:**
   * Cloud Run queries Notion API to fetch existing "Categories" options.
   * Cloud Run calls Vertex AI to summarize the book based *only* on the `title`, relying on the AI's internal knowledge base.
   * Cloud Run calls `notion.pages.update()` (to add tags/top 3 points) and `notion.blocks.children.append()` (to add the detailed summary to the body) targeting the existing `page_id`.

## 5. AI System Prompt & Schema
The Cloud Run Function must construct the prompt as follows, forcing an `application/json` response schema from Vertex AI:

**System Instruction:**
"You are the engine behind 'Centaur Notes', an expert AI summarising texts about AI, Defence, Tech, and Geopolitics. You will receive either the full text of an article/transcript OR just the title of a known book. 
Your task is to output a JSON object with the following keys:
1. `title`: A concise title for the text.
2. `top_3_points`: An array of exactly 3 'must know' bullet points.
3. `summary`: A 200-400 word detailed summary. You MUST use rich Markdown formatting within this string (`###` for subheadings, `**bold**`).
4. `selected_categories`: An array of 1-3 categories that best fit this text. **CRITICAL INSTRUCTION:** You MUST prioritize selecting from the 'Existing Categories' list provided to maintain a stable taxonomy. ONLY suggest a new category if the text covers a distinct topic completely unrepresented by the current list."

**User Prompt Payload (Dynamic):**
*If Route 1 (Extension):* "Existing Categories: [{fetched_categories}]\nText to analyze: {markdown_text}"
*If Route 2 (Notion Button):* "Existing Categories: [{fetched_categories}]\nPlease provide a comprehensive summary and analysis of the following book based on your internal knowledge: {title}"

## 6. Implementation Phases (For AI Assistant)

**Phase 1: Environment & Notion Setup**
* Set up local `.env` variables for `NOTION_API_KEY`, `NOTION_DATABASE_ID`, and GCP Project details.

**Phase 2: Refactoring the Existing Python Backend**
* **Cleanup:** Remove all `firestore` imports, emulator logic, and `google-cloud-firestore` dependencies from `pyproject.toml` and `main.py`.
* **Dependencies:** Add `notion-client` via `uv add notion-client`.
* **Logic:** Refactor the existing `main.py` endpoints. Keep the CORS headers and Vertex AI initialization. Implement the Notion API call to fetch existing Multi-select options, call Vertex AI, and implement the dual-route logic (create new page vs. update existing page). Use a markdown-to-notion-blocks parser to ensure the `summary` renders correctly in the page body.

**Phase 3: Centaur Notes Chrome Extension**
* Update the existing extension to point to the correct local/deployed Cloud Run endpoint.
* Implement the Youtube transcript fetching logic for video URLs.
* Ensure the background script correctly displays a loading/success UI based on the new backend responses.