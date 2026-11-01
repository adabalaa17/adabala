import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import os

# Streamlit is synchronous, so using Motor (async) with repeated asyncio.run() calls
# causes "Event loop is closed" errors. We use standard PyMongo for the dashboard instead.
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "agent_orchestrator"

@st.cache_resource
def get_db_client():
    return MongoClient(MONGO_URI)

client = get_db_client()
db = client[DB_NAME]

st.set_page_config(page_title="CTO Dashboard - Agent Orchestrator", layout="wide")

st.title("👨‍💼 CTO Dashboard: Agent Orchestrator")
st.markdown("Manage your virtual company of AI agents. Review sprint meetings, assign roles, and approve plans.")

# --- Tab Layout ---
tab1, tab2, tab3 = st.tabs(["📊 Pending Reports & Approvals", "🤖 Agent Roles", "📂 History"])

with tab1:
    st.header("Latest Sprint Report")

    # Use sync PyMongo query
    latest_report = db.reports.find_one(sort=[("_id", -1)])

    if not latest_report:
        st.info("No reports generated yet. The agents are currently in their first sprint.")
    else:
        st.subheader(f"Report Date: {latest_report.get('timestamp', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')}")

        status = latest_report.get("status", "unknown")
        if status == "pending_cto_approval":
            st.warning("⚠️ Action Required: Agents are paused waiting for your approval and the next plan.")

            st.markdown("### Meeting Notes & Suggestions")
            for note in latest_report.get("meeting_notes", []):
                st.info(note)

            st.markdown("### Next 3-Day Plan Decision")
            with st.form("approval_form"):
                new_plan = st.text_area("Write the explicit plan for the next 3 days for the agents to follow:",
                                        value=f"Continuing from: {latest_report.get('previous_plan', '')}")
                submitted = st.form_submit_button("Approve & Start Next Sprint")

                if submitted:
                    # Update DB synchronously
                    db.reports.update_one(
                        {"_id": latest_report["_id"]},
                        {"$set": {"status": "approved", "new_plan_issued": new_plan}}
                    )
                    # We also update a global state document so the orchestrator knows to resume
                    db.orchestrator_state.update_one(
                        {"type": "global_state"},
                        {"$set": {"is_paused": False, "current_plan": new_plan}},
                        upsert=True
                    )
                    st.success("Plan approved! Agents have resumed their work.")
                    st.rerun()
        else:
            st.success("✅ The current sprint is active. No pending approvals required.")
            st.markdown(f"**Current Plan Executing:**\n {latest_report.get('new_plan_issued', 'N/A')}")

with tab2:
    st.header("Agent Configuration")
    st.markdown("Configure which agents are connected and their organizational roles.")

    # Static demo list. In a full app, this reads/writes to MongoDB.
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Agent 1 (CLI Command)", value="aider")
        st.selectbox("Agent 1 Role", ["Lead Developer", "QA Engineer", "Security Analyst", "Product Manager"], index=0)
    with col2:
        st.text_input("Agent 2 (CLI Command)", value="claude-code")
        st.selectbox("Agent 2 Role", ["Lead Developer", "QA Engineer", "Security Analyst", "Product Manager"], index=2)

    st.button("Save Configuration")

with tab3:
    st.header("Historical Reports")
    st.markdown("Past 3-day sprint meeting reports will appear here.")