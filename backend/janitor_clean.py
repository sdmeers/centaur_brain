import os
import re
import yaml
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from logger import log_action
from google import genai
from google.genai import types

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=dotenv_path)
VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not VAULT_PATH or not GEMINI_API_KEY:
    raise RuntimeError("Missing OBSIDIAN_VAULT_PATH or GEMINI_API_KEY in .env")

SUMMARIES_DIR = os.path.join(VAULT_PATH, "02 Summaries")
ATLAS_DIR = os.path.join(VAULT_PATH, "03 Atlas")
CONCEPTS_DIR = os.path.join(VAULT_PATH, "04 Concepts")

client = genai.Client(api_key=GEMINI_API_KEY)

# Canonical Mapping
MAP = {
    r"#agi\b": "[[Artificial General Intelligence]]",
    r"\[\[AGI\]\]": "[[Artificial General Intelligence]]",
    r"#ai\b": "[[Artificial Intelligence]]",
    r"#artificial_intelligence\b": "[[Artificial Intelligence]]",
    r"#artificial-intelligence\b": "[[Artificial Intelligence]]",
    r"\[\[AI\]\]": "[[Artificial Intelligence]]",
    r"#ethics\b": "[[Ethics]]",
    r"\[\[Ethical Artificial Intelligence\]\]": "[[Ethics]]",
    r"\[\[Ethical AI\]\]": "[[Ethics]]",
    r"#geopolitics\b": "[[Geopolitics]]",
    r"\[\[LLM\]\]": "[[Large Language Model]]",
    r"#cybersecurity\b": "[[Cybersecurity]]"
}

def clean_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    match = re.search(r'---(.*?)---', content, re.DOTALL)
    if not match: return
    
    yaml_block = match.group(1)
    body = content.split("---", 2)[2]
    
    try:
        data = yaml.safe_load(yaml_block)
    except: return

    old_tags = data.get("tags", [])
    new_tags = ["brain"]
    doc_type = data.get("type", "article")
    new_tags.append(doc_type)
    
    topics_to_add = []
    for t in old_tags:
        if t in ["brain", "article", "video", "paper", "book", "report"]:
            continue
        clean_t = t.replace("_", " ").replace("-", " ").title()
        topics_to_add.append(f"[[{clean_t}]]")

    data["tags"] = new_tags
    new_body = body.strip()
    new_body = re.sub(r'^#\s*\[\[.*?\]\]\s*', '', new_body, flags=re.MULTILINE)
    new_body = re.sub(r'^#\s*.*?\n', '', new_body, count=1)
    
    for pattern, replacement in MAP.items():
        new_body = re.sub(pattern, replacement, new_body, flags=re.IGNORECASE)
    
    if topics_to_add:
        unique_topics = [t for t in set(topics_to_add) if t not in new_body]
        if unique_topics:
            new_body = new_body.strip() + "\n\n**Topics:** " + ", ".join(unique_topics) + "\n"

    new_yaml = yaml.dump(data, sort_keys=False, allow_unicode=True).strip()
    new_content = f"---\n{new_yaml}\n---\n\n{new_body.strip()}"
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"  [FIXED] {file_path.name}")

def extract_snippets(content: str, link: str, snippet_length: int = 150) -> list[str]:
    snippets = []
    pattern = re.compile(rf'.{{0,{snippet_length}}}\[\[{re.escape(link)}(?:\|.*?)?\]\].{{0,{snippet_length}}}', re.IGNORECASE)
    for match in pattern.finditer(content):
        snippets.append(match.group(0).strip().replace('\n', ' '))
    return snippets

def run_janitor():
    print(f"🧹 Janitor starting...")
    
    # 1. Clean existing summaries
    files = list(Path(SUMMARIES_DIR).glob("*.md"))
    for f in files:
        clean_file(f)
        
    # 2. Orphan Link Detection
    print("📍 Detecting Missing Link Snippets...")
    all_markdown_files = list(Path(SUMMARIES_DIR).glob("*.md")) + list(Path(CONCEPTS_DIR).glob("*.md"))
    
    links_data = {} # link -> {'count': int, 'snippets': list[str]}
    
    for f in all_markdown_files:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
            links = re.findall(r'\[\[(.*?)\]\]', content)
            for raw_link in links:
                topic = raw_link.split('|')[0].strip()
                if not topic or topic.endswith(('.pdf', '.md', '_raw')):
                    continue
                    
                if topic not in links_data:
                    links_data[topic] = {'count': 0, 'snippets': []}
                
                links_data[topic]['count'] += 1
                if len(links_data[topic]['snippets']) < 5:
                    snippets = extract_snippets(content, topic)
                    links_data[topic]['snippets'].extend(snippets)

    # Check which links are missing a file in CONCEPTS_DIR, ATLAS_DIR, or SUMMARIES_DIR
    missing_concepts = {}
    source_emojis = ("🎞️", "🏛️", "📄", "📖")
    
    for topic, data in links_data.items():
        # Skip if the link starts with a source emoji
        if topic.startswith(source_emojis):
            continue
            
        safe_topic = re.sub(r'[\\/*?:"<>|]', "", topic).strip()
        concept_path = os.path.join(CONCEPTS_DIR, f"{safe_topic}.md")
        atlas_path = os.path.join(ATLAS_DIR, f"{safe_topic}.md")
        summary_path = os.path.join(SUMMARIES_DIR, f"{safe_topic}.md")
        
        if not any(os.path.exists(p) for p in [concept_path, atlas_path, summary_path]):
            missing_concepts[topic] = data
            
    # 3. Auto-Healing
    # Sort missing concepts by count descending
    sorted_missing = sorted(missing_concepts.items(), key=lambda x: x[1]['count'], reverse=True)
    top_n = min(5, len(sorted_missing))
    
    manifested_count = 0
    if top_n > 0:
        print(f"🏥 Auto-healing top {top_n} missing concepts...")
        for topic, data in sorted_missing[:top_n]:
            print(f"  [HEALING] [[{topic}]] ({data['count']} mentions)")
            safe_topic = re.sub(r'[\\/*?:"<>|]', "", topic).strip()
            concept_path = os.path.join(CONCEPTS_DIR, f"{safe_topic}.md")
            
            snippets_str = "\n".join([f"- \"{s}\"" for s in data['snippets'][:5]])
            prompt = f"""You are building a 'Second Brain'. 
Generate a concept page for '{topic}' based on its usage in the following context snippets from the user's vault:

{snippets_str}

Please return the content formatted as Markdown. Include a definition, and synthesize how it's being used based on the snippets."""
            
            try:
                response = client.models.generate_content(
                    model="gemini-3.1-flash-lite-preview",
                    contents=prompt
                )
                with open(concept_path, 'w', encoding='utf-8') as f:
                    f.write(response.text.strip())
                manifested_count += 1
            except Exception as e:
                print(f"  [ERROR] Failed to heal [[{topic}]]: {e}")
                
    # 4. Contradiction/Synthesis Scan
    print("🔍 Scanning for large concepts to refactor...")
    refactored_count = 0
    concept_files = list(Path(CONCEPTS_DIR).glob("*.md"))
    for f in concept_files:
        if os.path.getsize(f) > 2000: # ~500 words
            print(f"  [REFACTORING] {f.name}")
            with open(f, 'r', encoding='utf-8') as file:
                content = file.read()
                
            prompt = f"""Refactor and organize this concept page, checking for internal contradictions and improving structure. Maintain all existing wikilinks and core information.

Here is the concept page content:
{content}
"""
            try:
                response = client.models.generate_content(
                    model="gemini-3.1-flash-lite-preview",
                    contents=prompt
                )
                with open(f, 'w', encoding='utf-8') as file:
                    file.write(response.text.strip())
                refactored_count += 1
            except Exception as e:
                print(f"  [ERROR] Failed to refactor {f.name}: {e}")
                
    # 5. Orphan Detection
    print("🕸️ Scanning for Orphaned Concepts...")
    all_summaries_and_atlas = list(Path(SUMMARIES_DIR).glob("*.md")) + list(Path(ATLAS_DIR).glob("*.md"))
    active_links = set()

    for f in all_summaries_and_atlas:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
            links = re.findall(r'\[\[(.*?)\]\]', content)
            for raw_link in links:
                topic = raw_link.split('|')[0].strip()
                active_links.add(topic)

    concept_files = list(Path(CONCEPTS_DIR).glob("*.md"))
    orphans = []
    for f in concept_files:
        concept_name = f.stem
        if concept_name not in active_links:
            orphans.append(concept_name)

    if orphans:
        print(f"📍 Found {len(orphans)} orphaned concepts (manually review in 04 Concepts/):")
        for o in sorted(orphans):
            print(f"  - [[{o}]]")
    else:
        print("✅ No orphaned concepts found.")

    print("✨ Vault clean-up, auto-healing, and refactoring complete.")
    log_action("Lint", f"Janitor pass: {manifested_count} concepts healed, {refactored_count} refactored, {len(orphans)} orphans detected.")

if __name__ == "__main__":
    run_janitor()
