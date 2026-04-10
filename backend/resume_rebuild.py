import os
import asyncio
from dotenv import load_dotenv
from add_book import add_book

# Fix path for .env
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=dotenv_path)

# Only the books that failed or were partial
REMAINING_BOOKS = [
    ("The Singularity is Nearer", "Ray Kurzweil"),
    ("Thinking, Fast and Slow", "Daniel Kahneman"),
    ("Tools and Weapons", "Brad Smith")
]

async def resume_rebuild():
    print(f"Resuming Rebuild: Processing {len(REMAINING_BOOKS)} remaining books...")
    for idx, (title, author) in enumerate(REMAINING_BOOKS):
        print(f"\n[Book {idx+1}/{len(REMAINING_BOOKS)}] Processing: {title} by {author}")
        try:
            await add_book(title, author)
        except Exception as e:
            print(f"  Error processing book {title}: {e}")
            
        if idx < len(REMAINING_BOOKS) - 1:
            print("  Sleeping for 120 seconds to respect API rate limits...")
            await asyncio.sleep(120)

    print("\n--- Remaining Books Rebuild Complete ---")

if __name__ == "__main__":
    asyncio.run(resume_rebuild())
