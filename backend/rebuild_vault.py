import os
import re
import asyncio
import fitz  # PyMuPDF
from dotenv import load_dotenv

# Local imports from main.py
from main import (
    generate_brain_node, 
    update_concept_page, 
    get_atlas_themes, 
    sanitize_filename, 
    fetch_cover
)
from add_book import add_book
from logger import log_action

load_dotenv()

OBSIDIAN_VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH")
if not OBSIDIAN_VAULT_PATH:
    raise RuntimeError("CRITICAL: OBSIDIAN_VAULT_PATH missing from .env")

SOURCES_PATH = os.path.join(OBSIDIAN_VAULT_PATH, "01 Sources")
SUMMARIES_PATH = os.path.join(OBSIDIAN_VAULT_PATH, "02 Summaries")
CONCEPTS_PATH = os.path.join(OBSIDIAN_VAULT_PATH, "04 Concepts")

def extract_pdf_text_local(file_path: str) -> str:
    """Reads PDF text from a local file."""
    doc = fitz.open(file_path)
    text = ""
    max_pages = min(20, len(doc)) # Extract up to 20 pages
    for i in range(max_pages):
        text += doc[i].get_text()
    return text.strip()

BOOKS_TO_EXTRACT = [
    ("A Thousand Brains: A New Theory of Intelligence", "Jeff Hawkins"),
    ("Army of None: Autonomous Weapons and the Future of War", "Paul Scharre"),
    ("Chip War", "Chris Miller"),
    ("Deep Utopia", "Nick Bostrom"),
    ("Factfulness", "Hans Rosling"),
    ("Four Battlegrounds: Power in the Age of Artificial Intelligence", "Paul Scharre"),
    ("Genesis: Artificial Intelligence, Hope, and the Human Spirit", "Henry A. Kissinger, Eric Schmidt, Craig Mundie"),
    ("Good Strategy, Bad Strategy", "Richard Rumelt"),
    ("Good to Great", "Jim Collins"),
    ("Hello World: Being Human in the Age of Algorithms", "Hannah Fry"),
    ("How Innovation Works", "Matt Ridley"),
    ("Human Compatible", "Stuart Russell"),
    ("I, Warbot: The Dawn of Artificially Intelligent Conflict", "Kenneth Payne"),
    ("Leaders Eat Last", "Simon Sinek"),
    ("Start With Why", "Simon Sinek"),
    ("Supercommunicators", "Charles Duhigg"),
    ("Superintelligence: Paths, Dangers, Strategies", "Nick Bostrom"),
    ("The Age of AI: And Our Human Future", "Henry A. Kissinger, Eric Schmidt, Daniel Huttenlocher"),
    ("The AI Mirror", "Shannon Vallor"),
    ("The Atomic Human", "Neil D. Lawrence"),
    ("The Coming Wave", "Mustafa Suleyman"),
    ("The Culture Code", "Daniel Coyle"),
    ("The Kill Chain: Defending America in the Future of High-Tech Warfare", "Christian Brose"),
    ("The Lean Startup", "Eric Ries"),
    ("The Singularity is Nearer", "Ray Kurzweil"),
    ("Thinking, Fast and Slow", "Daniel Kahneman"),
    ("Tools and Weapons", "Brad Smith")
]

async def rebuild_all():
    print("Starting Full Vault Rebuild Process...")
    
    if os.path.exists(SOURCES_PATH):
        source_files = [f for f in os.listdir(SOURCES_PATH) if f.endswith('.md') or f.endswith('.pdf')]
        source_files.sort()
        
        print(f"\n--- Phase 1: Rebuilding {len(source_files)} Sources ---")

        for idx, filename in enumerate(source_files):
            print(f"\n[Source {idx+1}/{len(source_files)}] Processing: {filename}")
            
            file_path = os.path.join(SOURCES_PATH, filename)
            content_text = ""
            url = ""
            is_youtube = False
            
            # Extract title by removing extension and _raw
            raw_title = filename
            if raw_title.endswith("_raw.md"):
                raw_title = raw_title[:-7]
            elif raw_title.endswith(".pdf"):
                raw_title = raw_title[:-4]
                
            # Remove emojis at the start for a clean title hint
            title_hint = re.sub(r'^[^\w\s]+', '', raw_title).strip()
            
            if filename.endswith(".md"):
                with open(file_path, "r", encoding="utf-8") as f:
                    content_text = f.read()
                    
                # Try to extract URL
                url_match = re.search(r'^Source:\s*(https?://[^\s]+)', content_text, re.MULTILINE)
                if url_match:
                    url = url_match.group(1)
                    is_youtube = "youtube.com/watch" in url or "youtu.be/" in url
                    
            elif filename.endswith(".pdf"):
                content_text = extract_pdf_text_local(file_path)
                url = filename
                
            if not content_text:
                print(f"  Skipping {filename} - no content extracted.")
                continue
                
            try:
                print(f"  Generating Brain Node for '{title_hint}'...")
                atlas_themes = get_atlas_themes()
                brain_node_result = await generate_brain_node(
                    title_hint=title_hint,
                    author_hint="",
                    url=url,
                    content=content_text,
                    atlas_themes=atlas_themes
                )
                
                brain_node_markdown = brain_node_result.summary_markdown.strip()
                
                # Clean yaml brackets
                def clean_yaml_brackets(content: str) -> str:
                    def fix_list(match):
                        val = match.group(1)
                        items = re.findall(r'\[+([^\[\]]+)\]+', val)
                        clean_items = []
                        for item in items:
                            parts = [p.strip().strip('"').strip("'") for p in item.split(',')]
                            clean_items.extend([p for p in parts if p])
                        formatted = ", ".join([f'"[[{t}]]"' for t in clean_items])
                        return f'theme_related: [{formatted}]'

                    def fix_primary(match):
                        val = match.group(1)
                        items = re.findall(r'\[+([^\[\]]+)\]+', val)
                        if items:
                            t = items[0].strip().strip('"').strip("'")
                            return f'theme_primary: "[[{t}]]"'
                        return match.group(0)

                    content = re.sub(r'theme_related:\s*(.*)', fix_list, content)
                    content = re.sub(r'theme_primary:\s*(.*)', fix_primary, content)
                    return content

                brain_node_markdown = clean_yaml_brackets(brain_node_markdown)
                
                # Fetch Cover Image
                cover_url = fetch_cover(url, is_youtube)
                if cover_url:
                    if 'cover: "' in brain_node_markdown:
                        brain_node_markdown = re.sub(r'cover: ".*?"', f'cover: "{cover_url}"', brain_node_markdown)
                    else:
                        brain_node_markdown = brain_node_markdown.replace("type:", f"cover: \"{cover_url}\"\ntype:", 1)
                
                # Finalize Title
                real_title = title_hint
                match = re.search(r'^title:\s*"(.*?)"', brain_node_markdown, re.MULTILINE)
                if match:
                    real_title = match.group(1)
                
                real_title = re.sub(r'^\(\d+\)\s*', '', real_title)
                safe_title = sanitize_filename(real_title)
                
                # Inject Source link
                source_link_name = filename
                if filename.endswith(".md"):
                    source_link_name = filename[:-3] # Remove .md to link to the file
                source_injection = f"\n\n**Source Material:** [[{source_link_name}]]\n\n## tl;dr"
                brain_node_markdown = brain_node_markdown.replace("\n## tl;dr", source_injection, 1)
                
                node_path = os.path.join(SUMMARIES_PATH, f"{safe_title}.md")
                with open(node_path, "w", encoding="utf-8") as f:
                    f.write(brain_node_markdown)
                    
                # Process Concepts
                if brain_node_result.concepts:
                    print(f"  Processing {len(brain_node_result.concepts)} concepts...")
                    for concept in brain_node_result.concepts:
                        await update_concept_page(concept, brain_node_markdown, safe_title)
                else:
                    print(f"  WARNING - 0 concepts were extracted by Gemini.")
                    
                # Log
                themes = []
                primary_match = re.search(r'theme_primary:\s*"(.*?)"', brain_node_markdown)
                if primary_match:
                    themes.append(primary_match.group(1))
                    
                related_match = re.search(r'theme_related:\s*\[(.*?)\]', brain_node_markdown)
                if related_match:
                    related_themes = [t.strip().strip('"').strip("'") for t in related_match.group(1).split(',')]
                    themes.extend([t for t in related_themes if t])
                    
                log_action("Re-Ingested", f'Source: "{safe_title}"', concepts=themes)
                print(f"  Successfully saved: {safe_title}")
                
            except Exception as e:
                print(f"  Error processing {filename}: {e}")

            print("  Sleeping for 120 seconds to respect API rate limits...")
            await asyncio.sleep(120)

    print(f"\n--- Phase 2: Rebuilding {len(BOOKS_TO_EXTRACT)} Books ---")
    for idx, (title, author) in enumerate(BOOKS_TO_EXTRACT):
        print(f"\n[Book {idx+1}/{len(BOOKS_TO_EXTRACT)}] Processing: {title} by {author}")
        try:
            await add_book(title, author)
        except Exception as e:
            print(f"  Error processing book {title}: {e}")
            
        if idx < len(BOOKS_TO_EXTRACT) - 1:
            print("  Sleeping for 120 seconds to respect API rate limits...")
            await asyncio.sleep(120)

    print("\n--- Full Vault Rebuild Complete ---")

if __name__ == "__main__":
    asyncio.run(rebuild_all())
