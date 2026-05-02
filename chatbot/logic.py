import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# MCP
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

# -------------------------
# ENV SETUP
# -------------------------
load_dotenv()
import os

# ✅ Load API key safely
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("❌ GROQ_API_KEY not found. Set it in Streamlit secrets.")

print("API KEY LOADED:", api_key[:8])  # debug

# -------------------------
# CONFIG (Portable for Deployment)
# -------------------------
# Use environment variables or look for files relative to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)

# Default to sys.executable (current python) for the server
import sys
SERVER_PYTHON = os.getenv("SERVER_PYTHON", sys.executable)
# Look for main.py in chatbot folder or parent folder
if os.path.exists(os.path.join(BASE_DIR, "main.py")):
    SERVER_SCRIPT = os.path.join(BASE_DIR, "main.py")
else:
    SERVER_SCRIPT = os.getenv("SERVER_SCRIPT", os.path.join(PARENT_DIR, "expense-tracker", "main.py"))

# Initialize LLM


llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=api_key
)

async def extract_expense_details(user_input):
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = ChatPromptTemplate.from_template(
        "Extract expense details from the following message. "
        "Return ONLY a JSON object with these fields: 'amount' (float), 'category' (string), 'date' (YYYY-MM-DD), 'note' (string). "
        "If a field is missing, use null for amount/category/note. For date, use {today} if not mentioned. "
        "Message: {user_input}"
    )
    chain = prompt | llm | JsonOutputParser()
    try:
        return await chain.ainvoke({"user_input": user_input, "today": today})
    except Exception:
        return {"amount": None, "category": "Other", "date": today, "note": user_input}

async def call_mcp(user_input):
    server_params = StdioServerParameters(
        command=SERVER_PYTHON,
        args=[SERVER_SCRIPT],
        env=os.environ.copy()
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                text = user_input.lower()

                # Intent classification
                intent_prompt = (
                    "Classify user intent into ONE of these: \n"
                    "- 'ADD': User is describing a purchase or expense they just made.\n"
                    "- 'LIST': User explicitly asks to see, show, list, or view their transactions/expenses.\n"
                    "- 'SUMMARY': User asks for a summary, report, analysis, or graph of spending.\n"
                    "- 'CHAT': General greeting, questions about who you are, math, or anything else.\n\n"
                    f"Message: {user_input}\n\nIntent:"
                )
                intent_resp = await llm.ainvoke(intent_prompt)
                intent = intent_resp.content.strip().upper()

                # Overrides
                if any(word in text for word in ["summarize", "summary", "report", "total", "analyze"]):
                    intent = "SUMMARY"
                elif any(word in text for word in ["show", "list", "view history", "expenses"]):
                    if "ADD" not in intent:
                        intent = "LIST"

                if "ADD" in intent:
                    details = await extract_expense_details(user_input)
                    if details.get("amount"):
                        result = await session.call_tool(
                            "add_expense",
                            {
                                "date": details.get("date") or datetime.now().strftime("%Y-%m-%d"),
                                "amount": float(details["amount"]),
                                "category": (details.get("category") or "Other").strip().title(),
                                "note": details.get("note") or user_input
                            }
                        )
                        # Clear cache so dashboard refreshes instantly
                        st.cache_data.clear()
                        return f"✅ Added expense: ₹{details['amount']} for {details['category']}."
                    else:
                        response = await llm.ainvoke(user_input)
                        return response.content

                elif "SUMMARY" in intent:
                    return await session.call_tool("summarize", {"start_date": "2000-01-01", "end_date": "2100-12-31"})

                elif "LIST" in intent:
                    return await session.call_tool("list_expenses", {"start_date": "2000-01-01", "end_date": "2100-12-31"})

                else:
                    response = await llm.ainvoke(user_input)
                    return response.content

    except Exception as e:
        import traceback
        return f"❌ MCP Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"

async def get_dashboard_stats():
    server_params = StdioServerParameters(command=SERVER_PYTHON, args=[SERVER_SCRIPT], env=os.environ.copy())
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                res = await session.call_tool("list_expenses", {"start_date": "2000-01-01", "end_date": "2100-12-31"})
                data = json.loads(res.content[0].text) if hasattr(res, 'content') else []
                total = sum(d['amount'] for d in data)
                return total, len(data)
    except:
        return 0, 0

import streamlit as st

@st.cache_data(ttl=2, show_spinner=False) # Reduced to 2s for perfect sync
def get_complete_data_sync():
    """Sync wrapper for the async data fetcher to work with st.cache_data."""
    return asyncio.run(get_all_expenses_raw())

async def get_all_expenses_raw():
    server_params = StdioServerParameters(command=SERVER_PYTHON, args=[SERVER_SCRIPT], env=os.environ.copy())
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                res = await session.call_tool("list_expenses", {"start_date": "2000-01-01", "end_date": "2100-12-31"})
                return json.loads(res.content[0].text) if hasattr(res, 'content') else []
    except Exception as e:
        return []

def get_budget_analysis_sync(all_expenses, budgets):
    """Checks current spending against user-defined budgets (Sync)."""
    analysis = {}
    for exp in all_expenses:
        # Normalize category to Title Case
        cat = exp['category'].strip().title()
        analysis[cat] = analysis.get(cat, 0) + exp['amount']
    
    results = []
    for cat, limit in budgets.items():
        # Normalize budget key to Title Case
        norm_cat = cat.strip().title()
        spent = analysis.get(norm_cat, 0)
        pct = (spent / limit * 100) if limit > 0 else 0
        status = "safe"
        if pct >= 100: status = "danger"
        elif pct >= 80: status = "warning"
        results.append({"category": norm_cat, "spent": spent, "limit": limit, "pct": pct, "status": status})
    return results
