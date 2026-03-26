import os
import re
import yaml
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH")
SUMMARIES_DIR = os.path.join(VAULT_PATH, "Summaries")

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

    if not content.startswith("---"): return
    
    parts = content.split("---", 2)
    if len(parts) < 3: return
    
    yaml_block = parts[1]
    body = parts[2]
    
    try:
        data = yaml.safe_load(yaml_block)
    except: return

    # 1. Triage Tags vs Topics
    old_tags = data.get("tags", [])
    new_tags = ["brain"]
    doc_type = data.get("type", "article")
    new_tags.append(doc_type)
    
    topics_to_add = []
    for t in old_tags:
        if t in ["brain", "article", "video", "paper", "book", "report"]:
            continue
        # Convert tag to a Title Case wikilink
        clean_t = t.replace("_", " ").replace("-", " ").title()
        topics_to_add.append(f"[[{clean_t}]]")

    data["tags"] = new_tags
    
    # 2. Update Body with Canonical Synonyms and Remove Redundant H1
    new_body = body.strip()
    
    # Remove H1 if it matches the title or starts with a wikilink
    # Pattern: # [[Title]] or # Title
    new_body = re.sub(r'^#\s*\[\[.*?\]\]\s*', '', new_body, flags=re.MULTILINE)
    new_body = re.sub(r'^#\s*.*?\n', '', new_body, count=1)
    
    for pattern, replacement in MAP.items():
        new_body = re.sub(pattern, replacement, new_body, flags=re.IGNORECASE)
    
    # 3. Inject any tags moved from YAML into the bottom of the body
    if topics_to_add:
        # Avoid duplicate injections if we run this twice
        unique_topics = [t for t in set(topics_to_add) if t not in new_body]
        if unique_topics:
            new_body = new_body.strip() + "\n\n**Topics:** " + ", ".join(unique_topics) + "\n"

    # 4. Final YAML Assembly
    new_yaml = yaml.dump(data, sort_keys=False, allow_unicode=True).strip()
    new_content = f"---\n{new_yaml}\n---{new_body}"
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"  [CLEANED] {file_path.name}")

def manifest_topics():
    print("📍 Manifesting Topic Hubs...")
    all_links = {}
    files = list(Path(SUMMARIES_DIR).glob("*.md"))
    
    # 1. Count all wikilinks in summaries
    for f in files:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
            # Find all [[Topic]] links
            links = re.findall(r'\[\[(.*?)\]\]', content)
            for link in links:
                # Handle piped links like [[Topic|Display]]
                topic = link.split('|')[0].strip()
                if topic and not topic.endswith(('.pdf', '.md', '_raw')):
                    all_links[topic] = all_links.get(topic, 0) + 1
    
    # 2. Create files for topics with 2+ mentions
    for topic, count in all_links.items():
        if count >= 2:
            topic_path = os.path.join(VAULT_PATH, f"{topic}.md")
            if not os.path.exists(topic_path):
                with open(topic_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {topic}\n\nAutomated Topic Hub for Centaur Brain.\n\n## Mentions\nThis topic is connected to {count} different summaries.")
                print(f"  [MANIFESTED] {topic} ({count} connections)")

def run_janitor():
    print(f"🧹 Janitor starting in {SUMMARIES_DIR}...")
    files = list(Path(SUMMARIES_DIR).glob("*.md"))
    for f in files:
        clean_file(f)
    
    manifest_topics()
    print("✨ Vault clean-up and manifestation complete.")

if __name__ == "__main__":
    run_janitor()
