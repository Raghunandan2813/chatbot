import streamlit as st
import asyncio
import json
import csv
import io
from datetime import datetime
from styles import apply_styles
from logic import call_mcp, get_complete_data_sync, get_budget_analysis_sync

# -------------------------
# UI CONFIG
# -------------------------
st.set_page_config(page_title="FinAI | Smart Expense Tracker", page_icon="💳", layout="wide")
apply_styles()

# -------------------------
# UI HELPERS
# -------------------------
def render_message(response):
    if hasattr(response, 'content'):
        for item in response.content:
            if item.type == 'text':
                try:
                    data = json.loads(item.text)
                    if isinstance(data, list): st.table(data)
                    else: st.json(data)
                except: st.markdown(item.text)
            elif item.type == 'image':
                st.image(f"data:image/png;base64,{item.data}")
    elif isinstance(response, list):
        for item in response:
            if hasattr(item, 'text'): st.markdown(item.text)
            elif hasattr(item, 'data'): st.image(f"data:image/png;base64,{item.data}")
            else: st.write(item)
    else:
        st.markdown(str(response))

def convert_to_csv(data):
    if not data: return None
    output = io.StringIO()
    # Explicitly define fieldnames with capital letters for the CSV header
    fieldnames = ["Date", "Amount", "Category", "Subcategory", "Note"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for row in data:
        writer.writerow({
            "Date": row.get("date"),
            "Amount": row.get("amount"),
            "Category": row.get("category"),
            "Subcategory": row.get("subcategory"),
            "Note": row.get("note")
        })
    return output.getvalue()

# Dashboard Header
st.markdown("""
    <div class="header-container">
        <h1 class="header-title">BUDGET PLANNER DASHBOARD</h1>
        <p class="header-subtitle">Monthly Personal Budget Dashboard</p>
    </div>
    """, unsafe_allow_html=True)

# SKELETON PLACEHOLDER
st.subheader("🚨 Budget Watch")
metric_placeholder = st.empty()
with metric_placeholder.container():
    sk_col1, sk_col2, sk_col3 = st.columns(3)
    sk_col1.markdown('<div class="skeleton"></div>', unsafe_allow_html=True)
    sk_col2.markdown('<div class="skeleton"></div>', unsafe_allow_html=True)
    sk_col3.markdown('<div class="skeleton"></div>', unsafe_allow_html=True)

# FETCH DATA (CACHED)
all_data = get_complete_data_sync()
total_exp = sum(d['amount'] for d in all_data)
transaction_count = len(all_data)

# -------------------------
# SIDEBAR
# -------------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2454/2454282.png", width=60)
    st.title("FinAI")
    st.markdown("Your Smart Financial Co-pilot.")
    st.markdown("---")
    
    st.subheader("🗓️ Overview")
    st.metric("Total Expenses", f"₹{total_exp:,.0f}")
    st.metric("Transactions", transaction_count)
    
    st.markdown("---")
    st.subheader("🎯 Budget Limits")
    food_limit = st.number_input("Food Budget", value=5000)
    travel_limit = st.number_input("Travel Budget", value=3000)
    shopping_limit = st.number_input("Shopping Budget", value=10000)
    user_budgets = {"Food": food_limit, "Travel": travel_limit, "Shopping": shopping_limit}

    st.markdown("---")
    st.subheader("📥 Data Export")
    csv_data = convert_to_csv(all_data)
    if csv_data:
        st.download_button(label="Download CSV Report", data=csv_data, file_name=f"finai_expenses_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")

# -------------------------
# DASHBOARD METRICS (Real Data)
# -------------------------
analysis = get_budget_analysis_sync(all_data, user_budgets)

with metric_placeholder.container():
    cols = st.columns(len(analysis))
    for i, item in enumerate(analysis):
        with cols[i]:
            status_class = item['status']
            icon = "✅" if status_class == "safe" else "⚠️" if status_class == "warning" else "🚫"
            st.markdown(f"""
                <div class="metric-card {status_class}">
                    <div class="metric-label">{icon} {item['category']}</div>
                    <div class="metric-value">₹{item['spent']:,.0f}</div>
                    <div class="status-text {status_class}">
                        {item['pct']:.0f}% of ₹{item['limit']:,.0f}
                    </div>
                </div>
            """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# -------------------------
# CHAT INTERFACE
# -------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        render_message(message["content"])

if prompt := st.chat_input("What did you spend on?"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = asyncio.run(call_mcp(prompt))
            render_message(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    if isinstance(response, str) and "✅ Added" in response:
        st.rerun()