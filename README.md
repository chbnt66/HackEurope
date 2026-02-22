# GEO Auditor 🔍

**Built at HackEurope — Paris, France — 21–22 February 2026**

GEO Auditor is a full-stack AI-powered tool that analyzes any website's **Generative Engine Optimization (GEO)** score — i.e., how likely it is to be cited, summarized, or recommended by AI search tools like ChatGPT, Claude, Gemini, or Perplexity.

---

## 🚀 Features

- **Website Crawler** — Extracts clean Markdown content and structured JSON-LD data using [Crawl4AI](https://github.com/unclecode/crawl4ai) and BeautifulSoup
- **GEO Audit** — Analyzes content with Gemini 2.5 Flash via LangChain and produces:
  - A GEO score (0–100)
  - Critical analysis of the site
  - 5 priority recommendations
  - Coherence & comparison score interpretations
- **Coherence Score** — Cosine similarity between the site content and its web reputation (via Tavily + Sentence Transformers)
- **Comparison Score** — Cosine similarity between the site and the sector leader identified by Tavily
- **`llms.txt` Generation** — Auto-generates a compressed Markdown summary optimized for AI crawlers, using [Compresr](https://compresr.com)
- **SEO/AEO Optimizer** — Uses Claude (Anthropic) to rewrite content, structured data, and metadata for maximum AI visibility
- **Miro Mind Map Export** — Exports the full audit as a visual mind map on a Miro board (via REST API and MCP server)
- **Supabase Webhook Integration** — Supports async audit triggering via Supabase Database Webhooks
- **Streamlit Frontend** — Interactive web UI for running audits and visualizing results
- **Lovable Frontend** — Production-ready React frontend connected to the FastAPI backend

---

## 📁 Project Structure

```
HackEurope/
├── backend/
│   ├── api.py                  # FastAPI app — /audit, /audit/webhook, /miro/export
│   ├── improve_website.py      # Claude-powered SEO/AEO optimizer
│   ├── miro_mcp_server.py      # MCP server for Miro mind map export
│   └── Projet/
│       ├── audit_engine.py     # Core GEO audit logic (Gemini + Tavily + Compresr)
│       ├── Crawler.py          # Website crawler (Crawl4AI + BeautifulSoup)
│       └── test.py             # Standalone pipeline test script
├── frontend/
│   ├── app.py                  # Streamlit UI
│   └── miro_export.py          # Synchronous Miro export helper
├── environment.yml             # Conda environment definition
└── README.md
```

---

## ⚙️ Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-org/HackEurope.git
cd HackEurope
```

### 2. Create the Conda environment

```bash
conda env create -f environment.yml
conda activate geo_optimizer_hackathon
```

### 3. Install Playwright browsers (required by Crawl4AI)

```bash
playwright install
```

### 4. Configure environment variables

Create a `.env` file in `backend/Projet/`:

```env
# Google Gemini
GOOGLE_API_KEY=your_google_api_key

# Tavily (web search)
TAVILY_API_KEY=your_tavily_api_key

# Compresr (llms.txt compression)
COMPRESR_API_KEY=your_compresr_api_key

# Anthropic Claude (SEO optimizer)
CLAUDE_API=your_anthropic_api_key

# Miro (mind map export)
MIRO_ACCESS_TOKEN=your_miro_access_token

# Supabase (optional — for webhook integration)
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_supabase_service_key
```

---

## ▶️ Running the Application

### Start the FastAPI backend

```bash
cd backend
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

API available at: `http://localhost:8000`
Interactive docs: `http://localhost:8000/docs`

### Start the Streamlit frontend

```bash
cd frontend
streamlit run app.py
```

### Run the standalone test pipeline

```bash
cd backend/Projet
python test.py
```

### Expose the API publicly (for Supabase webhooks or Lovable frontend)

```bash
ngrok http 8000
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `POST` | `/audit` | Run a full GEO audit on a URL |
| `POST` | `/audit/webhook` | Supabase webhook trigger |
| `POST` | `/miro/export` | Export audit results to a Miro board |

### Example request

```bash
curl -X POST http://localhost:8000/audit \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### Example response

```json
{
  "url": "https://example.com",
  "title": "Example Company",
  "markdown_length": 4521,
  "json_ld_count": 2,
  "coherence_score": 0.7843,
  "comparison_score": 0.6120,
  "best_competitor": "Industry Leader Inc.",
  "llms_txt_compressed": "# Example Company\n...",
  "llm_report": "{\"score\": 68, \"critical_analysis\": \"...\", \"top5_recommendations\": [...]}"
}
```

---

## 🧠 How It Works

```
URL Input
  ↓
Crawl4AI → Markdown + JSON-LD extraction
  ↓
Tavily → External web reputation search
  ↓
Sentence Transformers → Coherence score (site vs. web)
Sentence Transformers → Comparison score (site vs. sector leader)
  ↓
Gemini 2.5 Flash (LangChain) → GEO audit report
  ↓
Compresr → Compressed llms.txt
  ↓
FastAPI response → Streamlit / Lovable / Supabase
```

---

## 📚 Tech Stack

| Layer | Technology |
|-------|------------|
| LLM (audit) | Google Gemini 2.5 Flash via LangChain |
| LLM (SEO optimizer) | Anthropic Claude Opus |
| Web search | Tavily |
| Embeddings | Sentence Transformers (`all-MiniLM-L6-v2`) |
| Crawler | Crawl4AI + BeautifulSoup |
| Compression | Compresr |
| Backend | FastAPI + Uvicorn |
| Database | Supabase (PostgreSQL) |
| Frontend (demo) | Streamlit |
| Frontend (prod) | Lovable (React) |
| Mind maps | Miro REST API + MCP Server |
| Tunneling | ngrok |

---

## 📝 License

Built during HackEurope 2026. All rights reserved.
