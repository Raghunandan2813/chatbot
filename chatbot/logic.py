import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import streamlit as st
from langchain_community.chat_models import ChatOllama
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

# Using Ollama - no API key needed

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


llm = ChatOllama(
    model="mistral"
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

                # 1. Fast Path / Rule-based checks (No AI needed)
                intent = None
                if any(word in text for word in ["summarize", "summary", "report", "total", "analyze"]):
                    intent = "SUMMARY"
                elif any(word in text for word in ["show", "list", "view history", "expenses"]):
                    intent = "LIST"
                
                # 2. If not determined by rules, use AI to classify and extract in one go
                if not intent:
                    prompt = (
                        "Analyze this message and return a JSON object. "
                        "Determine the intent ('ADD', 'CHAT').\n"
                        "- 'ADD': User is describing a purchase or expense.\n"
                        "- 'CHAT': General conversation, questions, etc.\n\n"
                        "If intent is 'ADD', also extract: 'amount' (float), 'category' (string), 'date' (YYYY-MM-DD), 'note' (string).\n"
                        f"Today's date: {datetime.now().strftime('%Y-%m-%d')}\n"
                        f"Message: {user_input}\n"
                        "Return ONLY a JSON object with 'intent' and optionally 'amount', 'category', 'date', 'note'."
                    )
                    
                    chain = ChatPromptTemplate.from_template("{prompt}") | llm | JsonOutputParser()
                    try:
                        resp_data = await chain.ainvoke({"prompt": prompt})
                        intent = resp_data.get("intent", "CHAT").upper()
                    except Exception:
                        # Fallback if JSON parsing fails
                        resp = await llm.ainvoke(user_input)
                        return resp.content
                
                if intent == "SUMMARY":
                    return await session.call_tool("summarize", {"start_date": "2000-01-01", "end_date": "2100-12-31"})

                elif intent == "LIST":
                    return await session.call_tool("list_expenses", {"start_date": "2000-01-01", "end_date": "2100-12-31"})

                elif intent == "ADD":
                    if "resp_data" in locals() and resp_data.get("amount"):
                        result = await session.call_tool(
                            "add_expense",
                            {
                                "date": resp_data.get("date") or datetime.now().strftime("%Y-%m-%d"),
                                "amount": float(resp_data["amount"]),
                                "category": (resp_data.get("category") or "Other").strip().title(),
                                "note": resp_data.get("note") or user_input
                            }
                        )
                        st.cache_data.clear()
                        return f"✅ Added expense: ₹{resp_data['amount']} for {resp_data['category']}."
                    else:
                        response = await llm.ainvoke(user_input)
                        return response.content
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
