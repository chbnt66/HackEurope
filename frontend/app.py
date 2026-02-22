import json
import sys
import os
import streamlit as st
import requests
from dotenv import load_dotenv

# Load .env for MIRO_ACCESS_TOKEN
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "backend", "Projet", ".env"))

sys.path.insert(0, os.path.dirname(__file__))
from miro_export import export_to_miro

API_URL = "http://localhost:8000/audit"

st.set_page_config(page_title="GEO Auditor", page_icon="🔍", layout="wide")

st.title("🔍 GEO Auditor")
st.caption("Analyze the AI referencing of any website in seconds.")

# ── State initialization ─────────────────────────────────────────────────────
if "audit_data" not in st.session_state:
    st.session_state.audit_data = None
if "audit_report" not in st.session_state:
    st.session_state.audit_report = None
if "miro_board_id" not in st.session_state:
    st.session_state.miro_board_id = ""

# ── Launch form ──────────────────────────────────────────────────────────────
url_input = st.text_input("Site URL to audit", placeholder="https://example.com")

if st.button("Launch audit", type="primary", disabled=not url_input):
    with st.spinner("Crawling + analysis in progress... (30-60 seconds)"):
        try:
            response = requests.post(API_URL, json={"url": url_input}, timeout=120)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.ConnectionError:
            st.error("Unable to reach the API. Make sure the FastAPI server is running on localhost:8000.")
            st.stop()
        except requests.exceptions.HTTPError as e:
            try:
                detail = e.response.json().get("detail", str(e))
            except Exception:
                detail = e.response.text or str(e)
            st.error("API Error:")
            st.code(detail, language="text")
            st.stop()

    # Parse the report
    report = {}
    try:
        raw = data.get("llm_report", "")
        clean = raw.strip().lstrip("```json").rstrip("```").strip()
        report = json.loads(clean)
    except Exception:
        report = {}

    # Store in state to persist between reruns
    st.session_state.audit_data = data
    st.session_state.audit_report = report

# ── Affichage des résultats (depuis le state) ─────────────────────────────────
if st.session_state.audit_data:
    data = st.session_state.audit_data
    report = st.session_state.audit_report

    st.success("Audit complete!")
    st.markdown(f"**Analyzed site:** {data.get('title', data['url'])}")
    st.markdown(f"`{data['url']}`")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("GEO Score", f"{report.get('score', '—')} / 100")
    col2.metric("Site ↔ web coherence", data.get("coherence_score", "—"))
    col3.metric("Comparison vs leader", data.get("comparison_score", "—"))
    col4.metric("Identified leader",
                (data.get("best_competitor", "—")[:30] + "…")
                if data.get("best_competitor") and len(data.get("best_competitor", "")) > 30
                else data.get("best_competitor", "—"))

    if not report:
        st.warning("The JSON report could not be parsed.")
        st.text(data.get("llm_report", ""))
        st.stop()

    # ── Critical analysis ─────────────────────────────────────────────────────
    with st.expander("📋 Critical analysis", expanded=True):
        st.markdown(report.get("critical_analysis", "—"))

    # ── Top 5 recommendations ─────────────────────────────────────────────────
    with st.expander("💡 Top 5 recommendations", expanded=True):
        for i, conseil in enumerate(report.get("top5_recommendations", []), 1):
            st.markdown(f"**{i}.** {conseil}")

    # ── Score interpretations ─────────────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        with st.expander("📊 Coherence interpretation"):
            st.markdown(report.get("coherence_interpretation", "—"))
    with col_b:
        with st.expander("🏆 Comparison interpretation"):
            st.markdown(report.get("comparison_interpretation", "—"))

    # ── LLMS.TXT compressé ────────────────────────────────────────────────────
    with st.expander("📄 llms.txt compressé (prêt pour les LLM)"):
        llms_content = data.get("llms_txt_compressed") or report.get("llms_txt_content", "—")
        st.code(llms_content, language="markdown")
        st.download_button(
            label="⬇️ Download llms.txt",
            data=llms_content,
            file_name="llms.txt",
            mime="text/plain"
        )

    # ── Export Mind Map Miro ──────────────────────────────────────────────────
    st.divider()
    st.subheader("🧠 Exporter la Mind Map vers Miro")

    miro_token = os.environ.get("MIRO_ACCESS_TOKEN", "")
    if not miro_token or miro_token == "REMPLACER_PAR_TON_TOKEN_MIRO":
        st.warning("Add `MIRO_ACCESS_TOKEN=...` to your `.env` file to enable Miro export.")
    else:
        board_input = st.text_input(
            "Miro Board (ID or full URL)",
            placeholder="uXjVxxxx= or https://miro.com/app/board/uXjVxxxx=/",
            key="miro_board_input"
        )
        if st.button("Export mind map to Miro 🚀", disabled=not board_input):
            try:
                geo_score = report.get("score", 0)
                conseils = report.get("top5_recommendations", [])
                with st.spinner("Creating mind map on Miro..."):
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
                st.error(f"Miro error: {e}")

        # ── Embed Miro directly into Streamlit ──────────────────────────────
        embed_board_id = st.session_state.get("miro_board_id", "") or board_input
        if embed_board_id:
            # Extract raw ID if it's a URL
            raw_id = embed_board_id.strip()
            if "/board/" in raw_id:
                raw_id = raw_id.split("/board/")[1].split("/")[0].split("?")[0]

            embed_url = f"https://miro.com/app/live-embed/{raw_id}/?autoplay=yep"
            st.markdown("**Miro board preview:**")
            import streamlit.components.v1 as components
            components.iframe(embed_url, height=600, scrolling=True)
