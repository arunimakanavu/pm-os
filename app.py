import streamlit as st
import os
import json
from datetime import datetime
from pathlib import Path

# Must be first Streamlit call
st.set_page_config(
    page_title="PM OS",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded"
)

import database as db
import rag
import agents

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------
db.init_db()
Path("data/uploads").mkdir(parents=True, exist_ok=True)
Path("data/chroma").mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg: #0c0c0f;
    --surface: #141417;
    --surface2: #1c1c21;
    --border: #2a2a32;
    --accent: #7c6af7;
    --accent2: #4ade80;
    --accent3: #fb923c;
    --accent4: #f472b6;
    --text: #e8e8f0;
    --muted: #6b6b80;
    --danger: #f87171;
}

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background: var(--bg);
    color: var(--text);
}

/* Hide default Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2rem; max-width: 100%; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

/* Logo */
.pm-logo {
    font-size: 1.4rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    color: var(--text);
    padding: 0.5rem 0 1.5rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1rem;
}
.pm-logo span { color: var(--accent); }

/* Nav buttons */
.stButton > button {
    background: transparent !important;
    border: 1px solid var(--border) !important;
    color: var(--muted) !important;
    border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    text-align: left !important;
    padding: 0.5rem 1rem !important;
    width: 100% !important;
    transition: all 0.15s ease !important;
    letter-spacing: 0.02em !important;
}
.stButton > button:hover {
    background: var(--surface2) !important;
    border-color: var(--accent) !important;
    color: var(--text) !important;
}

/* Cards */
.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 0.75rem;
    transition: border-color 0.15s;
}
.card:hover { border-color: var(--accent); }

.card-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 0.3rem;
}
.card-meta {
    font-size: 0.75rem;
    color: var(--muted);
    font-family: 'JetBrains Mono', monospace;
}

/* Status badges */
.badge {
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.badge-backlog { background: #1e1e2e; color: var(--muted); border: 1px solid var(--border); }
.badge-in_progress { background: #1a1a2e; color: var(--accent); border: 1px solid var(--accent); }
.badge-done { background: #0f2a1e; color: var(--accent2); border: 1px solid var(--accent2); }
.badge-high { background: #2a1a0e; color: var(--accent3); border: 1px solid var(--accent3); }
.badge-critical { background: #2a0e0e; color: var(--danger); border: 1px solid var(--danger); }
.badge-medium { background: #1e1e1e; color: #a0a0b0; border: 1px solid #3a3a4a; }
.badge-low { background: #1a1a1a; color: var(--muted); border: 1px solid #2a2a3a; }

/* Chat */
.chat-bubble-user {
    background: var(--accent);
    color: white;
    padding: 0.75rem 1rem;
    border-radius: 12px 12px 4px 12px;
    margin: 0.5rem 0;
    margin-left: 20%;
    font-size: 0.9rem;
    line-height: 1.5;
}
.chat-bubble-assistant {
    background: var(--surface2);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 0.75rem 1rem;
    border-radius: 12px 12px 12px 4px;
    margin: 0.5rem 0;
    margin-right: 15%;
    font-size: 0.9rem;
    line-height: 1.6;
}
.agent-tag {
    font-size: 0.65rem;
    font-family: 'JetBrains Mono', monospace;
    color: var(--accent);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.3rem;
}

/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(124, 106, 247, 0.15) !important;
}

/* Metrics */
.metric-box {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.2rem;
    text-align: center;
}
.metric-val {
    font-size: 2.2rem;
    font-weight: 800;
    color: var(--accent);
    line-height: 1;
    margin-bottom: 0.3rem;
}
.metric-label {
    font-size: 0.72rem;
    color: var(--muted);
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

/* Section headers */
.section-header {
    font-size: 0.7rem;
    font-weight: 700;
    color: var(--muted);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin: 1.5rem 0 0.75rem;
    font-family: 'JetBrains Mono', monospace;
}

/* File uploader */
[data-testid="stFileUploader"] {
    background: var(--surface) !important;
    border: 1px dashed var(--border) !important;
    border-radius: 12px !important;
}

/* PRD output */
.prd-output {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    font-family: 'Syne', sans-serif;
    line-height: 1.7;
    white-space: pre-wrap;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: var(--surface) !important;
    border-radius: 10px !important;
    border: 1px solid var(--border) !important;
    gap: 4px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--muted) !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.83rem !important;
    border-radius: 7px !important;
    border: none !important;
}
.stTabs [aria-selected="true"] {
    background: var(--accent) !important;
    color: white !important;
}

/* Divider */
hr { border-color: var(--border) !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "chat"
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "model_id" not in st.session_state:
    st.session_state.model_id = os.environ.get("PM_OS_MODEL", "microsoft/Phi-3-mini-4k-instruct")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="pm-logo">PM<span>OS</span> ⬡</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">Navigation</div>', unsafe_allow_html=True)
    pages = [
        ("💬", "Chat", "chat"),
        ("🗺️", "Roadmap", "roadmap"),
        ("📋", "Standup", "standup"),
        ("📄", "PRD Builder", "prd"),
        ("📚", "Knowledge Base", "kb"),
        ("📊", "Digest", "digest"),
    ]
    for icon, label, key in pages:
        if st.button(f"{icon}  {label}", key=f"nav_{key}"):
            st.session_state.page = key

    # Model selector
    st.markdown('<div class="section-header">Model</div>', unsafe_allow_html=True)
    model_choice = st.selectbox(
        "HuggingFace model",
        [
            "microsoft/Phi-3-mini-4k-instruct",
            "mistralai/Mistral-7B-Instruct-v0.3",
            "Qwen/Qwen2.5-3B-Instruct",
            "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        ],
        index=0,
        label_visibility="collapsed"
    )
    if model_choice != st.session_state.model_id:
        st.session_state.model_id = model_choice
        os.environ["PM_OS_MODEL"] = model_choice
        # Reset cached pipeline on model change
        import agents as _agents
        _agents._pipeline = None
        st.info("Model changed — will load on next message.")

    # Stats
    st.markdown('<div class="section-header">Quick Stats</div>', unsafe_allow_html=True)
    summary = db.get_roadmap_summary()
    total = sum(summary.values())
    doc_count = rag.get_doc_count()
    st.markdown(f"""
    <div style="font-family:'JetBrains Mono',monospace; font-size:0.78rem; color:var(--muted); line-height:2;">
    ◆ {total} features tracked<br>
    ◆ {summary.get('in_progress',0)} in progress<br>
    ◆ {doc_count} doc chunks indexed<br>
    ◆ {st.session_state.model_id.split('/')[-1]}
    </div>
    """, unsafe_allow_html=True)

page = st.session_state.page

# ---------------------------------------------------------------------------
# CHAT PAGE
# ---------------------------------------------------------------------------
if page == "chat":
    st.markdown('<div class="section-header">AI Assistant</div>', unsafe_allow_html=True)
    st.markdown("Talk to your PM OS. It routes to the right agent automatically.")

    # Force agent selector
    col1, col2 = st.columns([3, 1])
    with col2:
        force = st.selectbox("Force agent", ["auto", "roadmap", "standup", "prd", "query", "digest"],
                             label_visibility="collapsed")

    # Chat display
    chat_container = st.container()
    with chat_container:
        if not st.session_state.chat_messages:
            st.markdown("""
            <div style="text-align:center;padding:3rem 0;color:var(--muted);">
                <div style="font-size:2rem;margin-bottom:0.5rem;">⬡</div>
                <div style="font-size:0.9rem;">Ask about your roadmap, paste standup notes, or request a PRD draft.</div>
            </div>
            """, unsafe_allow_html=True)

        for msg in st.session_state.chat_messages:
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-bubble-user">{msg["content"]}</div>', unsafe_allow_html=True)
            else:
                agent_label = msg.get("agent", "")
                tag = f'<div class="agent-tag">▸ {agent_label} agent</div>' if agent_label else ""
                content = msg["content"].replace("\n", "<br>")
                st.markdown(f'<div class="chat-bubble-assistant">{tag}{content}</div>', unsafe_allow_html=True)

    # Input
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area("Message", placeholder="e.g. 'Add a dark mode feature to Q3' or paste standup notes...",
                                   height=80, label_visibility="collapsed")
        submitted = st.form_submit_button("Send ↵", use_container_width=True)

    if submitted and user_input.strip():
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        db.save_message("user", user_input)

        with st.spinner("Thinking..."):
            fa = None if force == "auto" else force
            history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_messages[:-1]]
            response, agent_used = agents.process_message(user_input, history, force_agent=fa)

        st.session_state.chat_messages.append({"role": "assistant", "content": response, "agent": agent_used})
        db.save_message("assistant", response, agent_used)
        st.rerun()

    if st.button("Clear chat", key="clear_chat"):
        st.session_state.chat_messages = []
        st.rerun()

# ---------------------------------------------------------------------------
# ROADMAP PAGE
# ---------------------------------------------------------------------------
elif page == "roadmap":
    st.markdown('<div class="section-header">Roadmap</div>', unsafe_allow_html=True)

    # Summary metrics
    summary = db.get_roadmap_summary()
    cols = st.columns(4)
    metrics = [
        ("Backlog", summary.get("backlog", 0), "#6b6b80"),
        ("In Progress", summary.get("in_progress", 0), "#7c6af7"),
        ("Done", summary.get("done", 0), "#4ade80"),
        ("Total", sum(summary.values()), "#e8e8f0"),
    ]
    for col, (label, val, color) in zip(cols, metrics):
        with col:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-val" style="color:{color};">{val}</div>
                <div class="metric-label">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")
    tabs = st.tabs(["All", "Backlog", "In Progress", "Done", "➕ Add Feature"])

    status_map = {"All": None, "Backlog": "backlog", "In Progress": "in_progress", "Done": "done"}

    for i, (tab_label, status) in enumerate(status_map.items()):
        with tabs[i]:
            features = db.get_features(status=status)
            if not features:
                st.markdown('<div style="color:var(--muted);padding:1rem 0;font-size:0.85rem;">No features here yet.</div>', unsafe_allow_html=True)
            for f in features:
                with st.container():
                    c1, c2, c3 = st.columns([5, 2, 1])
                    with c1:
                        status_badge = f.get("status", "backlog").replace(" ", "_")
                        priority_badge = f.get("priority", "medium")
                        st.markdown(f"""
                        <div class="card">
                            <div class="card-title">{f['title']}</div>
                            <div style="margin:0.4rem 0;">{f.get('description','')[:120]}</div>
                            <div style="margin-top:0.5rem;">
                                <span class="badge badge-{status_badge}">{f.get('status','backlog')}</span>
                                &nbsp;
                                <span class="badge badge-{priority_badge}">{priority_badge}</span>
                                &nbsp;
                                <span class="card-meta">{f.get('owner','') or 'No owner'} · {f.get('quarter','') or 'No quarter'}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    with c2:
                        new_status = st.selectbox("Status", ["backlog", "in_progress", "done"],
                                                   index=["backlog","in_progress","done"].index(f.get("status","backlog")),
                                                   key=f"status_{f['id']}", label_visibility="collapsed")
                        if new_status != f.get("status"):
                            db.update_feature(f["id"], status=new_status)
                            st.rerun()
                    with c3:
                        if st.button("✕", key=f"del_{f['id']}"):
                            db.delete_feature(f["id"])
                            st.rerun()

    with tabs[4]:
        with st.form("add_feature_form"):
            st.markdown('<div class="section-header">New Feature</div>', unsafe_allow_html=True)
            title = st.text_input("Title *", placeholder="e.g. Dark Mode Support")
            description = st.text_area("Description", placeholder="What does this feature do?", height=80)
            c1, c2, c3 = st.columns(3)
            with c1:
                status = st.selectbox("Status", ["backlog", "in_progress", "done"])
            with c2:
                priority = st.selectbox("Priority", ["low", "medium", "high", "critical"])
            with c3:
                quarter = st.text_input("Quarter", placeholder="Q3 2025")
            owner = st.text_input("Owner", placeholder="@name")
            if st.form_submit_button("Add to Roadmap", use_container_width=True):
                if title:
                    db.add_feature(title, description, status, priority, owner, quarter)
                    st.success(f"✅ '{title}' added!")
                    st.rerun()

# ---------------------------------------------------------------------------
# STANDUP PAGE
# ---------------------------------------------------------------------------
elif page == "standup":
    st.markdown('<div class="section-header">Standup Processor</div>', unsafe_allow_html=True)

    tabs = st.tabs(["Process Notes", "History"])

    with tabs[0]:
        with st.form("standup_form"):
            raw = st.text_area("Paste your raw standup notes",
                               placeholder="Finished the auth refactor. Working on the new onboarding flow. Blocked on design review for the dashboard.",
                               height=180)
            submitted = st.form_submit_button("Process Standup ↵", use_container_width=True)

        if submitted and raw.strip():
            with st.spinner("Processing..."):
                result = agents.standup_agent(raw)
            st.markdown("""<div class="section-header">Structured Output</div>""", unsafe_allow_html=True)
            st.markdown(f'<div class="card" style="white-space:pre-wrap;line-height:1.8;">{result}</div>', unsafe_allow_html=True)

    with tabs[1]:
        standups = db.get_standups(limit=10)
        if not standups:
            st.markdown('<div style="color:var(--muted);padding:1rem;font-size:0.85rem;">No standups recorded yet.</div>', unsafe_allow_html=True)
        for s in standups:
            with st.expander(f"📋 {s['date']}"):
                cols = st.columns(3)
                with cols[0]:
                    st.markdown("**Done**")
                    st.markdown(s.get("done", "—") or "—")
                with cols[1]:
                    st.markdown("**Doing**")
                    st.markdown(s.get("doing", "—") or "—")
                with cols[2]:
                    st.markdown("**Blocked**")
                    st.markdown(s.get("blocked", "—") or "—")

# ---------------------------------------------------------------------------
# PRD BUILDER PAGE
# ---------------------------------------------------------------------------
elif page == "prd":
    st.markdown('<div class="section-header">PRD Builder</div>', unsafe_allow_html=True)

    tabs = st.tabs(["Generate PRD", "Saved PRDs"])

    with tabs[0]:
        with st.form("prd_form"):
            title = st.text_input("Feature title", placeholder="e.g. Real-time Collaboration")
            description = st.text_area("Describe the feature",
                                       placeholder="Users should be able to co-edit documents simultaneously with live cursor presence and conflict resolution...",
                                       height=120)
            submitted = st.form_submit_button("Generate PRD ↵", use_container_width=True)

        if submitted and description.strip():
            with st.spinner("Drafting PRD..."):
                prd = agents.prd_agent(description, title)
            st.markdown('<div class="section-header">Generated PRD</div>', unsafe_allow_html=True)
            st.markdown(prd)
            st.download_button("⬇ Download PRD", prd, file_name=f"{title or 'prd'}_{datetime.now().strftime('%Y%m%d')}.md")

    with tabs[1]:
        prds = db.get_prds(limit=20)
        if not prds:
            st.markdown('<div style="color:var(--muted);padding:1rem;font-size:0.85rem;">No PRDs generated yet.</div>', unsafe_allow_html=True)
        for p in prds:
            with st.expander(f"📄 {p['title']} — {p['created_at'][:10]}"):
                st.markdown(p.get("full_draft", ""))
                st.download_button("⬇ Download", p.get("full_draft",""), file_name=f"{p['title']}.md", key=f"dl_prd_{p['id']}")

# ---------------------------------------------------------------------------
# KNOWLEDGE BASE PAGE
# ---------------------------------------------------------------------------
elif page == "kb":
    st.markdown('<div class="section-header">Knowledge Base</div>', unsafe_allow_html=True)
    st.markdown("Upload docs to ground AI responses in your actual product context.")

    tabs = st.tabs(["Upload", "Search", "Index"])

    with tabs[0]:
        uploaded = st.file_uploader(
            "Drop files here",
            type=["pdf", "docx", "txt", "md", "csv"],
            accept_multiple_files=True,
            label_visibility="collapsed"
        )

        if uploaded:
            for file in uploaded:
                with st.spinner(f"Ingesting {file.name}..."):
                    result = rag.ingest_file(file.read(), file.name)
                if result["success"]:
                    st.success(f"✅ **{file.name}** — {result['chunks']} chunks indexed as `{result['doc_type']}`")
                    with st.expander("Preview"):
                        st.text(result["preview"])
                else:
                    st.error(f"❌ {file.name}: {result['reason']}")

    with tabs[1]:
        query = st.text_input("Search your docs", placeholder="e.g. onboarding flow requirements")
        if query:
            with st.spinner("Searching..."):
                results = rag.retrieve(query, n_results=5)
            if results:
                for r in results:
                    meta = r["metadata"]
                    score = f"{(1 - r['distance']):.2f}" if r.get("distance") is not None else "—"
                    st.markdown(f"""
                    <div class="card">
                        <div class="card-meta">{meta.get('filename','?')} · {meta.get('doc_type','?')} · relevance {score}</div>
                        <div style="margin-top:0.5rem;font-size:0.85rem;line-height:1.6;">{r['text'][:400]}...</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown('<div style="color:var(--muted);">No results found.</div>', unsafe_allow_html=True)

    with tabs[2]:
        docs = rag.list_ingested_docs()
        count = rag.get_doc_count()
        st.markdown(f'<div class="card-meta">{count} total chunks across {len(docs)} documents</div>', unsafe_allow_html=True)
        if docs:
            for d in docs:
                st.markdown(f"""
                <div class="card">
                    <div class="card-title">{d['filename']}</div>
                    <span class="badge badge-medium">{d['doc_type']}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:var(--muted);padding:1rem;font-size:0.85rem;">No docs indexed yet.</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# DIGEST PAGE
# ---------------------------------------------------------------------------
elif page == "digest":
    st.markdown('<div class="section-header">Weekly Digest</div>', unsafe_allow_html=True)
    st.markdown("AI-generated summary of your product, roadmap, and team velocity.")

    if st.button("Generate Digest", use_container_width=False):
        with st.spinner("Generating digest..."):
            digest = agents.digest_agent()
        st.markdown("---")
        st.markdown(digest)
        st.download_button("⬇ Download Digest",
                           digest,
                           file_name=f"digest_{datetime.now().strftime('%Y%m%d')}.md")
    else:
        # Show last standups and roadmap snapshot
        st.markdown('<div class="section-header">Roadmap Snapshot</div>', unsafe_allow_html=True)
        summary = db.get_roadmap_summary()
        cols = st.columns(len(summary) or 1)
        for col, (k, v) in zip(cols, summary.items()):
            with col:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-val">{v}</div>
                    <div class="metric-label">{k}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-header">Recent Standups</div>', unsafe_allow_html=True)
        standups = db.get_standups(limit=5)
        for s in standups:
            st.markdown(f"""
            <div class="card">
                <div class="card-meta">{s['date']}</div>
                <div style="margin-top:0.4rem;font-size:0.85rem;">
                    <strong>Done:</strong> {(s.get('done') or '—')[:100]}<br>
                    <strong>Doing:</strong> {(s.get('doing') or '—')[:100]}
                </div>
            </div>""", unsafe_allow_html=True)
