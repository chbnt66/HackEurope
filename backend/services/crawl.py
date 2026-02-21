import asyncio
import json
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler

class Crawler:
    def __init__(self, url):
        self.url = url

    def extract_pme_data(self):
        return asyncio.run(self._async_extract())

    async def _async_extract(self):
        result_data = {
            "url": self.url,
            "markdown_content": "",
            "structured_data": [],
            "metadata": {}
        }

        async with AsyncWebCrawler(verbose=False) as crawler:
            print(f"step 1")
            result = await crawler.arun(url=self.url)
            print(f"step 2")
            if result.success:
                print(f"step 3")
                result_data["markdown_content"] = result.markdown
                result_data["metadata"] = result.metadata
                print(f"step 4")
                soup = BeautifulSoup(result.html, 'html.parser')
                json_ld_scripts = soup.find_all('script', type='application/ld+json')
                print(f"step 5")

                for script in json_ld_scripts:
                    print(f"step 6")
                    try:
                        clean_json = json.loads(script.string)
                        result_data["structured_data"].append(clean_json)
                    except (json.JSONDecodeError, TypeError):
                        continue
            else:
                print(f"Erreur de crawl : {result.error_message}")

        return result_data