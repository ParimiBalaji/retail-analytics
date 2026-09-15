import dspy

class Router(dspy.Signature):
    """
    Classify the question.
    Output 'sql' if it asks for numbers, data, or top lists.
    Output 'rag' if it asks for definitions, policies, or text.
    Output 'hybrid' if it needs definitions AND data.
    """
    question = dspy.InputField()
    classification = dspy.OutputField(desc="Must be one of: 'sql', 'rag', 'hybrid'")

class TextToSQL(dspy.Signature):
    """
    Write a SQLite query.
    - Tables: 'orders', 'order_items', 'products', 'customers'.
    - CRITICAL: Always JOIN 'products p' if you filter by Category or Product Name.
    - Date format: strftime('%Y-%m', OrderDate) = '1997-06'.
    - Revenue: SUM(UnitPrice * Quantity * (1 - Discount)).
    - Margin: SUM((UnitPrice * 0.3) * Quantity * (1 - Discount)).
    - LIMIT: If question asks for 'Top 3', use 'LIMIT 3'.
    - Syntax: Check parenthesis carefully. Example: ROUND(SUM(...), 2)
    """
    question = dspy.InputField()
    db_schema = dspy.InputField(desc="Schema info")
    sql_query = dspy.OutputField(desc="SQL query starting with SELECT")

class HybridSynthesizer(dspy.Signature):
    """
    Answer the question using the context.
    - Output strict JSON.
    - citations must be a list of strings.
    - final_answer must match the format_hint.
    """
    question = dspy.InputField()
    context = dspy.InputField()
    sql_query = dspy.InputField()
    sql_result = dspy.InputField()
    format_hint = dspy.InputField()
    
    final_answer = dspy.OutputField(desc="Value matching format_hint")
    explanation = dspy.OutputField(desc="Brief explanation")
    citations = dspy.OutputField(desc="List of strings like ['orders']")