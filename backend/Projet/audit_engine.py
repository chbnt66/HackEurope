import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from tavily import TavilyClient
from typing import Dict, Any
from sentence_transformers import SentenceTransformer, util
from compresr import CompressionClient

class GEOAuditor:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0)
        self.tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.compresr = CompressionClient(api_key=os.environ["COMPRESR_API_KEY"])

    def close(self):
        """Releases network resources associated with TavilyClient."""
        try:
            self.tavily.close()
        except Exception:
            pass

    def compute_coherence_score(self, site_markdown: str, tavily_results: list) -> float:
        """
        Calculates a coherence score (0 to 1) between the site content
        and what the web says about the company via Tavily.

        - Score close to 1.0 (e.g. 0.85): site and external sources agree
          → LLM will be confident → High Trust Score.
        - Low score (e.g. 0.30): site presents itself differently from its web image
          → risk of not being recommended by LLMs.
        """
        # Text A: site summary (first 1000 characters)
        text_a = site_markdown[:1000]

        # Text B: aggregated content from Tavily results
        text_b = " ".join([res['content'] for res in tavily_results[:5] if 'content' in res])

        if not text_b.strip():
            return 0.0

        # Encode as vectors
        vector_a = self.embedding_model.encode(text_a, convert_to_tensor=True)
        vector_b = self.embedding_model.encode(text_b, convert_to_tensor=True)

        # Cosine similarity
        cosine_score = util.pytorch_cos_sim(vector_a, vector_b)
        return round(cosine_score.item(), 4)

    def compute_comparison_score(self, site_markdown: str, company_name: str) -> Dict[str, Any]:
        """
        Finds the best sector player according to Tavily, then calculates
        a cosine similarity score between the client content and
        what Tavily knows about that leader.

        Returns a dict with:
          - 'score'           : float (0 to 1)
          - 'best_competitor' : str  (name/URL of the found leader)
          - 'best_content'    : str  (excerpt used for comparison)
        """
        # Step 1: ask Tavily which is the best in the sector
        sector_search = self.tavily.search(
            query=f"best world leader reference sector competitor {company_name}",
            search_depth="advanced",
            max_results=5
        )
        competitor_results = sector_search.get("results", [])
        if not competitor_results:
            return {"score": 0.0, "best_competitor": "unknown", "best_content": ""}

        # Step 2: take the content of the 1st result (most relevant according to Tavily)
        best = competitor_results[0]
        best_name = best.get("title") or best.get("url", "unknown")
        best_content = " ".join(
            [res["content"] for res in competitor_results[:3] if "content" in res]
        )

        if not best_content.strip():
            return {"score": 0.0, "best_competitor": best_name, "best_content": ""}

        # Step 3: cosine similarity client vs leader
        text_client = site_markdown[:1000]
        vec_client = self.embedding_model.encode(text_client, convert_to_tensor=True)
        vec_best = self.embedding_model.encode(best_content, convert_to_tensor=True)
        score = util.pytorch_cos_sim(vec_client, vec_best)

        return {
            "score": round(score.item(), 4),
            "best_competitor": best_name,
            "best_content": best_content[:500]   # short excerpt for the report
        }

    async def generate_geo_report(self, site_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes the data and generates the audit + llms.txt file
        """

        company_name = site_data["metadata"].get("title", "cette entreprise")
        web_context = self.tavily.search(
            query=f"Reputation, services and reviews about {company_name}",
            search_depth="advanced"
        )

        # Calculate coherence score between site and web sources
        tavily_results = web_context.get("results", [])
        coherence_score = self.compute_coherence_score(
            site_data["markdown_content"],
            tavily_results
        )

        # Calculate comparison score vs best in sector
        comparison = self.compute_comparison_score(
            site_data["markdown_content"],
            company_name
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in Generative Engine Optimization (GEO).
            Your role is to analyze the content of a business to maximize its chances of being cited by LLMs.
            
            You must produce two things:
            1. An AUDIT: strengths, weaknesses, and 5 priority recommendations.
            2. A LLMS.TXT FILE: An ultra-condensed summary in structured Markdown for AI bots.
            """),
            ("user", """Here is the site data:
            URL: {url}
            STRUCTURED DATA: {structured_data}
            MARKDOWN CONTENT: {markdown_content}
             
            EXTERNAL DATA (TAVILY):
            {web_results}

            COHERENCE SCORE (cosine similarity between the site and web sources, from 0 to 1): {coherence_score}
            A high score (e.g. 0.85) means the site is consistent with its web reputation → High Trust Score.
            A low score (e.g. 0.30) means a strong inconsistency → risk of being ignored or misquoted by LLMs.
             
            COMPARISON SCORE (cosine similarity between our client and the best in the sector according to Tavily): {comparison_score}
            Reference leader identified by Tavily: {best_competitor}
            Excerpt from leader content: {best_content}
            A high score means the client is positioned similarly to the leader → good semantic coverage.
            A low score means the client is missing key industry topics → gaps to fill.
            
            Reply ONLY with a valid JSON object using EXACTLY these key names (do not rename or translate them).
            ALL string values must be written in English, regardless of the language of the site being analyzed.
            {{
              "score": <integer 0-100>,
              "critical_analysis": "<string: critical analysis of the site, in English>",
              "top5_recommendations": ["<recommendation 1>", "<recommendation 2>", "<recommendation 3>", "<recommendation 4>", "<recommendation 5>"],
              "llms_txt_content": "<string: condensed llms.txt in markdown, in English>",
              "coherence_interpretation": "<string, in English>",
              "comparison_interpretation": "<string, in English>"
            }}""")
        ])

        chain = prompt | self.llm
        # Limit markdown if too long to save tokens
        response = await chain.ainvoke({
            "url": site_data["url"],
            "structured_data": str(site_data["structured_data"]),
            "markdown_content": site_data["markdown_content"][:1000],
            "web_results": web_context,
            "coherence_score": coherence_score,
            "comparison_score": comparison["score"],
            "best_competitor": comparison["best_competitor"],
            "best_content": comparison["best_content"]
        })

        # Extraction et compression du llms_txt_content via Compresr
        llms_txt_compressed = None
        try:
            raw = response.content.strip().lstrip("```json").rstrip("```").strip()
            report_dict = json.loads(raw)
            llms_txt_raw = report_dict.get("llms_txt_content", "")
            if llms_txt_raw:
                compression_result = self.compresr.generate(
                    context=llms_txt_raw,
                    question="What are the services, expertise, strengths and key information of this company for an LLM in deep research?",
                    compression_model_name="compresr_v1"
                )
                llms_txt_compressed = compression_result.data.compressed_context
                report_dict["llms_txt_content"] = llms_txt_compressed
            llm_report_final = json.dumps(report_dict, ensure_ascii=False)
        except Exception:
            # If compression fails or JSON is malformed, keep the original
            llm_report_final = response.content

        return {
            "llm_report": llm_report_final,
            "coherence_score": coherence_score,
            "comparison_score": comparison["score"],
            "best_competitor": comparison["best_competitor"],
            "llms_txt_compressed": llms_txt_compressed
        }