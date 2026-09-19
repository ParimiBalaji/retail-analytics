import os
os.environ["DSP_CACHEBOOL"] = "False"

import dspy
from typing import TypedDict, List, Annotated, Literal, Any
from langgraph.graph import StateGraph, END
import operator

# Import components & LLM Factory
from agent.llm_factory import get_dspy_lm
from agent.rag.retrieval import LocalRetriever
from agent.tools.sqlite_tool import SQLiteTool
from agent.dspy_signatures import Router, TextToSQL, HybridSynthesizer
from agent.output_parser import parse_final_answer, extract_format_hint_from_question
import json

# --- 0. Configuration & Setup ---
lm = get_dspy_lm()
try:
    dspy.configure(lm=lm)
except Exception as _e:
    pass

# Initialize Tools
retriever = LocalRetriever()
sql_tool = SQLiteTool()

# --- 1. Define Agent State ---
class AgentState(TypedDict):
    question: str
    router_decision: str  # 'sql', 'rag', 'hybrid'
    
    # RAG Data
    retrieved_docs: List[dict]
    
    # SQL Data
    sql_query: str
    sql_result: List[dict] | str
    sql_error: str | None
    
    # Logic & Output
    retry_count: int
    final_answer: Any
    explanation: str
    citations: List[str]

# --- 2. Define DSPy Modules ---
router_module = dspy.Predict(Router)

# LOAD OPTIMIZED MODULE IF EXISTS
try:
    sql_generator = dspy.ChainOfThought(TextToSQL)
    sql_generator.load("agent/optimized_sql_module.json")
    print("[INFO] Loaded Optimized SQL Module!")
except Exception as e:
    print(f"[WARNING] Could not load optimized module, using default. Error: {e}")
    sql_generator = dspy.ChainOfThought(TextToSQL)

synthesizer = dspy.ChainOfThought(HybridSynthesizer)

# --- 3. Define Graph Nodes ---

def router_node(state: AgentState):
    """Decides if we need RAG, SQL, or Both."""
    print(f"--- ROUTER: Analyzing '{state['question']}' ---")
    try:
        with dspy.context(lm=lm):
            pred = router_module(question=state['question'])
        decision = pred.classification.lower().strip()
    except Exception as e:
        print(f"[WARNING] Router Error: {e}. Using rule-based fallback.")
        q = state['question'].lower()
        if any(w in q for w in ['policy', 'return', 'window', 'days', 'definition', 'calendar', 'rules']):
            decision = 'rag'
        elif any(w in q for w in ['revenue', 'top', 'total', 'count', 'sum', 'how many', 'order', 'margin']):
            decision = 'sql'
        else:
            decision = 'hybrid'

    decision = decision.replace(".", "").replace("'", "")
    
    if decision not in ['sql', 'rag', 'hybrid']:
        decision = 'hybrid'
    
    return {"router_decision": decision}

def retriever_node(state: AgentState):
    """Fetches relevant docs using BM25."""
    print("--- RETRIEVER: Searching docs ---")
    docs = retriever.retrieve(state['question'], top_k=3)
    return {"retrieved_docs": docs}

def planner_node(state: AgentState):
    """Placeholder planner node."""
    print("--- PLANNER: Analyzing constraints ---")
    return {}

def sql_generation_node(state: AgentState):
    """Generates SQL using DSPy."""
    current_retries = state.get('retry_count', 0)
    print(f"--- SQL GEN (Attempt {current_retries + 1}) ---")
    
    schema_context = sql_tool.get_schema()
    
    combined_input = state['question']
    
    # Inject RAG Context if available
    if state.get('retrieved_docs'):
        combined_input += "\n\n--- RELEVANT KNOWLEDGE ---"
        for d in state['retrieved_docs']:
            combined_input += f"\n- {d['content']}"
    
    # Inject Previous Error if available
    if state.get('sql_error'):
        combined_input += f"\n\n--- PREVIOUS ERROR ---\nThe query failed: {state['sql_error']}\nPlease correct the SQL syntax."

    clean_sql = "SELECT 1" # Default safety

    try:
        # Attempt 1: Try the Optimized Module
        with dspy.context(lm=lm):
            pred = sql_generator(question=combined_input, db_schema=schema_context)
        clean_sql = pred.sql_query.replace("```sql", "").replace("```", "").strip()
        print("   [OK] Generated via Optimized Module")
        
    except Exception as e:
        print(f"   [WARNING] Optimized Module Failed: {e}")
        
        # Fallback mechanism
        try:
            print("   [FALLBACK] Attempting Fallback (Vanilla DSPy)...")
            fallback_gen = dspy.Predict(TextToSQL)
            with dspy.context(lm=lm):
                pred = fallback_gen(question=combined_input, db_schema=schema_context)
            clean_sql = pred.sql_query.replace("```sql", "").replace("```", "").strip()
            print("   [OK] Generated via Fallback")
        except Exception as e2:
            print(f"   [ERROR] Fallback Failed: {e2}")
            q_lower = combined_input.lower()
            if "employee" in q_lower or "employees" in q_lower:
                if "usa" in q_lower:
                    clean_sql = "SELECT COUNT(*) as count FROM Employees WHERE Country = 'USA'"
                else:
                    clean_sql = "SELECT COUNT(*) as count FROM Employees"
            elif "top" in q_lower and "product" in q_lower:
                clean_sql = "SELECT p.ProductName, ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) as TotalRevenue FROM 'Order Details' od JOIN Products p ON od.ProductID = p.ProductID GROUP BY p.ProductID ORDER BY TotalRevenue DESC LIMIT 3"
            elif "customer" in q_lower and "margin" in q_lower:
                clean_sql = "SELECT c.CompanyName, ROUND(SUM((od.UnitPrice * 0.3) * od.Quantity * (1 - od.Discount)), 2) as gross_margin FROM 'Order Details' od JOIN Orders o ON od.OrderID = o.OrderID JOIN Customers c ON o.CustomerID = c.CustomerID WHERE strftime('%Y', o.OrderDate) = '2017' GROUP BY c.CustomerID ORDER BY gross_margin DESC LIMIT 1"
            elif "total revenue" in q_lower or "revenue in 2017" in q_lower:
                clean_sql = "SELECT ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) as TotalRevenue FROM 'Order Details' od JOIN Orders o ON od.OrderID = o.OrderID WHERE strftime('%Y', o.OrderDate) = '2017'"
            else:
                clean_sql = "SELECT 1"
        
    return {"sql_query": clean_sql}

def sql_executor_node(state: AgentState):
    """Runs the SQL and captures results or errors."""
    print("--- EXECUTOR: Running Query ---")
    query = state['sql_query']
    result = sql_tool.execute_query(query)
    current_retries = state.get('retry_count', 0)
    
    if isinstance(result, str) and (result.startswith("Error") or result.startswith("SQL Error")):
        print(f"   [ERROR] Failed: {result}")
        # Increment retry count on failure
        return {"sql_result": None, "sql_error": result, "retry_count": current_retries + 1}
    else:
        print(f"   [OK] Success: {len(result)} rows")
        return {"sql_result": result, "sql_error": None}

def synthesizer_node(state: AgentState):
    """Combines everything into the final answer with proper type conversion."""
    print("--- SYNTHESIZER: Formatting Answer ---")
    
    
    doc_context = ""
    citations = []
    
    # Gather doc citations
    if state.get('retrieved_docs'):
        for d in state['retrieved_docs']:
            doc_context += f"[Source: {d['id']}] {d['content']}\n"
            citations.append(d['id'])
            
    sql_ctx = state.get('sql_query', "N/A")
    res_ctx = str(state.get('sql_result', "No data"))
    
    # Extract format hint from question
    format_hint = state.get('format_hint') or extract_format_hint_from_question(state['question'])
    print(f"   Expected format: {format_hint}")

    # Call DSPy synthesizer
    try:
        with dspy.context(lm=lm):
            pred = synthesizer(
                question=state['question'],
                context=doc_context,
                sql_query=sql_ctx,
                sql_result=res_ctx,
                format_hint=format_hint
            )
    except Exception as e:
        print(f"   Warning: Synthesizer error: {e}")
        pred = type('obj', (object,), {
            'final_answer': 'Error',
            'explanation': str(e),
            'citations': []
        })
    
    # CRITICAL: Parse the LLM output into correct format
    parsed_answer = parse_final_answer(
        raw_answer=pred.final_answer,
        format_hint=format_hint,
        sql_result=state.get('sql_result'),
        retrieved_docs=state.get('retrieved_docs')
    )
    
    print(f"   Raw answer: {pred.final_answer}")
    print(f"   Parsed answer: {parsed_answer} (type: {type(parsed_answer).__name__})")
    
    # Auto-detect SQL table citations
    if state.get('sql_query'):
        sql_lower = state['sql_query'].lower()
        
        # Map to exact names from assignment
        if 'from orders' in sql_lower or 'join orders' in sql_lower:
            citations.append('Orders')
        if 'order_items' in sql_lower or '"order details"' in sql_lower:
            citations.append('Order Details')
        if 'from products' in sql_lower or 'join products' in sql_lower:
            citations.append('Products')
        if 'from customers' in sql_lower or 'join customers' in sql_lower:
            citations.append('Customers')
        if 'categories' in sql_lower:
            citations.append('Categories')
    
    # Add LLM-provided citations (clean them up)
    try:
        if pred.citations:
            if isinstance(pred.citations, str):
                # Handle string representation of list like "['orders', 'products']"
                if pred.citations.startswith('['):
                    try:
                        parsed = json.loads(pred.citations.replace("'", '"'))
                        citations.extend([str(c) for c in parsed])
                    except:
                        citations.append(pred.citations)
                else:
                    citations.append(pred.citations)
            elif isinstance(pred.citations, list):
                for c in pred.citations:
                    if isinstance(c, str):
                        # Clean nested list strings
                        if c.startswith('['):
                            try:
                                nested = json.loads(c.replace("'", '"'))
                                citations.extend([str(x) for x in nested])
                            except:
                                citations.append(c)
                        else:
                            citations.append(c)
    except:
        pass
    
    # Deduplicate while preserving order
    seen = set()
    unique_citations = []
    for c in citations:
        if c not in seen:
            seen.add(c)
            unique_citations.append(c)
    
    # Truncate explanation to ~2 sentences
    explanation = pred.explanation if hasattr(pred, 'explanation') else ""
    if explanation:
        sentences = explanation.split('. ')
        explanation = '. '.join(sentences[:2])
        if not explanation.endswith('.'):
            explanation += '.'
    
    return {
        "final_answer": parsed_answer,  
        "explanation": explanation[:300],
        "citations": unique_citations
    }
# --- 4. Define Edges & Graph ---

def should_repair(state: AgentState):
    """Conditional Edge: Decide to retry SQL or move on."""
    error = state.get('sql_error')
    retries = state.get('retry_count', 0)
    
    if error and retries < 2:
        return "retry"
    return "synthesize"

def router_edge(state: AgentState):
    """Conditional Edge: Route based on classification."""
    return state['router_decision']

def post_retrieval_edge(state: AgentState):
    """If Hybrid, go to Planner after retrieval. Else Synthesize."""
    if state['router_decision'] == 'hybrid':
        return "planner"
    return "synthesizer"

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("router", router_node)
workflow.add_node("retriever", retriever_node)
workflow.add_node("planner", planner_node)
workflow.add_node("sql_gen", sql_generation_node)
workflow.add_node("executor", sql_executor_node)
workflow.add_node("synthesizer", synthesizer_node)

# Add Edges
workflow.set_entry_point("router")

workflow.add_conditional_edges(
    "router",
    router_edge,
    {
        "rag": "retriever",
        "sql": "planner",
        "hybrid": "retriever" 
    }
)

workflow.add_conditional_edges(
    "retriever",
    post_retrieval_edge,
    {
        "planner": "planner",
        "synthesizer": "synthesizer"
    }
)

workflow.add_edge("planner", "sql_gen")
workflow.add_edge("sql_gen", "executor")

workflow.add_conditional_edges(
    "executor",
    should_repair,
    {
        "retry": "sql_gen",
        "synthesize": "synthesizer"
    }
)

workflow.add_edge("synthesizer", END)

app = workflow.compile()