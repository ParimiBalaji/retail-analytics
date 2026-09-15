from agent.graph_hybrid import app

def save_graph_syntax():
    print("Generating graph syntax...")
    try:
        # Get the Mermaid syntax string directly
        graph_syntax = app.get_graph().draw_mermaid()
        
        # Save to a text file
        output_file = "../assets/graph_architecture.mmd"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(graph_syntax)
            
        print(f"✅ Graph syntax saved to {output_file}")
        print("\n--- COPY THE CONTENT BELOW ---")
        print(graph_syntax)
        print("------------------------------")
        print("\nTo view this graph:")
        print("1. Open 'assets/graph_architecture.mmd' in VS Code (install 'Mermaid Preview' extension)")
        print("2. OR copy the text above and paste it into https://mermaid.live")
        
    except Exception as e:
        print(f"❌ Failed to generate graph: {e}")

if __name__ == "__main__":
    save_graph_syntax()