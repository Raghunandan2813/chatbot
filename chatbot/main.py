from fastmcp import FastMCP
import mcp.types as types
import os
import sqlite3
import aiosqlite
import io
import base64
import matplotlib
matplotlib.use('Agg')  # Set the backend to Agg for headless environments
import matplotlib.pyplot as plt

# -----------------------
# DB CONFIG
# -----------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "expenses.db")

print("DB Path:", DB_PATH)

mcp = FastMCP("ExpenseTracker")


# -----------------------
# INIT DB (RUN ON STARTUP, NOT DECORATOR)
# -----------------------
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)

        conn.commit()

    print("DB initialized successfully")


# IMPORTANT: call immediately (NOT on_event)
init_db()


# -----------------------
# ADD EXPENSE
# -----------------------
@mcp.tool()
async def add_expense(date: str, amount: float, category: str, subcategory: str = "", note: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            INSERT INTO expenses(date, amount, category, subcategory, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (date, amount, category, subcategory, note)
        )
        await db.commit()

        return {
            "status": "success",
            "id": cur.lastrowid
        }


# -----------------------
# LIST EXPENSES
# -----------------------
@mcp.tool()
async def list_expenses(start_date: str, end_date: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cur = await db.execute(
            """
            SELECT * FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        )

        rows = await cur.fetchall()
        return [dict(r) for r in rows]


# -----------------------
# SUMMARY
# -----------------------
@mcp.tool()
async def summarize(start_date: str, end_date: str, category: str | None = None):
    """
    Summarize expenses between two dates, providing a detailed analysis, 
    financial advice, and a visualization graph.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        query = """
            SELECT category, SUM(amount) as total, COUNT(*) as count
            FROM expenses
            WHERE date BETWEEN ? AND ?
        """
        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " GROUP BY category ORDER BY total DESC"

        cur = await db.execute(query, params)
        rows = await cur.fetchall()

        if not rows:
            return "No expenses found for the selected period."

        data = [dict(r) for r in rows]
        total_amount = sum(r["total"] for r in data)
        
        # Use the dashboard color palette
        NAVY_BG = "#020617"
        NAVY_CARD = "#0f172a"
        CYAN = "#38bdf8"
        INDIGO = "#6366f1"
        TEXT_GRAY = "#cbd5e1"

        # 1. GENERATE ADVICE (Dashboard Style)
        advice = f"### 📊 Allocation Summary\n"
        advice += f"**Total Spending: ₹{total_amount:,.2f}**\n\n"
        
        essential_categories = ["Food", "Transport", "Bills", "Health"]
        essential_total = sum(r["total"] for r in data if r["category"] in essential_categories)
        discretionary_total = total_amount - essential_total
        
        essential_pct = (essential_total / total_amount * 100) if total_amount > 0 else 0
        discretionary_pct = (discretionary_total / total_amount * 100) if total_amount > 0 else 0
        
        advice += f"**Actual Allocation Of The Income:**\n"
        advice += f"- **Essentials (Needs):** {essential_pct:.1f}%\n"
        advice += f"- **Discretionary (Wants):** {discretionary_pct:.1f}%\n\n"
        
        advice += "#### 💡 Strategic Solutions\n"
        if discretionary_pct > 40:
            advice += "⚠️ **High Discretionary Spending:** Your 'Wants' are above 40%. Consider cutting non-essential shopping.\n"
        else:
            advice += "✅ **Healthy Budget:** Your allocation is well-balanced!\n"

        # 2. GENERATE DASHBOARD GRAPH (Pie/Donut)
        plt.figure(figsize=(8, 8), facecolor=NAVY_BG)
        ax = plt.gca()
        ax.set_facecolor(NAVY_BG)
        
        categories = [r["category"] for r in data]
        amounts = [r["total"] for r in data]
        
        # Donut chart style - NO WHITE
        colors = [CYAN, INDIGO, "#4f46e5", "#1e293b", "#334155", "#475569"]
        wedges, texts, autotexts = plt.pie(
            amounts, 
            labels=categories, 
            autopct='%1.1f%%', 
            startangle=140, 
            colors=colors, 
            pctdistance=0.85,
            wedgeprops=dict(width=0.4, edgecolor=NAVY_BG)
        )
        
        # Style the labels to be readable on dark background
        plt.setp(autotexts, size=11, weight="bold", color=NAVY_BG) # Percentages inside
        plt.setp(texts, size=13, weight="bold", color=TEXT_GRAY) # Labels outside
        
        plt.title("Expense Summary\nActual Expenses Payment", fontsize=18, fontweight='bold', color=CYAN, pad=20)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=120)
        plt.close()
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')

        return [
            types.TextContent(type="text", text=advice),
            types.ImageContent(type="image", data=image_base64, mimeType="image/png")
        ]


# -----------------------
# RESOURCES
# -----------------------
@mcp.resource("expense:///categories", mime_type="application/json")
def categories():
    return {
        "categories": [
            "Food",
            "Transport",
            "Shopping",
            "Education",
            "Bills",
            "Health",
            "Other"
        ]
    }


# -----------------------
# RUN SERVER
# -----------------------
if __name__ == "__main__":
    mcp.run()