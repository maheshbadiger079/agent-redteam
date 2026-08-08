"""
Streamlit Web Form + Public Trust Report Dashboard
----------------------------------------------------
Free to run locally:   streamlit run webapp/streamlit_app.py
Free to host publicly: push to GitHub, deploy on Streamlit Community Cloud
                        (share.streamlit.io) — no cost, no credit card.

Two tabs:
  1. "Attack a Target" — lets any visitor point the harness at their own
     agent endpoint without cloning the repo.
  2. "Trust Report" — public aggregated dashboard of all runs logged so far.
"""

import sys
import os
import uuid
import json
import streamlit as st
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib
import harness.target_adapter
import harness.runner
import harness.classifier
import harness.storage
importlib.reload(harness.target_adapter)
importlib.reload(harness.runner)
importlib.reload(harness.classifier)
importlib.reload(harness.storage)

from harness.runner import load_attacks
from harness.target_adapter import TargetAgent
from harness.classifier import heuristic_classify
from harness import storage


st.set_page_config(
    page_title="Agent Red-Team & Safety Eval Harness",
    page_icon="🛡️",

    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .stApp {
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    .main-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 1.8rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 {
        color: #f8fafc;
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
    }
    .main-header p {
        color: #94a3b8;
        margin-top: 0.5rem;
        font-size: 1.05rem;
    }
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
    }
    .badge-safe {
        background-color: #dcfce7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
    }
    .badge-warn {
        background-color: #fef9c3;
        color: #854d0e;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
    }
    .badge-vuln {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>🛡️ Agent Red-Team & Safety Eval Harness</h1>
    <p>Attack AI agents on purpose — prompt injection, jailbreaks, tool misuse — and score how well they hold up against the OWASP LLM Top 10 standards.</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["⚔️ Attack a Target Endpoint", "📊 Public Trust Report & Analytics"])

with tab1:
    st.subheader("Point the harness at any AI agent endpoint")
    st.caption("No repo clone required. Your API keys stay safe in your browser session.")

    # Preset Quick Fill Buttons
    st.markdown("#### ⚡ Quick Presets")
    p_col1, p_col2, p_col3 = st.columns(3)
    with p_col1:
        if st.button("🤖 Sandboxed Demo Target (FastAPI)", use_container_width=True):
            st.session_state["target_url"] = "http://localhost:8000/chat"
            st.session_state["target_type"] = "http_custom"
            st.session_state["target_label"] = "demo-target-fastapi"
            st.session_state["api_key_header"] = "X-API-Key"
    with p_col2:
        if st.button("🦙 Local Ollama Model", use_container_width=True):
            st.session_state["target_url"] = "http://localhost:11434/v1"
            st.session_state["target_type"] = "openai_compatible"
            st.session_state["target_label"] = "local-ollama-llama3"
            st.session_state["model"] = "llama3.1"
    with p_col3:
        if st.button("⚡ Groq Cloud Endpoint", use_container_width=True):
            st.session_state["target_url"] = "https://api.groq.com/openai/v1"
            st.session_state["target_type"] = "openai_compatible"
            st.session_state["target_label"] = "groq-llama3-8b"
            st.session_state["model"] = "llama-3.1-8b-instant"

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        target_label = st.text_input(
            "Label for this target (shown on public dashboard)",
            value=st.session_state.get("target_label", "my-target-agent")
        )
        target_url = st.text_input(
            "Target Base URL",
            value=st.session_state.get("target_url", "http://localhost:8000/chat"),
            placeholder="http://localhost:8000/chat or https://api.groq.com/openai/v1"
        )
        target_type = st.selectbox(
            "Target Type",
            ["http_custom", "openai_compatible"],
            index=0 if st.session_state.get("target_type") == "http_custom" else 1
        )
        api_key_header = st.selectbox(
            "API Key Authentication Header",
            ["Authorization (Bearer)", "X-API-Key", "api-key"],
            index=1 if st.session_state.get("api_key_header") == "X-API-Key" else 0
        )

    with col2:
        model = st.text_input("Model Name (if applicable)", value=st.session_state.get("model", ""))
        api_key = st.text_input("API Key (optional, kept in-session only)", type="password")
        user_label = st.text_input("Your Name / Handle (for external users metric)", "")

        if target_type == "http_custom":
            with st.expander("⚙️ Advanced JSON Payload Options", expanded=False):
                req_field = st.text_input("Request Field Name", value="input")
                res_field = st.text_input("Response Field Name", value="output")
        else:
            req_field, res_field = "input", "output"

    st.markdown(" ")
    if st.button("🚀 Run Full OWASP Attack Suite", type="primary", use_container_width=True):
        if not target_url or not target_label:
            st.error("❌ Target URL and Target Label are required.")
        else:
            try:
                attacks = load_attacks()
            except Exception as ex:
                st.error(f"Failed to load attack library: {ex}")
                st.stop()

            header_choice = "X-API-Key" if "X-API-Key" in api_key_header else ("Authorization" if "Authorization" in api_key_header else api_key_header)

            os.environ["_SESSION_API_KEY"] = api_key or ""
            target = TargetAgent(
                base_url=target_url,
                api_key_env="_SESSION_API_KEY" if api_key else None,
                model=model or None,
                target_type=target_type,
                request_field=req_field,
                response_field=res_field,
                api_key_header=header_choice,
            )

            run_id = str(uuid.uuid4())[:8]
            progress = st.progress(0)
            status_text = st.empty()
            results_display = []

            for i, attack in enumerate(attacks):
                status_text.markdown(f"Running Attack **[{attack['id']}]** {attack['name']} ({attack['category']})...")
                response_text = target.send(attack["payload"])
                verdict = heuristic_classify(attack, response_text)
                storage.save_result(run_id, target_label, attack, verdict)
                
                results_display.append({
                    "Attack ID": attack["id"],
                    "Attack Name": attack["name"],
                    "OWASP Category": attack["category"],
                    "Severity": attack["severity"].upper(),
                    "Verdict": verdict.verdict,
                    "Matched Signals": ", ".join(verdict.matched_signals) if verdict.matched_signals else "None",
                    "Response Preview": verdict.raw_response[:120] + "..." if len(verdict.raw_response) > 120 else verdict.raw_response,
                })
                progress.progress((i + 1) / len(attacks))

            status_text.empty()
            if user_label:
                storage.log_external_user(user_label, target_label, run_id)

            st.success(f"✅ Evaluation Complete! Run ID: `{run_id}`")
            df = pd.DataFrame(results_display)

            def highlight_verdict(val):
                if val == "blocked":
                    return "background-color: #dcfce7; color: #166534; font-weight: bold;"
                elif val == "partial":
                    return "background-color: #fef9c3; color: #854d0e; font-weight: bold;"
                else:
                    return "background-color: #fee2e2; color: #991b1b; font-weight: bold;"

            st.dataframe(df.style.map(highlight_verdict, subset=["Verdict"]), use_container_width=True)

            counts = df["Verdict"].value_counts()
            c1, c2, c3 = st.columns(3)
            c1.metric("🟢 Blocked (Safe)", int(counts.get("blocked", 0)))
            c2.metric("🟡 Partial (Warning)", int(counts.get("partial", 0)))
            c3.metric("🔴 Succeeded (Vulnerabilities Found)", int(counts.get("succeeded", 0)))

with tab2:
    st.subheader("Aggregated Trust Report & Security Analytics")
    st.caption("Live tracking across all external developers and target agents evaluated by this harness.")

    stats = storage.summary_stats()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("👥 External Users", stats["external_users"])
    m2.metric("🤖 Distinct Agents Tested", stats["distinct_agents"])
    m3.metric("🎯 Total Attack Attempts", stats["total_attack_attempts"])
    m4.metric("🚨 Vulnerabilities Found", stats["vulnerabilities_found"])

    st.markdown("---")

    col_left, col_right = st.columns([1, 1])

    all_rows = storage.all_results()
    if all_rows:
        df_all = pd.DataFrame(all_rows)

        with col_left:
            st.markdown("### 📊 Failure Category Breakdown")
            vuln_df = df_all[df_all["verdict"] == "succeeded"]
            if not vuln_df.empty:
                cat_counts = vuln_df["category"].value_counts()
                st.bar_chart(cat_counts)
            else:
                st.info("No vulnerabilities detected across recorded runs yet!")

        with col_right:
            st.markdown("### 🛡️ Overall Verdict Distribution")
            verdict_counts = df_all["verdict"].value_counts()
            st.bar_chart(verdict_counts)

        st.markdown("### 📜 Complete Evaluation History")

        # Filters
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            selected_target = st.selectbox("Filter by Target Label", ["All"] + list(df_all["target_label"].unique()))
        with filter_col2:
            selected_verdict = st.selectbox("Filter by Verdict", ["All", "blocked", "partial", "succeeded"])

        filtered_df = df_all.copy()
        if selected_target != "All":
            filtered_df = filtered_df[filtered_df["target_label"] == selected_target]
        if selected_verdict != "All":
            filtered_df = filtered_df[filtered_df["verdict"] == selected_verdict]

        st.dataframe(
            filtered_df[["run_id", "target_label", "category", "severity", "verdict", "matched_signals"]],
            use_container_width=True
        )

        # Export Options
        st.markdown("### 📥 Download Trust Report")
        ex1, ex2 = st.columns(2)
        with ex1:
            json_str = json.dumps(stats, indent=2)
            st.download_button("Download Trust Report (JSON)", json_str, file_name="trust_report.json", mime="application/json")
        with ex2:
            csv_str = df_all.to_csv(index=False)
            st.download_button("Download All Evaluation Log (CSV)", csv_str, file_name="redteam_eval_log.csv", mime="text/csv")
    else:
        st.info("No runs logged yet. Execute an attack suite in Tab 1 to record initial benchmark metrics.")

