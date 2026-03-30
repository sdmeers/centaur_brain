import httpx
import time
import os

def reprocess_all():
    # Use the port from environment or default to 8080
    port = os.getenv("PORT", "8080")
    api_url = f"http://127.0.0.1:{port}/process"
    
    source_file = "sources_all.txt"
    if not os.path.exists(source_file):
        print(f"Error: {source_file} not found.")
        return

    with open(source_file, "r") as f:
        sources = [line.strip() for line in f if line.strip()]
    
    print(f"Starting re-indexing of {len(sources)} sources...")
    
    for i, source in enumerate(sources, 1):
        payload = {
            "source": "re-index",
            "url": source,
            "title": "Re-Indexing Existing Content",
            "authorHint": "",
            "markdownText": "" 
        }
        
        max_retries = 3
        retry_count = 0
        success = False
        
        while retry_count < max_retries and not success:
            try:
                print(f"[{i}/{len(sources)}] Processing: {source} (Attempt {retry_count + 1})")
                response = httpx.post(api_url, json=payload, timeout=180.0) 
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"  ✓ Success: {data.get('title')}")
                    success = True
                elif response.status_code == 500 and "503" in response.text:
                    print(f"  !! Gemini 503 Overload. Retrying in 10s...")
                    retry_count += 1
                    time.sleep(10)
                else:
                    print(f"  ✗ Failed: {source} (Status: {response.status_code}, Body: {response.text[:100]})")
                    break # Don't retry other errors
            except Exception as e:
                print(f"  !! Error: {source} -> {str(e)}")
                retry_count += 1
                time.sleep(5)
        
        # Respectful delay between different URLs
        time.sleep(2)

if __name__ == "__main__":
    reprocess_all()
