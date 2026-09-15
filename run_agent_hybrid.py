import click
import json
import os
from typing import List, Dict, Any
from agent.graph_hybrid import app  # Import compiled graph

from dotenv import load_dotenv

load_dotenv()

@click.command()
@click.option('--batch', required=True, help='Path to input JSONL file')
@click.option('--out', required=True, help='Path to output JSONL file')
def run(batch, out):
    """
    Main entry point to run the Retail Analytics Copilot.
    Reads questions from --batch, runs the graph, and writes to --out.
    """
    print(f"🚀 Starting Retail Copilot...")
    print(f"📂 Reading from: {batch}")
    print(f"💾 Writing to: {out}")

    results = []
    
    if not os.path.exists(batch):
        print(f"Error: Input file '{batch}' not found.")
        return

    with open(batch, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    with open(out, 'w', encoding='utf-8') as f_out:
        for i, line in enumerate(lines):
            if not line.strip():
                continue
                
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                print(f"⚠️ Skipping invalid JSON line: {line[:50]}...")
                continue

            question_id = item['id']
            question_text = item['question']
            format_hint = item.get('format_hint', '') 
            
            print(f"\n[{i+1}/{len(lines)}] Processing ID: {question_id}")
            
            initial_state = {
                "question": question_text,
                "format_hint": format_hint, 
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
                final_state = app.invoke(initial_state)
                
                # Calculate Heuristic Confidence
                confidence = 0.5
                if final_state.get('sql_result') and not final_state.get('sql_error'):
                    confidence += 0.3
                if final_state.get('retrieved_docs'):
                    confidence += 0.1
                if final_state.get('retry_count', 0) > 0:
                    confidence -= 0.2
                confidence = max(0.0, min(1.0, confidence))

                output_record = {
                    "id": question_id,
                    "final_answer": final_state.get("final_answer", "Error"),
                    "sql": final_state.get("sql_query", ""),
                    "confidence": round(confidence, 2),
                    "explanation": final_state.get("explanation", "No explanation provided."),
                    "citations": final_state.get("citations", [])
                }
                
                f_out.write(json.dumps(output_record) + "\n")
                f_out.flush()
                
            except Exception as e:
                print(f"❌ Error processing {question_id}: {e}")
                error_record = {
                    "id": question_id,
                    "final_answer": "Error",
                    "sql": "",
                    "confidence": 0.0,
                    "explanation": str(e),
                    "citations": []
                }
                f_out.write(json.dumps(error_record) + "\n")

    print(f"\n✅ Done! Results saved to {out}")

if __name__ == '__main__':
    run()