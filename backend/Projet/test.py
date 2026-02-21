import os 
import asyncio
import json
import sys
from dotenv import load_dotenv


# Chargement des clés API depuis le .env (jamais hardcodées ici)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

from Crawler import extract_pme_data
from audit_engine import GEOAuditor

# ─── URL à tester ────────────────────────────────────────────────────────────
TEST_URL = "https://4ipgroup.com/"
# ─────────────────────────────────────────────────────────────────────────────

async def run_pipeline():
    print(f"\n{'='*60}")
    print(f"  PIPELINE GEO AUDIT")
    print(f"  URL : {TEST_URL}")
    print(f"{'='*60}\n")

    # ── Étape 1 : Crawl ──────────────────────────────────────────────────────
    print("⏳ [1/3] Crawl du site en cours...")
    site_data = await extract_pme_data(TEST_URL)
    print(f"✅ Crawl terminé :")
    print(f"   - Caractères Markdown  : {len(site_data['markdown_content'])}")
    print(f"   - Blocs JSON-LD        : {len(site_data['structured_data'])}")
    print(f"   - Titre détecté        : {site_data['metadata'].get('title', 'N/A')}")

    # ── Étape 2 : Score de cohérence (aperçu rapide) ─────────────────────────
    print("\n⏳ [2/3] Calcul du score de cohérence (sentence-transformers)...")
    auditor = GEOAuditor()
    
    # On fait une recherche Tavily séparée juste pour afficher le score avant le rapport
    from tavily import TavilyClient
    import os
    tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    company_name = site_data["metadata"].get("title", TEST_URL)
    web_context = tavily.search(
        query=f"Réputation, services et avis sur {company_name}",
        search_depth="advanced"
    )
    tavily_results = web_context.get("results", [])
    coherence_score = auditor.compute_coherence_score(site_data["markdown_content"], tavily_results)
    
    # fermer la connexion Tavily provisoire
    try:
        tavily.close()
    except Exception:
        pass

    print(f"✅ Score de cohérence : {coherence_score:.4f}")
    if coherence_score >= 0.7:
        interpretation = "Forte concordance site ↔ web → Trust Score élevé"
    elif coherence_score >= 0.4:
        interpretation = "Concordance modérée → marge d'amélioration"
    else:
        interpretation = "Faible concordance → image web incohérente avec le site"
    print(f"   Interprétation        : {interpretation}")

    # ── Étape 3 : Rapport GEO complet via Gemini ─────────────────────────────
    print("\n⏳ [3/3] Génération du rapport GEO (Gemini)...")
    result = await auditor.generate_geo_report(site_data)
    print("✅ Rapport généré !\n")

    # fermer le client conservé dans l'auditor
    try:
        auditor.close()
    except Exception:
        pass

    print(f"{'─'*60}")
    print(f"  SCORE DE COHÉRENCE  : {result['coherence_score']}")
    print(f"{'─'*60}")
    print("  RAPPORT LLM :")
    print(f"{'─'*60}")

    # Tentative de pretty-print si le LLM renvoie du JSON
    try:
        report_json = json.loads(result["llm_report"].strip("```json\n").strip("```"))
        print(json.dumps(report_json, indent=2, ensure_ascii=False))
    except (json.JSONDecodeError, AttributeError):
        print(result["llm_report"])

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    # ProactorEventLoop est requis sur Windows par Playwright/crawl4ai (subprocesses).
    # L'erreur "Fatal error on SSL transport / Event loop is closed" est un bug connu
    # Python 3.10/Windows : les __del__ SSL sont appelés après loop.close().
    # On la filtre via un exception handler personnalisé — la pipeline est 100% correcte.
    def _silence_ssl_closed(loop, context):
        exc = context.get("exception")
        if isinstance(exc, (RuntimeError, AttributeError)) and "Event loop is closed" in str(exc):
            return  # ignoré silencieusement
        loop.default_exception_handler(context)

    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
    loop.set_exception_handler(_silence_ssl_closed)
    try:
        loop.run_until_complete(run_pipeline())
        loop.run_until_complete(asyncio.sleep(0.25))  # laisse drainer les callbacks
    finally:
        loop.close()
