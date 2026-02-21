"""
Helper appelé directement depuis Streamlit pour exporter la mind map vers Miro.
Réplique la logique du MCP server mais de façon synchrone (httpx sync).
"""
import os
import httpx

MIRO_API_URL = "https://api.miro.com/v2/boards"


def export_to_miro(
    board_id: str,
    company_name: str,
    geo_score: int,
    recommendations: list,
    coherence_score: float = 0.0,
    comparison_score: float = 0.0,
    best_competitor: str = "",
) -> str:
    token = os.environ.get("MIRO_ACCESS_TOKEN")
    if not token:
        raise ValueError("MIRO_ACCESS_TOKEN non défini dans le .env")

    # Extraction robuste de l'ID depuis tout format d'URL Miro
    # Formats acceptés :
    #   uXjVxxxx=
    #   https://miro.com/app/board/uXjVxxxx=/
    #   https://miro.com/app/board/uXjVxxxx=/?...
    raw = board_id.strip()
    if "miro.com" in raw:
        if "/board/" in raw:
            raw = raw.split("/board/")[1].split("/")[0].split("?")[0]
        else:
            raise ValueError(
                "URL Miro invalide. Format attendu : https://miro.com/app/board/uXjVxxxx=/\n"
                "Copiez l'URL depuis la barre d'adresse de votre board Miro."
            )
    board_id = raw
    if not board_id:
        raise ValueError("ID de board Miro vide. Vérifiez l'URL copiée.")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    if geo_score < 50:
        center_color = "#ff9d48"
    elif geo_score < 80:
        center_color = "#f5d128"
    else:
        center_color = "#2d9bf0"

    def create_shape(client, content, x, y, w, h, color, font_size=14):
        payload = {
            "data": {"shape": "round_rectangle", "content": content},
            "style": {"fillColor": color, "textAlign": "center", "fontSize": font_size},
            "position": {"x": x, "y": y},
            "geometry": {"width": w, "height": h},
        }
        r = client.post(f"{MIRO_API_URL}/{board_id}/shapes", headers=headers, json=payload)
        if r.status_code in [200, 201]:
            return r.json().get("id")
        raise RuntimeError(f"Miro shape error {r.status_code}: {r.text}")

    def create_connector(client, from_id, to_id):
        payload = {
            "startItem": {"id": from_id},
            "endItem": {"id": to_id},
            "style": {"strokeColor": "#aaaaaa", "strokeWidth": "2"},
        }
        client.post(f"{MIRO_API_URL}/{board_id}/connectors", headers=headers, json=payload)

    with httpx.Client(timeout=15) as client:
        # Nœud central
        center_id = create_shape(
            client,
            f"<strong>🌍 {company_name}</strong><br/>Score GEO : {geo_score}/100",
            x=0, y=0, w=320, h=100, color=center_color, font_size=18,
        )

        # Branche cohérence
        coh_id = create_shape(
            client,
            f"📊 Cohérence site ↔ web<br/>{coherence_score:.2f} / 1.0",
            x=-550, y=-150, w=260, h=80, color="#c9f0ff",
        )
        create_connector(client, center_id, coh_id)

        # Branche comparaison
        comp_id = create_shape(
            client,
            f"🏆 Vs leader secteur<br/>{comparison_score:.2f} / 1.0<br/>{best_competitor[:40]}",
            x=-550, y=50, w=260, h=100, color="#ffe4c9",
        )
        create_connector(client, center_id, comp_id)

        # Nœud conseils
        conseils_id = create_shape(
            client,
            "💡 Conseils prioritaires",
            x=500, y=0, w=220, h=60, color="#d5f692",
        )
        create_connector(client, center_id, conseils_id)

        # Sous-nœuds conseils
        y_base = -200
        for i, conseil in enumerate(recommendations[:5]):
            conseil_str = str(conseil) if not isinstance(conseil, str) else conseil
            ellipsis = "…" if len(conseil_str) > 120 else ""
            c_id = create_shape(
                client,
                f"#{i+1} {conseil_str[:120]}{ellipsis}",
                x=820, y=y_base + i * 130, w=340, h=110, color="#f0ffc9",
            )
            create_connector(client, conseils_id, c_id)

    return f"✅ Mind map exportée pour '{company_name}' (score {geo_score}/100)"
