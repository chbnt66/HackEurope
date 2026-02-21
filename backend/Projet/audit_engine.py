import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from tavily import TavilyClient
from typing import Dict, Any
from sentence_transformers import SentenceTransformer, util

class GEOAuditor:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0)
        self.tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

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
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Tu es un expert en Generative Engine Optimization (GEO). 
            Ton rôle est d'analyser le contenu d'une PME pour maximiser ses chances d'être citée par des LLM.
            
            Tu dois produire deux choses :
            1. Un AUDIT : Score de 0 à 100, points forts, points faibles, et 5 conseils prioritaires.
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
            
            Réponds au format JSON avec les clés suivantes : 
            'score', 'analyse_critique', 'conseils_top5', 'llms_txt_content', 'coherence_interpretation'.""")
        ])

        chain = prompt | self.llm
        # On limite le markdown s'il est trop long pour économiser les tokens
        response = await chain.ainvoke({
            "url": site_data["url"],
            "structured_data": str(site_data["structured_data"]),
            "markdown_content": site_data["markdown_content"][:1000],
            "web_results": web_context,
            "coherence_score": coherence_score
        })

        return {
            "llm_report": response.content,
            "coherence_score": coherence_score
        }