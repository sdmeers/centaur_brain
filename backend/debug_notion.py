import os
import json
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

notion = Client(auth=NOTION_API_KEY)

def debug_database():
    try:
        # 1. Standard Retrieve
        db = notion.databases.retrieve(database_id=NOTION_DATABASE_ID)
        print("Database Properties (Standard):")
        print(json.dumps(db.get("properties", {}), indent=2))
        
        # 2. Check Data Source if it exists
        if "data_sources" in db and db["data_sources"]:
            ds_id = db["data_sources"][0]["id"]
            print(f"\nRetrieving Data Source: {ds_id}")
            ds = notion.data_sources.retrieve(data_source_id=ds_id)
            print("Data Source Properties:")
            print(json.dumps(ds.get("properties", {}), indent=2))
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_database()
