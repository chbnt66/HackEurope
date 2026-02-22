import asyncio
import json
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler
from typing import Dict, Any

async def extract_pme_data(url: str) -> Dict[str, Any]:
    """
    Transforms a URL into a dictionary ready for LLM analysis.
    """
    result_data = {
        "url": url,
        "markdown_content": "",
        "structured_data": [],
        "metadata": {}
    }

    # 1. Use Crawl4AI for clean Markdown
    async with AsyncWebCrawler(verbose=False) as crawler:
        result = await crawler.arun(url=url)
        
        if result.success:
            result_data["markdown_content"] = result.markdown
            result_data["metadata"] = result.metadata
            
            # 2. Use BeautifulSoup for JSON-LD (Structured Data)
            # Get raw HTML to extract <script type="application/ld+json"> tags
            soup = BeautifulSoup(result.html, 'html.parser')
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            
            for script in json_ld_scripts:
                try:
                    # Clean and load the JSON
                    clean_json = json.loads(script.string)
                    result_data["structured_data"].append(clean_json)
                except (json.JSONDecodeError, TypeError):
                    continue
        else:
            print(f"Crawl error: {result.error_message}")

    return result_data

# --- QUICK TEST ---
if __name__ == "__main__":
    # Replace with the URL of a local business to test
    test_url = "https://4ipgroup.com/" 
    
    data = asyncio.run(extract_pme_data(test_url))
    
    print(f"--- ANALYSIS OF: {data['url']} ---")
    print(f"Number of Markdown characters: {len(data['markdown_content'])}")
    print(f"Number of JSON-LD objects found: {len(data['structured_data'])}")
    print("\nStructured data example:")
    #print(json.dumps(data['structured_data'][:1], indent=2, ensure_ascii=False))
    print(json.dumps(data, indent=2, ensure_ascii=False))