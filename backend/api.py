import os
import sys
import asyncio
import traceback
import concurrent.futures

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "Projet", ".env"))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY) if SUPABASE_URL and SUPABASE_SERVICE_KEY else None

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "Projet"))
from Crawler import extract_pme_data
from audit_engine import GEOAuditor

app = FastAPI(title="GEO Auditor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuditRequest(BaseModel):
    url: str


@app.get("/")
def root():
    return {"status": "GEO Auditor API is running"}


def _run_pipeline_in_thread(url: str) -> dict:
    """
    Runs the pipeline in a dedicated thread with its own ProactorEventLoop.
    This isolates Playwright (which needs ProactorEventLoop to spawn
    the browser) from the main uvicorn loop.
    """
    async def _pipeline():
        site_data = await extract_pme_data(url)
        if not site_data["markdown_content"]:
            raise ValueError("Unable to crawl this URL.")
        auditor = GEOAuditor()
        try:
            result = await auditor.generate_geo_report(site_data)
        finally:
            auditor.close()
        return site_data, result

    # Nouveau loop ProactorEventLoop dans ce thread
    loop = asyncio.ProactorEventLoop()
    asyncio.set_event_loop(loop)
    try:
        site_data, result = loop.run_until_complete(_pipeline())
        loop.run_until_complete(asyncio.sleep(0.25))  # drain SSL
    finally:
        loop.close()

    return {
        "url": url,
        "title": site_data["metadata"].get("title", ""),
        "markdown_length": len(site_data["markdown_content"]),
        "json_ld_count": len(site_data["structured_data"]),
        **result,
    }


@app.post("/audit")
async def run_audit(request: AuditRequest):
    """
    Runs the full pipeline in a separate thread to avoid conflicts
    between ProactorEventLoop (Playwright) and the uvicorn loop.
    """
    try:
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            result = await loop.run_in_executor(
                executor, _run_pipeline_in_thread, request.url
            )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        detail = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=detail)


# ── Supabase Webhook endpoint ─────────────────────────────────────────────────

def _process_supabase_audit(audit_id: str, url: str):
    """Processes an audit triggered by a Supabase webhook and updates the row."""
    if supabase:
        supabase.table("audits").update({"status": "processing"}).eq("id", audit_id).execute()
    try:
        result = _run_pipeline_in_thread(url)
        if supabase:
            # Parse score from llm_report if possible
            score = None
            try:
                import json
                raw = result.get("llm_report", "")
                clean = raw.strip().lstrip("```json").rstrip("```").strip()
                report = json.loads(clean)
                raw_score = report.get("score")
                if raw_score is not None:
                    raw_score = float(raw_score)
                    # score between 0 and 1 → bring to 100
                    score = int(raw_score * 100) if raw_score <= 1 else int(raw_score)
            except Exception:
                pass

            supabase.table("audits").update({
                "status": "done",
                "title": result.get("title"),
                "score": score,
                "coherence_score": str(result.get("coherence_score", "")),
                "comparison_score": str(result.get("comparison_score", "")),
                "best_competitor": result.get("best_competitor"),
                "llm_report": result.get("llm_report"),
                "updated_at": "now()",
            }).eq("id", audit_id).execute()
    except Exception as e:
        if supabase:
            supabase.table("audits").update({
                "status": "error",
                "llm_report": traceback.format_exc(),
                "updated_at": "now()",
            }).eq("id", audit_id).execute()


@app.post("/audit/webhook")
async def supabase_webhook(request: Request):
    """
    Endpoint called by the Supabase Database Webhook on INSERT
    into the `audits` table with status='pending'.
    """
    payload = await request.json()
    record = payload.get("record", {})
    audit_id = record.get("id")
    url = record.get("url")

    if not audit_id or not url:
        raise HTTPException(status_code=400, detail="Fields 'id' and 'url' required in the payload.")

    # Start processing in the background (does not block the webhook response)
    loop = asyncio.get_event_loop()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    loop.run_in_executor(executor, _process_supabase_audit, audit_id, url)

    return {"status": "processing", "id": audit_id}


# ── Miro Export endpoint ──────────────────────────────────────────────────────

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "frontend"))
from miro_export import export_to_miro as _export_to_miro


class MiroExportRequest(BaseModel):
    board_id: str
    company_name: str
    geo_score: int
    recommendations: list
    coherence_score: float = 0.0
    comparison_score: float = 0.0
    best_competitor: str = ""


@app.post("/miro/export")
def miro_export(request: MiroExportRequest):
    """
    Exports the GEO mind map to a Miro board.
    The MIRO_ACCESS_TOKEN is read from the .env on the server side.
    """
    try:
        msg = _export_to_miro(
            board_id=request.board_id,
            company_name=request.company_name,
            geo_score=request.geo_score,
            recommendations=request.recommendations,
            coherence_score=request.coherence_score,
            comparison_score=request.comparison_score,
            best_competitor=request.best_competitor,
        )
        return {"status": "ok", "message": msg}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
