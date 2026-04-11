# Centaur Brain: Deduplication Refactor Plan

## Objective
To eliminate redundant and overlapping concept pages within the Obsidian vault (`04 Concepts`) while preserving all unique insights, links, and graph integrity. This will be achieved through a two-pronged approach: **Proactive Prevention** (Prompt Engineering & RAG) and **Reactive Remediation** (Automated merging via `janitor_clean.py`).

---

## Phase 1: Proactive Prevention (RAG & Prompts)
**Goal:** Prevent the generation scripts from creating new, slightly altered names for concepts that already exist in the vault.

### 1.1 "Dictionary" Injection (RAG Approach)
*   **Action:** Update the scripts responsible for generating summaries and extracting concepts (e.g., `add_book.py`, `rebuild_vault.py`, or any future ingestion scripts) to read the current state of the vault.
*   **Implementation Steps:**
    *   Use the `OBSIDIAN_VAULT_PATH` defined in `backend/.env`.
    *   Dynamically read all filenames in the `04 Concepts` directory and strip the `.md` extension to create a "Known Concepts Dictionary".
    *   Inject this list into the system prompt context window before calling the LLM to extract topics/concepts.
    *   **Prompt Instruction:** *"Here is a list of existing concepts in the vault: [LIST]. If a concept you identify is highly similar, synonymous, or an acronym of an existing concept, DO NOT create a new name. You MUST use the exact existing concept name from the list for your wikilinks."*

### 1.2 Strict Naming Conventions Guardrails
*   **Action:** Add rigid formatting rules to the extraction prompts to ensure any *truly new* concepts follow a uniform standard, minimizing future programmatic drift.
*   **Implementation Steps:**
    *   Append a "Formatting & Naming Guardrails" section to the system prompts.
    *   **Prompt Rules:** 
        1. Always use singular nouns (e.g., 'Agent', not 'Agents').
        2. Always use the full term, omitting parenthetical acronyms in titles (e.g., 'Minimum Viable Product', never 'Minimum Viable Product (MVP)').
        3. Remove hyphens from compound concepts unless grammatically strictly required (e.g., 'Hyperwar', never 'Hyper-war').

---

## Phase 2: Reactive Remediation (`janitor_clean.py`)
**Goal:** Identify existing duplicates in the vault, intelligently merge their contents using the LLM, and heal all associated links across the entire vault.

### 2.1 Algorithmic Grouping (Normalization)
*   **Action:** Create a function in `janitor_clean.py` that normalizes filenames to find implicit duplicates.
*   **Implementation Steps:**
    *   Iterate through all files in `04 Concepts`.
    *   Apply a normalization transformation to the filenames: lowercase, strip hyphens, strip parentheticals, and convert plurals to singulars (e.g., stripping trailing 's' where appropriate).
    *   Group files that normalize to the identical string (e.g., `Hyperwar.md`, `Hyper-war.md` -> group: `hyperwar`).

### 2.2 LLM-Powered Synthesis
*   **Action:** Use the Gemini API to merge the content of grouped duplicates into a single, comprehensive "Canonical" page.
*   **Implementation Steps:**
    *   For each detected duplicate group, read the full text of all files in the group.
    *   Construct a prompt for the Gemini API (using the existing `gemini-3.1-flash-lite-preview` or similar free-tier model).
    *   **Prompt Instruction:** *"You are an expert knowledge manager. Merge the following concept pages into a single, comprehensive canonical page. You must retain all unique insights, theories, related concepts, and source links (e.g., `[[📄 Source Name]]`). Resolve any contradictions gracefully, eliminate repetition, and structure the output with clear Markdown headings. Do not output anything outside of the Markdown content."*

### 2.3 Canonical Naming & YAML Alias Injection
*   **Action:** Save the merged content correctly so that Obsidian recognizes the old terms.
*   **Implementation Steps:**
    *   Determine the best canonical filename from the group (e.g., the one without hyphens/acronyms).
    *   Take the discarded filenames (e.g., "Minimum Viable Product (MVP)") and inject them into the YAML frontmatter of the new canonical file as `aliases: ["Minimum Viable Product (MVP)"]`.
    *   Write the synthesized LLM output to the canonical `.md` file.

### 2.4 Vault-Wide Link Healing
*   **Action:** Ensure no broken links remain in `02 Summaries`, `03 Atlas`, or `04 Concepts`.
*   **Implementation Steps:**
    *   Iterate through all markdown files in the vault.
    *   For every file that was merged and discarded, perform a regex find-and-replace.
    *   Convert standard links to piped links to preserve readability. Example: Change `[[Hyper-war]]` to `[[Hyperwar|Hyper-war]]`.
    *   Delete the old duplicate files from the filesystem once the healing is verified.

### 2.5 Execution & Limits (Free-Tier Protection)
*   **Action:** Protect the Gemini API free tier limits (500 requests/day) and log the changes.
*   **Implementation Steps:**
    *   **Chunking & State Management:** The janitor script runs as a cron or scheduled job. It must not attempt to process all 629+ files in a single run. Implement a lightweight state tracker (e.g., `janitor_state.json`) that records which files or duplicate groups have already been processed or evaluated.
    *   **Daily Quota Guardrails:** Introduce a hardcoded limit for the number of LLM calls per run (e.g., `MAX_API_CALLS_PER_RUN = 20`). Once this limit is reached, the script should gracefully exit and resume from the saved state on the next run. This ensures the script never exhausts the daily 500 request quota, leaving room for other scripts (like `add_book.py`).
    *   **Rate Limiting:** Add a slight delay (e.g., `asyncio.sleep(4)`) between LLM calls during the synthesis loop to avoid hitting Requests Per Minute (RPM) limits.
    *   **Logging:** Log all grouped duplicates, synthesized files, and healed links using the existing `log_action` from `logger.py`.

---
*Instructions for Coding Agent: Implement the above features without modifying the core functionality of unrelated janitor tasks. Ensure all file paths use `os.path.join` and reference the existing `VAULT_PATH` environment variable.*