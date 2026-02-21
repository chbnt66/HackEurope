import os
import httpx
from mcp.server.fastmcp import FastMCP

# Initialisation du serveur MCP
# Ce serveur est destiné à être appelé par des IA (Claude, Cursor…)
# via le protocole MCP (stdio). Il n'est PAS lancé par uvicorn.
mcp = FastMCP("Miro GEO Audit Server")

MIRO_API_URL = "https://api.miro.com/v2/boards"


@mcp.tool()
async def export_audit_to_miro(
    board_id: str,
    company_name: str,
    geo_score: int,
    recommendations: list[str],
    coherence_score: float = 0.0,
    comparison_score: float = 0.0,
    best_competitor: str = "",
) -> str:
    """
    Exporte les résultats d'un audit GEO vers un tableau Miro sous forme de mind map.

    Args:
        board_id: ID ou URL du board Miro (ex: 'uXjVxxxx=')
        company_name: Nom de l'entreprise analysée
        geo_score: Score GEO global (0-100)
        recommendations: Liste des 5 conseils prioritaires
        coherence_score: Score de cohérence site ↔ web (0-1)
        comparison_score: Score de comparaison vs leader (0-1)
        best_competitor: Nom du leader identifié par Tavily
    """
    token = os.environ.get("MIRO_ACCESS_TOKEN")
    if not token:
        return "❌ MIRO_ACCESS_TOKEN non défini dans les variables d'environnement."

    # Extraction robuste de l'ID depuis tout format d'URL Miro
    raw = board_id.strip()
    if "miro.com" in raw:
        if "/board/" in raw:
            raw = raw.split("/board/")[1].split("/")[0].split("?")[0]
        else:
            return "❌ URL Miro invalide. Format attendu : https://miro.com/app/board/uXjVxxxx=/"
    board_id = raw
    if not board_id:
        return "❌ ID de board Miro vide."

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # Couleur du nœud central selon le score
    if geo_score < 50:
        center_color = "#ff9d48"
    elif geo_score < 80:
        center_color = "#f5d128"
    else:
        center_color = "#2d9bf0"

    created_ids = {}

    async with httpx.AsyncClient() as client:

        async def create_shape(content, x, y, w, h, color, font_size=14):
            payload = {
                "data": {"shape": "round_rectangle", "content": content},
                "style": {"fillColor": color, "textAlign": "center", "fontSize": font_size},
                "position": {"x": x, "y": y},
                "geometry": {"width": w, "height": h},
            }
            r = await client.post(f"{MIRO_API_URL}/{board_id}/shapes", headers=headers, json=payload)
            if r.status_code in [200, 201]:
                return r.json().get("id")
            return None

        async def create_connector(from_id, to_id):
            payload = {
                "startItem": {"id": from_id},
                "endItem": {"id": to_id},
                "style": {"strokeColor": "#aaaaaa", "strokeWidth": "2"},
            }
            await client.post(f"{MIRO_API_URL}/{board_id}/connectors", headers=headers, json=payload)

        # ── Nœud central ──────────────────────────────────────────────────────
        center_id = await create_shape(
            f"<strong>🌍 {company_name}</strong><br/>Score GEO : {geo_score}/100",
            x=0, y=0, w=320, h=100, color=center_color, font_size=18,
        )
        if not center_id:
            return "❌ Impossible de créer le nœud central sur Miro."

        # ── Branche Cohérence (gauche) ────────────────────────────────────────
        coh_id = await create_shape(
            f"📊 Cohérence site ↔ web<br/>{coherence_score:.2f} / 1.0",
            x=-550, y=-150, w=260, h=80, color="#c9f0ff",
        )
        if coh_id:
            await create_connector(center_id, coh_id)

        # ── Branche Comparaison (gauche bas) ──────────────────────────────────
        comp_id = await create_shape(
            f"🏆 Vs leader secteur<br/>{comparison_score:.2f} / 1.0<br/><small>{best_competitor[:40]}</small>",
            x=-550, y=50, w=260, h=100, color="#ffe4c9",
        )
        if comp_id:
            await create_connector(center_id, comp_id)

        # ── Branche Conseils (droite) ─────────────────────────────────────────
        conseils_node_id = await create_shape(
            "💡 Conseils prioritaires",
            x=500, y=0, w=220, h=60, color="#d5f692",
        )
        if conseils_node_id:
            await create_connector(center_id, conseils_node_id)

            y_base = -200
            for i, conseil in enumerate(recommendations[:5]):
                conseil_str = str(conseil) if not isinstance(conseil, str) else conseil
                ellipsis = "…" if len(conseil_str) > 120 else ""
                conseil_id = await create_shape(
                    f"#{i+1} {conseil_str[:120]}{ellipsis}",
                    x=820, y=y_base + i * 130, w=340, h=110, color="#f0ffc9",
                )
                if conseil_id:
                    await create_connector(conseils_node_id, conseil_id)

    return (
        f"✅ Mind map GEO exportée sur Miro pour '{company_name}' "
        f"(score {geo_score}/100) — {len(recommendations)} conseils ajoutés."
    )


if __name__ == "__main__":
    print("Démarrage du Serveur MCP Miro GEO sur stdio…")
    mcp.run()
