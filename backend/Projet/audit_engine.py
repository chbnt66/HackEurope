import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any

class GEOAuditor:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0)

    async def generate_geo_report(self, site_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyse les données et génère l'audit + le fichier llms.txt
        """
        
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
            
            Réponds au format JSON avec les clés suivantes : 
            'score', 'analyse_critique', 'conseils_top5', 'llms_txt_content'.""")
        ])

        chain = prompt | self.llm
        # On limite le markdown s'il est trop long pour économiser les tokens
        response = await chain.ainvoke({
            "url": site_data["url"],
            "structured_data": str(site_data["structured_data"]),
            "markdown_content": site_data["markdown_content"][:10000] 
        })
        
        return response.content