# Project Specification: Centaur Brain (AI Knowledge Capture -> Obsidian)

## 1. Project Overview & Identity
**Centaur Brain** is a specialized tool for high-fidelity knowledge capture into a local **Obsidian** vault. It is a strategic pivot from the legacy "Centaur Notes" (Notion-based) system.

### Key Distinction: "Brain" vs. "Notes"
- **Centaur Notes (Existing):** Cloud-based, hierarchical Notion database for structured metadata.
- **Centaur Brain (New):** Local-first, flat-file knowledge graph in Obsidian. Focuses on **full-text preservation** and **AI-driven ontology mapping**.
- **Co-existence:** Centaur Brain will run in parallel with Centaur Notes. The Chrome Extension and Backend must have unique identifiers to avoid conflicts.

## 2. User Requirements
- **Ubiquitous Capture:** Capture web articles, academic papers (PDFs), YouTube transcripts, and book summaries from the browser.
- **Permanent Local Archive:** Every capture must save the **original raw source material** (Markdown or PDF) to the local filesystem.
- **AI-Augmented Synthesis:** Automatically generate a "Brain Node" (summary + ontology) using Google Gemini, containing bi-directional links (`[[wikilinks]]`) to key concepts.
- **Privacy & Ownership:** No cloud databases. All data lives in the user's Obsidian Vault.
- **PDF Intelligence:** Handle PDFs by downloading the original file and summarizing its contents.

## 3. System Architecture

### Frontend: Centaur Brain Chrome Extension
- **Identity:** Named "Centaur Brain" with a unique ID and icon to distinguish it from "Centaur Notes".
- **Extraction Engines:**
    - `Readability.js`: For clean article extraction.
    - `Turndown.js`: For HTML-to-Markdown conversion.
    - `YouTube Logic`: Fetches transcripts via background service workers.
- **PDF Detector:** Identifies PDF URLs and routes them to the backend for direct download.
- **Communication:** Sends JSON payloads to `http://localhost:8080/process`.

### Backend: Local Python API
- **Framework:** FastAPI (running locally via `uv`).
- **Processing Pipeline:**
    1. **Receiver:** Validates the payload (Source URL, Title, Raw Text/PDF URL).
    2. **Source Archiver:** 
        - Saves Markdown text to `Vault/Sources/{Title}_raw.md`.
        - Downloads PDFs to `Vault/Sources/{Title}.pdf`.
    3. **AI Analyst:** Sends the raw text to `gemini-2.0-flash` (or latest) with a specialized "Ontology Architect" prompt.
    4. **Node Creator:** Writes the AI output as a new Markdown file in `Vault/Inbox/{Title}.md`, including a YAML frontmatter and a `[[link]]` back to the raw source.
- **CLI Tools:**
    - `add_book.py`: A local script to trigger "Book Mode" (AI-generated book summaries saved directly to the vault).

## 4. Obsidian Data Schema

### Path A: The Source (`Vault/Sources/`)
- **Filename:** `{Sanitized_Title}_raw.md` or `{Sanitized_Title}.pdf`.
- **Content:** The verbatim extracted material.

### Path B: The Brain Node (`Vault/Inbox/`)
- **Filename:** `{Sanitized_Title}.md`.
- **Structure:**
```yaml
---
title: "{Title}"
author: "{Author/Channel}"
url: "{URL}"
captured_at: "{YYYY-MM-DD}"
type: "{article|video|paper|book}"
tags: [brain, {dynamic_tags}]
---
# [[{Title}]]

**Source Material:** [[{Sanitized_Title}_raw]]

## tl;dr
{Concise AI summary}

## Core Concepts
- **[[Concept 1]]**: {Description}
- **[[Concept 2]]**: {Description}

## Key Takeaways
- {Point 1}
- {Point 2}
```

## 5. Implementation Plan

### Phase 1: Environment & Dependency Refactoring
- [ ] **Python:** Initialize a new `uv` environment.
- [ ] **Dependencies:** Remove `notion-client` and `functions-framework`. Add `fastapi`, `uvicorn`, `httpx`, `python-multipart`, and `google-genai`.
- [ ] **Configuration:** Update `.env` to include local paths:
  - `OBSIDIAN_VAULT_PATH`
  - `GEMINI_API_KEY`
  - `PORT=8080`

### Phase 2: Local Backend Development (`backend/main.py`)
- [ ] **FastAPI Setup:** Create the `/process` endpoint.
- [ ] **File Operations:** Implement robust file writing logic for `Sources/` and `Inbox/` folders.
- [ ] **PDF Handler:** Use `httpx` to download and save PDFs; pass the URL to Gemini for analysis (using Gemini's native PDF support if possible, or text extraction).
- [ ] **AI Integration:** Port the prompt logic from legacy but update it to prioritize `[[wikilink]]` generation.

### Phase 3: Chrome Extension Transformation (`extension/`)
- [ ] **Manifest Update:** Rename to "Centaur Brain", update version, and reference the unique `centaur_notes_icon.jpg` (to be renamed/resized for "Brain").
- [ ] **UI/UX:** Update `popup.html` and `popup.js` to reflect the "Brain" branding.
- [ ] **PDF Logic:** Ensure the extension sends the PDF URL to the backend rather than attempting to scrape it directly.

### Phase 4: CLI Tooling Update (`backend/add_book.py`)
- [ ] **CLI Refactor:** Remove all Notion calls.
- [ ] **Direct-to-Vault:** Logic to generate a book summary via Gemini and save it straight to the Obsidian `Inbox`.

## 6. Security & Safety
- **Local Only:** The API will bind to `127.0.0.1` only.
- **Vault Safety:** Use sanitized filenames to prevent path injection or invalid filesystem characters.
- **API Keys:** Never hardcode keys; always use `.env`.
