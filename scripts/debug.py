import sqlite3
import pandas as pd

# Connect to DB
conn = sqlite3.connect("data/northwind.sqlite")

# 1. Get the Date Range
query = "SELECT MIN(OrderDate) as Start, MAX(OrderDate) as End FROM Orders"
print("--- Database Timeline ---")
print(pd.read_sql_query(query, conn))

# 2. Check for "Summer" months in the actual years
query2 = """
SELECT strftime('%Y', OrderDate) as Year, COUNT(*) as Orders 
FROM Orders 
GROUP BY Year
"""
print("\n--- Orders per Year ---")
print(pd.read_sql_query(query2, conn))

conn.close()