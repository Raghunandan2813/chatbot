import streamlit as st

ULTRA_DARK_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
    .stApp {
        background-color: #020617;
        font-family: 'Inter', sans-serif;
        color: #94a3b8;
    }
    .header-container {
        background-color: #0f172a;
        padding: 30px 20px;
        margin-top: -60px;
        margin-bottom: 20px;
        text-align: center;
        color: #38bdf8;
        border-bottom: 1px solid #1e293b;
    }
    .header-title {
        font-size: 2.5rem;
        font-weight: 800;
        letter-spacing: -1px;
        margin: 0;
        color: #f8fafc;
    }
    .header-subtitle {
        font-size: 1rem;
        color: #64748b;
    }
    .metric-card {
        background-color: #0f172a;
        padding: 20px;
        border-radius: 20px;
        border: 1px solid #1e293b;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        text-align: center;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #64748b;
        font-weight: 600;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #38bdf8;
    }
    .metric-card.warning {
        border: 2px solid #f59e0b !important;
    }
    .metric-card.danger {
        border: 2px solid #ef4444 !important;
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.3) !important;
    }
    .status-text {
        font-size: 0.8rem;
        font-weight: 700;
        margin-top: 5px;
    }
    .status-text.warning { color: #f59e0b; }
    .status-text.danger { color: #ef4444; }
    
    section[data-testid="stSidebar"] {
        background-color: #020617 !important;
        color: #94a3b8 !important;
        border-right: 1px solid #1e293b;
    }
    section[data-testid="stSidebar"] .stMarkdown {
        color: #64748b !important;
    }
    .stChatMessage {
        background-color: #0f172a !important;
        border: 1px solid #1e293b;
        border-radius: 20px !important;
        padding: 20px !important;
        margin-bottom: 20px !important;
        color: #cbd5e1 !important;
    }
    .stChatMessage[data-testid="stChatMessageUser"] {
        background-color: #1e293b !important;
        border-left: 5px solid #38bdf8;
    }
    .stTable {
        border-radius: 15px;
        overflow: hidden;
        border: 1px solid #1e293b;
        color: #94a3b8;
    }
    
    /* Skeleton Shimmer Effect */
    @keyframes shimmer {
        0% { background-position: -468px 0; }
        100% { background-position: 468px 0; }
    }
    .skeleton {
        background: #1e293b;
        background-image: linear-gradient(to right, #1e293b 0%, #334155 20%, #1e293b 40%, #1e293b 100%);
        background-repeat: no-repeat;
        background-size: 800px 104px;
        display: inline-block;
        position: relative;
        animation: shimmer 1.5s infinite linear;
        border-radius: 10px;
        width: 100%;
        height: 100px;
    }
</style>
"""

def apply_styles():
    st.markdown(ULTRA_DARK_CSS, unsafe_allow_html=True)
