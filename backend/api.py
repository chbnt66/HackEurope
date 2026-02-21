import os
import sys
import asyncio
import traceback
import concurrent.futures

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "Projet", ".env"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    Exécute la pipeline dans un thread dédié avec son propre ProactorEventLoop.
    Cela isole Playwright (qui a besoin de ProactorEventLoop pour spawner
    le navigateur) du loop principal d'uvicorn.
    """
    async def _pipeline():
        site_data = await extract_pme_data(url)
        if not site_data["markdown_content"]:
            raise ValueError("Impossible de crawler cette URL.")
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
    Lance la pipeline complète dans un thread séparé pour éviter les conflits
    entre ProactorEventLoop (Playwright) et le loop d'uvicorn.
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
