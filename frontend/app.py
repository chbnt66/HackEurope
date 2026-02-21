import json
import sys
import os
import streamlit as st
import requests
from dotenv import load_dotenv

# Charger le .env pour MIRO_ACCESS_TOKEN
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "backend", "Projet", ".env"))

sys.path.insert(0, os.path.dirname(__file__))
from miro_export import export_to_miro

API_URL = "http://localhost:8000/audit"

st.set_page_config(page_title="GEO Auditor", page_icon="🔍", layout="wide")

st.title("🔍 GEO Auditor")
st.caption("Analysez le référencement IA de n'importe quel site web en quelques secondes.")

# ── Initialisation du state ───────────────────────────────────────────────────
if "audit_data" not in st.session_state:
    st.session_state.audit_data = None
if "audit_report" not in st.session_state:
    st.session_state.audit_report = None
if "miro_board_id" not in st.session_state:
    st.session_state.miro_board_id = ""

# ── Formulaire de lancement ───────────────────────────────────────────────────
url_input = st.text_input("URL du site à auditer", placeholder="https://example.com")

if st.button("Lancer l'audit", type="primary", disabled=not url_input):
    with st.spinner("Crawl + analyse en cours… (30-60 secondes)"):
        try:
            response = requests.post(API_URL, json={"url": url_input}, timeout=120)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.ConnectionError:
            st.error("Impossible de joindre l'API. Vérifiez que le serveur FastAPI tourne sur localhost:8000.")
            st.stop()
        except requests.exceptions.HTTPError as e:
            try:
                detail = e.response.json().get("detail", str(e))
            except Exception:
                detail = e.response.text or str(e)
            st.error("Erreur API :")
            st.code(detail, language="text")
            st.stop()

    # Parse du rapport
    report = {}
    try:
        raw = data.get("llm_report", "")
        clean = raw.strip().lstrip("```json").rstrip("```").strip()
        report = json.loads(clean)
    except Exception:
        report = {}

    # Stockage dans le state pour persister entre les reruns
    st.session_state.audit_data = data
    st.session_state.audit_report = report

# ── Affichage des résultats (depuis le state) ─────────────────────────────────
if st.session_state.audit_data:
    data = st.session_state.audit_data
    report = st.session_state.audit_report

    st.success("Audit terminé !")
    st.markdown(f"**Site analysé :** {data.get('title', data['url'])}")
    st.markdown(f"`{data['url']}`")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Score GEO", f"{report.get('score', '—')} / 100")
    col2.metric("Cohérence site ↔ web", data.get("coherence_score", "—"))
    col3.metric("Comparaison vs leader", data.get("comparison_score", "—"))
    col4.metric("Leader identifié",
                (data.get("best_competitor", "—")[:30] + "…")
                if data.get("best_competitor") and len(data.get("best_competitor", "")) > 30
                else data.get("best_competitor", "—"))

    if not report:
        st.warning("Le rapport JSON n'a pas pu être parsé.")
        st.text(data.get("llm_report", ""))
        st.stop()

    # ── Analyse critique ──────────────────────────────────────────────────────
    with st.expander("📋 Analyse critique", expanded=True):
        st.markdown(report.get("analyse_critique", "—"))

    # ── Conseils Top 5 ────────────────────────────────────────────────────────
    with st.expander("💡 5 conseils prioritaires", expanded=True):
        for i, conseil in enumerate(report.get("conseils_top5", []), 1):
            st.markdown(f"**{i}.** {conseil}")

    # ── Interprétations des scores ────────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        with st.expander("📊 Interprétation cohérence"):
            st.markdown(report.get("coherence_interpretation", "—"))
    with col_b:
        with st.expander("🏆 Interprétation comparaison"):
            st.markdown(report.get("comparison_interpretation", "—"))

    # ── LLMS.TXT compressé ────────────────────────────────────────────────────
    with st.expander("📄 llms.txt compressé (prêt pour les LLM)"):
        llms_content = data.get("llms_txt_compressed") or report.get("llms_txt_content", "—")
        st.code(llms_content, language="markdown")
        st.download_button(
            label="⬇️ Télécharger llms.txt",
            data=llms_content,
            file_name="llms.txt",
            mime="text/plain"
        )

    # ── Export Mind Map Miro ──────────────────────────────────────────────────
    st.divider()
    st.subheader("🧠 Exporter la Mind Map vers Miro")

    miro_token = os.environ.get("MIRO_ACCESS_TOKEN", "")
    if not miro_token or miro_token == "REMPLACER_PAR_TON_TOKEN_MIRO":
        st.warning("Ajoutez `MIRO_ACCESS_TOKEN=...` dans votre fichier `.env` pour activer l'export Miro.")
    else:
        board_input = st.text_input(
            "Board Miro (ID ou URL complète)",
            placeholder="uXjVxxxx= ou https://miro.com/app/board/uXjVxxxx=/",
            key="miro_board_input"
        )
        if st.button("Exporter la mind map vers Miro 🚀", disabled=not board_input):
            try:
                geo_score = report.get("score", 0)
                conseils = report.get("conseils_top5", [])
                with st.spinner("Création de la mind map sur Miro..."):
                    msg = export_to_miro(
                        board_id=board_input,
                        company_name=data.get("title", data["url"]),
                        geo_score=int(geo_score) if str(geo_score).lstrip("-").isdigit() else 0,
                        recommendations=conseils,
                        coherence_score=float(data.get("coherence_score", 0)),
                        comparison_score=float(data.get("comparison_score", 0)),
                        best_competitor=data.get("best_competitor", ""),
                    )
                st.success(msg)
                # Stocker le board ID dans le state pour l'embed
                st.session_state.miro_board_id = board_input
            except Exception as e:
                st.error(f"Erreur Miro : {e}")

        # ── Embed Miro directement dans Streamlit ───────────────────────────
        embed_board_id = st.session_state.get("miro_board_id", "") or board_input
        if embed_board_id:
            # Extraire l'ID brut si c'est une URL
            raw_id = embed_board_id.strip()
            if "/board/" in raw_id:
                raw_id = raw_id.split("/board/")[1].split("/")[0].split("?")[0]

            embed_url = f"https://miro.com/app/live-embed/{raw_id}/?autoplay=yep"
            st.markdown("**Aperçu du board Miro :**")
            import streamlit.components.v1 as components
            components.iframe(embed_url, height=600, scrolling=True)
