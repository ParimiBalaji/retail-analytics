import argparse
import sys
import json
from agent.graph_hybrid import app as agent_app

def run_interactive():
    print("==================================================")
    print("Retail Analytics Copilot - Interactive CLI Shell")
    print("Type your question and press Enter. Type 'exit' or 'quit' to exit.")
    print("==================================================\n")
    
    while True:
        try:
            user_input = input("Query > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("Goodbye!")
                break
                
            execute_single_query(user_input)
            print("-" * 50)
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"[ERROR] {e}\n")

def execute_single_query(question: str):
    initial_state = {
        "question": question,
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
    
    print("\nProcessing question...")
    final_state = agent_app.invoke(initial_state)
    
    print(f"\nFinal Answer : {final_state.get('final_answer')}")
    if final_state.get('sql_query'):
        print(f"SQL Query    : {final_state.get('sql_query')}")
    if final_state.get('explanation'):
        print(f"Explanation  : {final_state.get('explanation')}")
    if final_state.get('citations'):
        print(f"Citations    : {', '.join(final_state.get('citations'))}")

def main():
    parser = argparse.ArgumentParser(description="Retail Analytics Copilot CLI")
    parser.add_argument("--query", "-q", type=str, help="Single query mode")
    args = parser.parse_args()
    
    if args.query:
        execute_single_query(args.query)
    else:
        run_interactive()

if __name__ == "__main__":
    main()
