import dspy
from dspy.teleprompt import BootstrapFewShot
from agent.dspy_signatures import TextToSQL
from agent.tools.sqlite_tool import SQLiteTool

# 1. Setup Local Model
lm = dspy.LM(model="ollama/phi3.5:3.8b-mini-instruct-q4_K_M", api_base="http://localhost:11434", temperature=0.0)
dspy.configure(lm=lm)
sql_tool = SQLiteTool()
schema = sql_tool.get_schema()

# 2. Golden Examples (Distilled from Gemini's Success)
train_examples = [
    # Q2: Top Category Summer 2017
    dspy.Example(
        question="During 'Summer Beverages 2017' as defined in the marketing calendar, which product category had the highest total quantity sold?",
        db_schema=schema,
        sql_query="SELECT cat.CategoryName, SUM(oi.Quantity) AS TotalQuantitySold FROM orders AS o JOIN order_items AS oi ON o.OrderID = oi.OrderID JOIN products AS p ON oi.ProductID = p.ProductID JOIN categories AS cat ON p.CategoryID = cat.CategoryID WHERE strftime('%Y-%m', o.OrderDate) IN ('2017-06', '2017-07', '2017-08') GROUP BY cat.CategoryName ORDER BY TotalQuantitySold DESC LIMIT 1;"
    ).with_inputs('question', 'db_schema'),

    # Q3: AOV Winter 2017
    dspy.Example(
        question="What was the Average Order Value during 'Winter Classics 2017'?",
        db_schema=schema,
        sql_query="SELECT ROUND(SUM(oi.UnitPrice * oi.Quantity * (1 - oi.Discount)) / COUNT(DISTINCT o.OrderID), 2) FROM orders o JOIN order_items oi ON o.OrderID = oi.OrderID WHERE o.OrderDate BETWEEN '2017-12-01' AND '2017-12-31';"
    ).with_inputs('question', 'db_schema'),

    # Q6: Best Margin
    dspy.Example(
        question="Who was the top customer by gross margin in 2017? Assume CostOfGoods is 70% of UnitPrice.",
        db_schema=schema,
        sql_query="SELECT c.CompanyName, ROUND(SUM(oi.UnitPrice * 0.3 * oi.Quantity * (1 - oi.Discount)), 2) AS total_gross_margin FROM customers AS c JOIN orders AS o ON c.CustomerID = o.CustomerID JOIN order_items AS oi ON o.OrderID = oi.OrderID WHERE strftime('%Y', o.OrderDate) = '2017' GROUP BY c.CustomerID, c.CompanyName ORDER BY total_gross_margin DESC LIMIT 1;"
    ).with_inputs('question', 'db_schema')
]

# 3. Run the Optimizer
print("🚀 Optimizing TextToSQL module with Golden Gemini Data... (Takes ~2 mins)")

teleprompter = BootstrapFewShot(metric=lambda x, y: True, max_bootstrapped_demos=3) 
optimized_sql_gen = teleprompter.compile(dspy.ChainOfThought(TextToSQL), trainset=train_examples)

# 4. Save
optimized_sql_gen.save("../agent/optimized_sql_module.json")
print("✅ Optimization complete! Saved to agent/optimized_sql_module.json")