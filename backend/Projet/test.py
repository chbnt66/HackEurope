import os 
import asyncio
import json
import sys
from dotenv import load_dotenv


# Load API keys from .env (never hardcoded here)
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

    # ── Step 1: Crawl ──────────────────────────────────────────────────────────────
    print("⏳ [1/3] Crawling site...")
    site_data = await extract_pme_data(TEST_URL)
    print(f"✅ Crawl complete:")
    print(f"   - Markdown characters : {len(site_data['markdown_content'])}")
    print(f"   - JSON-LD blocks      : {len(site_data['structured_data'])}")
    print(f"   - Detected title      : {site_data['metadata'].get('title', 'N/A')}")

    # ── Step 2: Coherence score (quick preview) ─────────────────────────────────
    print("⏳ [2/3] Computing coherence score (sentence-transformers)...")
    auditor = GEOAuditor()
    
    # Separate Tavily search just to display the score before the full report
    from tavily import TavilyClient
    import os
    tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    company_name = site_data["metadata"].get("title", TEST_URL)
    web_context = tavily.search(
        query=f"Reputation, services and reviews about {company_name}",
        search_depth="advanced"
    )
    tavily_results = web_context.get("results", [])
    coherence_score = auditor.compute_coherence_score(site_data["markdown_content"], tavily_results)
    
    # fermer la connexion Tavily provisoire
    try:
        tavily.close()
    except Exception:
        pass

    print(f"✅ Coherence score: {coherence_score:.4f}")
    if coherence_score >= 0.7:
        interpretation = "Strong site ↔ web agreement → High Trust Score"
    elif coherence_score >= 0.4:
        interpretation = "Moderate agreement → room for improvement"
    else:
        interpretation = "Weak agreement → web image inconsistent with site"
    print(f"   Interpretation        : {interpretation}")

    # ── Step 3: Full GEO report via Gemini ─────────────────────────────────────────────
    print("⏳ [3/3] Generating GEO report (Gemini)...")
    result = await auditor.generate_geo_report(site_data)
    print("✅ Report generated!\n")

    # close the client held in the auditor
    try:
        auditor.close()
    except Exception:
        pass

    print(f"{'─'*60}")
    print(f"  COHERENCE SCORE   : {result['coherence_score']}")
    print(f"  COMPARISON SCORE  : {result['comparison_score']}  (vs {result['best_competitor']})")
    print(f"{'─'*60}")
    print("  LLM REPORT:")
    print(f"{'─'*60}")

    # Try to pretty-print if the LLM returns JSON
    try:
        report_json = json.loads(result["llm_report"].strip("```json\n").strip("```"))
        print(json.dumps(report_json, indent=2, ensure_ascii=False))
    except (json.JSONDecodeError, AttributeError):
        print(result["llm_report"])

    if result.get("llms_txt_compressed"):
        print(f"\n{'─'*60}")
        print("  COMPRESSED LLMS.TXT (Compresr):")
        print(f"{'─'*60}")
        print(result["llms_txt_compressed"])

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    # ProactorEventLoop is required on Windows by Playwright/crawl4ai (subprocesses).
    # The "Fatal error on SSL transport / Event loop is closed" error is a known
    # Python 3.10/Windows bug: __del__ SSL callbacks are called after loop.close().
    # Filtered via a custom exception handler — the pipeline is 100% correct.
    def _silence_ssl_closed(loop, context):
        exc = context.get("exception")
        if isinstance(exc, (RuntimeError, AttributeError)) and "Event loop is closed" in str(exc):
            return  # silently ignored
        loop.default_exception_handler(context)

    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
    loop.set_exception_handler(_silence_ssl_closed)
    try:
        loop.run_until_complete(run_pipeline())
        loop.run_until_complete(asyncio.sleep(0.25))  # drain SSL callbacks
    finally:
        loop.close()
