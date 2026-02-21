import asyncio
import json
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler
from typing import Dict, Any

async def extract_pme_data(url: str) -> Dict[str, Any]:
    """
    Transforme une URL en un dictionnaire prêt pour l'analyse par un LLM.
    """
    result_data = {
        "url": url,
        "markdown_content": "",
        "structured_data": [],
        "metadata": {}
    }

    # 1. Utilisation de Crawl4AI pour un Markdown propre
    async with AsyncWebCrawler(verbose=False) as crawler:
        result = await crawler.arun(url=url)
        
        if result.success:
            result_data["markdown_content"] = result.markdown
            result_data["metadata"] = result.metadata
            
            # 2. Utilisation de BeautifulSoup pour le JSON-LD (Données structurées)
            # On récupère le HTML brut pour isoler les balises <script type="application/ld+json">
            soup = BeautifulSoup(result.html, 'html.parser')
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            
            for script in json_ld_scripts:
                try:
                    # Nettoyage et chargement du JSON
                    clean_json = json.loads(script.string)
                    result_data["structured_data"].append(clean_json)
                except (json.JSONDecodeError, TypeError):
                    continue
        else:
            print(f"Erreur de crawl : {result.error_message}")

    return result_data

# --- TEST RAPIDE ---
if __name__ == "__main__":
    # Remplace par l'URL d'une PME locale pour tester
    test_url = "https://4ipgroup.com/" 
    
    data = asyncio.run(extract_pme_data(test_url))
    
    print(f"--- ANALYSE DE : {data['url']} ---")
    print(f"Nombre de caractères Markdown : {len(data['markdown_content'])}")
    print(f"Nombre d'objets JSON-LD trouvés : {len(data['structured_data'])}")
    print("\nExemple de données structurées :")
    #print(json.dumps(data['structured_data'][:1], indent=2, ensure_ascii=False))
    print(json.dumps(data, indent=2, ensure_ascii=False))