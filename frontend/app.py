import json
import streamlit as st
import requests

API_URL = "http://localhost:8000/audit"

st.set_page_config(page_title="GEO Auditor", page_icon="🔍", layout="wide")

st.title("🔍 GEO Auditor")
st.caption("Analysez le référencement IA de n'importe quel site web en quelques secondes.")

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

    # ── En-tête ──────────────────────────────────────────────────────────────
    st.success("Audit terminé !")
    st.markdown(f"**Site analysé :** {data.get('title', data['url'])}")
    st.markdown(f"`{data['url']}`")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Score GEO", f"{data.get('report', {}).get('score', '—')} / 100")
    col2.metric("Cohérence site ↔ web", data.get("coherence_score", "—"))
    col3.metric("Comparaison vs leader", data.get("comparison_score", "—"))
    col4.metric("Leader identifié", data.get("best_competitor", "—")[:30] + "…"
                if data.get("best_competitor") and len(data.get("best_competitor","")) > 30
                else data.get("best_competitor", "—"))

    # ── Parse du rapport Gemini ───────────────────────────────────────────────
    report = {}
    try:
        raw = data.get("llm_report", "")
        clean = raw.strip().lstrip("```json").rstrip("```").strip()
        report = json.loads(clean)
    except Exception:
        report = {}

    if not report:
        st.warning("Le rapport JSON n'a pas pu être parsé.")
        st.text(data.get("llm_report", ""))
        st.stop()

    # ── Analyse critique ─────────────────────────────────────────────────────
    with st.expander("📋 Analyse critique", expanded=True):
        st.markdown(report.get("analyse_critique", "—"))

    # ── Conseils Top 5 ───────────────────────────────────────────────────────
    with st.expander("💡 5 conseils prioritaires", expanded=True):
        for i, conseil in enumerate(report.get("conseils_top5", []), 1):
            st.markdown(f"**{i}.** {conseil}")

    # ── Interprétations des scores ───────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        with st.expander("📊 Interprétation cohérence"):
            st.markdown(report.get("coherence_interpretation", "—"))
    with col_b:
        with st.expander("🏆 Interprétation comparaison"):
            st.markdown(report.get("comparison_interpretation", "—"))

    # ── LLMS.TXT compressé ───────────────────────────────────────────────────
    with st.expander("📄 llms.txt compressé (prêt pour les LLM)"):
        llms_content = data.get("llms_txt_compressed") or report.get("llms_txt_content", "—")
        st.code(llms_content, language="markdown")
        st.download_button(
            label="⬇️ Télécharger llms.txt",
            data=llms_content,
            file_name="llms.txt",
            mime="text/plain"
        )
