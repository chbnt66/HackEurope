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
        """Libère les ressources réseau associées à TavilyClient."""
        try:
            self.tavily.close()
        except Exception:
            pass

    def compute_coherence_score(self, site_markdown: str, tavily_results: list) -> float:
        """
        Calcule un score de cohérence (0 à 1) entre le contenu du site
        et ce que le web dit sur l'entreprise via Tavily.

        - Score proche de 1.0 (ex: 0.85) : le site et les sources externes concordent
          → LLM aura confiance → Trust Score élevé.
        - Score bas (ex: 0.30) : le site se présente différemment de son image web
          → risque de ne pas être recommandé par les LLM.
        """
        # Texte A : résumé du site (1000 premiers caractères)
        text_a = site_markdown[:1000]

        # Texte B : contenu agrégé des résultats Tavily
        text_b = " ".join([res['content'] for res in tavily_results[:5] if 'content' in res])

        if not text_b.strip():
            return 0.0

        # Encodage en vecteurs
        vector_a = self.embedding_model.encode(text_a, convert_to_tensor=True)
        vector_b = self.embedding_model.encode(text_b, convert_to_tensor=True)

        # Similarité cosinus
        cosine_score = util.pytorch_cos_sim(vector_a, vector_b)
        return round(cosine_score.item(), 4)

    def compute_comparison_score(self, site_markdown: str, company_name: str) -> Dict[str, Any]:
        """
        Trouve le meilleur acteur du secteur selon Tavily, puis calcule
        un score de similarité cosinus entre le contenu du client et
        ce que Tavily sait sur ce leader.

        Retourne un dict avec :
          - 'score'           : float (0 à 1)
          - 'best_competitor' : str  (nom/URL du leader trouvé)
          - 'best_content'    : str  (extrait utilisé pour la comparaison)
        """
        # Étape 1 : demander à Tavily quel est le meilleur du secteur
        sector_search = self.tavily.search(
            query=f"meilleur leader référence mondial secteur concurrent {company_name}",
            search_depth="advanced",
            max_results=5
        )
        competitor_results = sector_search.get("results", [])
        if not competitor_results:
            return {"score": 0.0, "best_competitor": "inconnu", "best_content": ""}

        # Étape 2 : prendre le contenu du 1er résultat (le + pertinent selon Tavily)
        best = competitor_results[0]
        best_name = best.get("title") or best.get("url", "inconnu")
        best_content = " ".join(
            [res["content"] for res in competitor_results[:3] if "content" in res]
        )

        if not best_content.strip():
            return {"score": 0.0, "best_competitor": best_name, "best_content": ""}

        # Étape 3 : similarité cosinus client vs leader
        text_client = site_markdown[:1000]
        vec_client = self.embedding_model.encode(text_client, convert_to_tensor=True)
        vec_best = self.embedding_model.encode(best_content, convert_to_tensor=True)
        score = util.pytorch_cos_sim(vec_client, vec_best)

        return {
            "score": round(score.item(), 4),
            "best_competitor": best_name,
            "best_content": best_content[:500]   # extrait court pour le rapport
        }

    async def generate_geo_report(self, site_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse les données et génère l'audit + le fichier llms.txt
        """

        company_name = site_data["metadata"].get("title", "cette entreprise")
        web_context = self.tavily.search(
            query=f"Réputation, services et avis sur {company_name}",
            search_depth="advanced"
        )

        # Calcul du score de cohérence entre le site et les sources web
        tavily_results = web_context.get("results", [])
        coherence_score = self.compute_coherence_score(
            site_data["markdown_content"],
            tavily_results
        )

        # Calcul du score de comparaison vs le meilleur du secteur
        comparison = self.compute_comparison_score(
            site_data["markdown_content"],
            company_name
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Tu es un expert en Generative Engine Optimization (GEO). 
            Ton rôle est d'analyser le contenu d'une PME pour maximiser ses chances d'être citée par des LLM.
            
            Tu dois produire deux choses :
            1. Un AUDIT : points forts, points faibles, et 5 conseils prioritaires.
            2. Un FICHIER LLMS.TXT : Un résumé ultra-condensé en Markdown structuré pour les robots IA.
            """),
            ("user", """Voici les données du site :
            URL: {url}
            DONNÉES STRUCTURÉES: {structured_data}
            CONTENU MARKDOWN: {markdown_content}
             
            DONNÉES EXTERNES (TAVILY):
            {web_results}

            SCORE DE COHÉRENCE (similarité cosinus entre le site et les sources web, de 0 à 1) : {coherence_score}
            Un score élevé (ex: 0.85) signifie que le site est cohérent avec sa réputation web → Trust Score élevé.
            Un score bas (ex: 0.30) signifie une incohérence forte → risque d'être ignoré ou mal cité par les LLM.
             
            SCORE DE COMPARAISON (similarité cosinus entre notre client et le meilleur du secteur selon Tavily) : {comparison_score}
            Leader de référence identifié par Tavily : {best_competitor}
            Extrait du contenu du leader : {best_content}
            Un score élevé signifie que le client est positionné de façon similaire au leader → bonne couverture sémantique.
            Un score bas signifie que le client manque les thèmes clés du secteur → lacunes à combler.
            
            Réponds au format JSON avec les clés suivantes : 
            'score', 'analyse_critique', 'conseils_top5', 'llms_txt_content', 'coherence_interpretation', 'comparison_interpretation'.""")
        ])

        chain = prompt | self.llm
        # On limite le markdown s'il est trop long pour économiser les tokens
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
                    question="Quels sont les services, l'expertise, les points forts et les informations clés de cette entreprise pour un LLM en deep research ?",
                    compression_model_name="compresr_v1"
                )
                llms_txt_compressed = compression_result.data.compressed_context
                report_dict["llms_txt_content"] = llms_txt_compressed
            llm_report_final = json.dumps(report_dict, ensure_ascii=False)
        except Exception:
            # Si la compression échoue ou le JSON est mal formé, on garde l'original
            llm_report_final = response.content

        return {
            "llm_report": llm_report_final,
            "coherence_score": coherence_score,
            "comparison_score": comparison["score"],
            "best_competitor": comparison["best_competitor"],
            "llms_txt_compressed": llms_txt_compressed
        }