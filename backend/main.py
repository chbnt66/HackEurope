from fastapi import FastAPI
from models import UrlWebsite, ExtractedWebPage
from services.improve_website import ImproveWebsite
from services.crawl import Crawler
from fastapi.middleware.cors import CORSMiddleware # For Supabase

app = FastAPI()

app.add_middleware(  # Special for SupaBase
    CORSMiddleware,
    allow_origins=["*"],  # fine for demo/testing
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/crawl") 
def web_crawl(data: UrlWebsite):
    crawler_url = Crawler(data.url)
    crawl_info_url = crawler_url.extract_pme_data() # 1min
    return {
        "message": "Web Crawler",
        "info_website": crawl_info_url
    }

@app.post("/suggestion") 
def suggestion(data: ExtractedWebPage):
    improve_website = ImproveWebsite(data.extracted_from_url)
    improvements = improve_website.optimize_seo_with_claude()
    return {
        "message": "Suggestion",
        "company": improvements
    }
