import sqlite3
import pandas as pd
from typing import List, Dict, Any, Union

class SQLiteTool:
    def __init__(self, db_path: str = "data/northwind.sqlite"):
        self.db_path = db_path
        self._init_views() # Auto-create simpler views

    def _init_views(self):
        """
        Creates lowercase views as suggested in the assignment.
        This helps the LLM avoid quoting errors (e.g. "Order Details").
        """
        views_sql = [
            "CREATE VIEW IF NOT EXISTS orders AS SELECT * FROM Orders;",
            "CREATE VIEW IF NOT EXISTS order_items AS SELECT * FROM \"Order Details\";",
            "CREATE VIEW IF NOT EXISTS products AS SELECT * FROM Products;",
            "CREATE VIEW IF NOT EXISTS customers AS SELECT * FROM Customers;"
        ]
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for sql in views_sql:
                    cursor.execute(sql)
                conn.commit()
        except Exception as e:
            print(f"Warning: Could not create views: {e}")

    def execute_query(self, query: str) -> Union[List[Dict[str, Any]], str]:
        """
        Executes a read-only SQL query and returns results.
        """
        forbidden = ["UPDATE", "DELETE", "DROP", "INSERT", "ALTER"]
        if any(cmd in query.upper() for cmd in forbidden):
            return f"Error: Unsafe query detected. Only SELECT is allowed."

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Use pandas for easy sql -> dict conversion
                df = pd.read_sql_query(query, conn)
                
                if df.empty:
                    return "Query executed successfully but returned no results."
                
                return df.to_dict(orient="records")
                
        except Exception as e:
            return f"SQL Error: {str(e)}"

    def get_schema(self) -> str:
        """
        Returns schema. We focus on the SIMPLIFIED VIEWS to help the LLM.
        """
        schema_str = []
        # ADD 'categories' HERE so it can look up "Beverages" -> ID 1
        target_tables = ['orders', 'order_items', 'products', 'customers', 'categories'] 
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for table in target_tables:
                    cursor.execute(f"PRAGMA table_info('{table}')")
                    columns = cursor.fetchall()
                    
                    # Col format: (cid, name, type, notnull, dflt, pk)
                    col_names = [col[1] for col in columns]
                    schema_str.append(f"Table: {table}")
                    schema_str.append(f"Columns: {', '.join(col_names)}")
                    schema_str.append("-" * 20)
                    
        except Exception as e:
            return f"Error retrieving schema: {str(e)}"
            
        return "\n".join(schema_str)