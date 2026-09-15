import streamlit as st
import pandas as pd
import json
import sqlite3
import os
import plotly.express as px
from agent.graph_hybrid import app as agent_app
from agent.tools.sqlite_tool import SQLiteTool

st.set_page_config(
    page_title="Retail Analytics Copilot",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern glassmorphism aesthetic
st.markdown("""
<style>
    .main-header {
        font-size: 2.3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #94a3b8;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }
    .badge-sql {
        background-color: #3b82f6;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .badge-rag {
        background-color: #10b981;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .badge-hybrid {
        background-color: #8b5cf6;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.image("https://img.icons8.com/duotone/96/000000/shopping-cart.png", width=64)
st.sidebar.title("🛒 Retail Copilot")
st.sidebar.markdown("Local-first AI Agent with SQL & RAG")

db_path = "data/northwind.sqlite"
db_status = "🟢 Connected" if os.path.exists(db_path) else "🔴 Database Missing"
st.sidebar.caption(f"Database: `{db_path}` ({db_status})")

st.sidebar.divider()
st.sidebar.subheader("Quick Samples")
sample_questions = [
    "What is the return policy for unopened beverages?",
    "Top 3 products by revenue",
    "Top customer by margin in 2017?",
    "How many employees are located in the USA?",
    "What is the total revenue for 2017?"
]

selected_sample = st.sidebar.selectbox("Choose a sample query:", ["Select..."] + sample_questions)

st.markdown('<div class="main-header">Retail Analytics AI Copilot</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Hybrid RAG + SQL Natural Language Analytics Engine</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["💬 Copilot Query", "🗄️ Database Explorer & SQL Sandbox", "📊 Benchmark & Observability"])

# TAB 1: Copilot Query
with tab1:
    col_input, col_btn = st.columns([5, 1])
    
    default_text = selected_sample if selected_sample != "Select..." else ""
    user_query = col_input.text_input("Ask a business question:", value=default_text, placeholder="e.g. What is the return window for unopened beverages?")
    run_query = col_btn.button("Ask Copilot 🚀", use_container_width=True, type="primary")

    if run_query and user_query:
        with st.spinner("Analyzing question, running routing, SQL execution & synthesis..."):
            initial_state = {
                "question": user_query,
                "format_hint": "",
                "router_decision": "",
                "retrieved_docs": [],
                "sql_query": "",
                "sql_result": "",
                "sql_error": None,
                "retry_count": 0,
                "final_answer": "",
                "explanation": "",
                "citations": []
            }
            try:
                final_state = agent_app.invoke(initial_state)
                
                # Confidence Calculation
                confidence = 0.5
                if final_state.get('sql_result') and not final_state.get('sql_error'):
                    confidence += 0.3
                if final_state.get('retrieved_docs'):
                    confidence += 0.1
                if final_state.get('retry_count', 0) > 0:
                    confidence -= 0.2
                confidence = max(0.0, min(1.0, confidence))
                
                # Header results
                res_col1, res_col2, res_col3 = st.columns(3)
                
                decision = final_state.get("router_decision", "hybrid").upper()
                badge_class = f"badge-{decision.lower()}"
                
                res_col1.markdown(f"**Route**: <span class='{badge_class}'>{decision}</span>", unsafe_allow_html=True)
                res_col2.metric("Confidence Score", f"{confidence * 100:.0f}%")
                res_col3.metric("SQL Retries", final_state.get("retry_count", 0))

                st.divider()

                # Answer Section
                st.subheader("💡 Answer")
                ans = final_state.get("final_answer")
                if isinstance(ans, (dict, list)):
                    st.json(ans)
                else:
                    st.success(f"**{ans}**")

                if final_state.get("explanation"):
                    st.info(f"**Explanation**: {final_state.get('explanation')}")

                # SQL Section
                if final_state.get("sql_query"):
                    st.subheader("⚡ Generated SQL Query")
                    st.code(final_state.get("sql_query"), language="sql")
                    
                    sql_res = final_state.get("sql_result")
                    if isinstance(sql_res, list) and len(sql_res) > 0:
                        st.subheader("📋 Query Results Table")
                        df_res = pd.DataFrame(sql_res)
                        st.dataframe(df_res, use_container_width=True)

                        # Auto visualization if numeric columns exist
                        num_cols = df_res.select_dtypes(include=['number']).columns.tolist()
                        str_cols = df_res.select_dtypes(include=['object']).columns.tolist()
                        if num_cols and str_cols:
                            st.subheader("📈 Visual Analysis")
                            fig = px.bar(df_res, x=str_cols[0], y=num_cols[0], title=f"{num_cols[0]} by {str_cols[0]}", color_discrete_sequence=['#6366f1'])
                            st.plotly_chart(fig, use_container_width=True)

                # Citations & RAG Section
                if final_state.get("retrieved_docs"):
                    with st.expander("📚 Retrieved Documentation Chunks (RAG Context)"):
                        for doc in final_state["retrieved_docs"]:
                            st.markdown(f"**ID**: `{doc['id']}` (Score: `{doc.get('score', 0):.2f}`)")
                            st.caption(doc["content"])
                            st.divider()

                if final_state.get("citations"):
                    st.caption("🏷️ **Sources / Citations**: " + ", ".join([f"`{c}`" for c in final_state.get("citations")]))

            except Exception as e:
                st.error(f"Error executing agent query: {e}")

# TAB 2: Database Explorer & Sandbox
with tab2:
    st.subheader("🗄️ SQLite Database Explorer & Direct Query Sandbox")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table';", conn)['name'].tolist()
        
        col_t1, col_t2 = st.columns([1, 3])
        selected_table = col_t1.selectbox("Select Table:", tables)
        
        if selected_table:
            schema_df = pd.read_sql_query(f"PRAGMA table_info('{selected_table}');", conn)
            col_t1.markdown(f"**Schema for `{selected_table}`**")
            col_t1.dataframe(schema_df[['name', 'type']], use_container_width=True)
            
            sample_df = pd.read_sql_query(f"SELECT * FROM '{selected_table}' LIMIT 10;", conn)
            col_t2.markdown(f"**Sample Data (`{selected_table}` - Top 10 rows)**")
            col_t2.dataframe(sample_df, use_container_width=True)

        st.divider()
        st.subheader("💻 SQL Console Sandbox")
        custom_sql = st.text_area("Write SQL Query:", value="SELECT p.ProductName, ROUND(SUM(od.UnitPrice * od.Quantity), 2) as Revenue FROM 'Order Details' od JOIN Products p ON od.ProductID = p.ProductID GROUP BY p.ProductID ORDER BY Revenue DESC LIMIT 5;", height=100)
        
        if st.button("Execute Custom SQL ⚡"):
            try:
                res_df = pd.read_sql_query(custom_sql, conn)
                st.dataframe(res_df, use_container_width=True)
                st.caption(f"Returned {len(res_df)} rows")
            except Exception as sql_e:
                st.error(f"SQL Error: {sql_e}")
        conn.close()
    else:
        st.error(f"Database not found at {db_path}")

# TAB 3: Benchmark & Observability
with tab3:
    st.subheader("📊 Benchmark Suite & Observability")
    benchmark_file = "benchmark_dataset.jsonl"
    
    if os.path.exists(benchmark_file):
        with open(benchmark_file, "r", encoding="utf-8") as f:
            bench_lines = [json.loads(line) for line in f if line.strip()]
        
        st.write(f"Loaded **{len(bench_lines)} benchmark items** from `{benchmark_file}`.")
        st.dataframe(pd.DataFrame(bench_lines), use_container_width=True)
        
        output_file = "outputs_hybrid.jsonl"
        if os.path.exists(output_file):
            st.divider()
            st.subheader("🎯 Latest Benchmark Execution Results")
            with open(output_file, "r", encoding="utf-8") as f:
                out_lines = [json.loads(line) for line in f if line.strip()]
            
            out_df = pd.DataFrame(out_lines)
            st.dataframe(out_df, use_container_width=True)
            
            avg_conf = out_df['confidence'].mean() if 'confidence' in out_df else 0
            st.metric("Average System Confidence", f"{avg_conf * 100:.1f}%")
    else:
        st.warning(f"Benchmark dataset `{benchmark_file}` not found.")
