import json
import re
from typing import Any

def parse_final_answer(raw_answer: str, format_hint: str, sql_result: Any, retrieved_docs: Any = None) -> Any:
    """
    Parse the LLM's raw text output into the correct format.
    Falls back to SQL result or retrieved RAG docs if parsing fails.
    """
    
    # Clean the answer
    answer = str(raw_answer).strip()
    
    # Handle "int" format
    if format_hint == "int":
        # Try parsing from answer text if not an Error
        if answer.lower() != "error":
            match = re.search(r'\d+', answer)
            if match:
                return int(match.group())
        
        # Fallback 1: check SQL result
        if isinstance(sql_result, list) and len(sql_result) > 0:
            first_val = list(sql_result[0].values())[0]
            if first_val is not None and str(first_val).isdigit():
                return int(first_val)

        # Fallback 2: check RAG docs for numbers (e.g. '14 days')
        if retrieved_docs and isinstance(retrieved_docs, list):
            for doc in retrieved_docs:
                content = doc.get('content', '')
                num_match = re.search(r'(\d+)\s*(days?|hours?|weeks?|months?|items?)', content, re.IGNORECASE)
                if num_match:
                    return int(num_match.group(1))
                num_match_generic = re.search(r'\b\d+\b', content)
                if num_match_generic:
                    return int(num_match_generic.group(0))

        return 0
    
    # Handle "float" format
    if format_hint == "float":
        if answer.lower() != "error":
            match = re.search(r'\d+\.?\d*', answer)
            if match:
                return round(float(match.group()), 2)
        
        # Fallback: SQL result
        if isinstance(sql_result, list) and len(sql_result) > 0:
            first_val = list(sql_result[0].values())[0]
            if first_val is not None:
                try:
                    return round(float(first_val), 2)
                except ValueError:
                    pass
        return 0.0
    
    # Handle list format FIRST (before dict) to avoid confusion
    if format_hint.startswith("list"):
        # Try JSON parsing from answer
        try:
            # Clean up the string
            list_str = answer.replace("'", '"')
            json_match = re.search(r'\[.*\]', list_str, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                if isinstance(parsed, list):
                    return parsed
        except:
            pass
        
        # Fallback: construct from SQL result
        if isinstance(sql_result, list) and len(sql_result) > 0:
            result_list = []
            
            # Check if it's a list of strings (like categories)
            if "list[str]" in format_hint.lower() or format_hint == "list":
                for row in sql_result:
                    # Get first column value
                    val = list(row.values())[0]
                    result_list.append(str(val))
                return result_list
            
            # List of dicts with product and revenue
            for row in sql_result:
                if "product" in format_hint and "revenue" in format_hint:
                    product = (row.get("ProductName") or 
                              row.get("product") or 
                              row.get("Product") or "")
                    
                    revenue = (row.get("total_revenue") or
                              row.get("TotalRevenue") or 
                              row.get("revenue") or 
                              row.get("Revenue") or 0)
                    
                    result_list.append({
                        "product": str(product),
                        "revenue": round(float(revenue), 2)
                    })
            
            return result_list
        
        return []
    
    # Handle dict format: {category:str, quantity:int} or {customer:str, margin:float}
    if "{" in format_hint and "}" in format_hint:
        # Try to parse as JSON from answer first
        try:
            # Remove single quotes, replace with double quotes
            json_str = answer.replace("'", '"')
            json_match = re.search(r'\{[^}]+\}', json_str)
            if json_match:
                parsed = json.loads(json_match.group())
                if parsed and isinstance(parsed, dict):
                    return parsed
        except:
            pass
        
        # Fallback: construct from SQL result (SINGLE ROW ONLY)
        if isinstance(sql_result, list) and len(sql_result) > 0:
            row = sql_result[0]
            
            # Pattern 1: {category:str, quantity:int}
            if "category" in format_hint and "quantity" in format_hint:
                category = (row.get("CategoryName") or 
                           row.get("category") or 
                           row.get("Category") or 
                           row.get("TotalQuantitySold") or "")
                
                quantity = (row.get("TotalQuantity") or 
                           row.get("TotalQuantitySold") or
                           row.get("total_quantity") or 
                           row.get("quantity") or 
                           row.get("Quantity") or 0)
                
                return {
                    "category": str(category),
                    "quantity": int(quantity)
                }
            
            # Pattern 2: {customer:str, margin:float}
            elif "customer" in format_hint and "margin" in format_hint:
                customer = (row.get("CompanyName") or 
                           row.get("customer") or 
                           row.get("Customer") or "")
                
                margin = (row.get("gross_margin") or 
                         row.get("total_gross_margin") or
                         row.get("margin") or 
                         row.get("Margin") or 0)
                
                return {
                    "customer": str(customer),
                    "margin": round(float(margin), 2)
                }
            
            # Pattern 3: {product:str, revenue:float}
            elif "product" in format_hint and "revenue" in format_hint:
                product = (row.get("ProductName") or 
                          row.get("product") or 
                          row.get("Product") or "")
                
                revenue = (row.get("TotalRevenue") or 
                          row.get("total_revenue") or
                          row.get("revenue") or 
                          row.get("Revenue") or 0)
                
                return {
                    "product": str(product),
                    "revenue": round(float(revenue), 2)
                }
            
            # Pattern 4: {order_id:int, freight:float}
            elif "order_id" in format_hint and "freight" in format_hint:
                order_id = (row.get("OrderID") or 
                           row.get("order_id") or 0)
                
                freight = (row.get("freight") or 
                          row.get("Freight") or 0)
                
                return {
                    "order_id": int(order_id),
                    "freight": round(float(freight), 2)
                }
        
        return {}
    
    # Handle list format: list[{product:str, revenue:float}] or list[str]
    if format_hint.startswith("list"):
        # Try JSON parsing from answer
        try:
            # Clean up the string
            list_str = answer.replace("'", '"')
            json_match = re.search(r'\[.*\]', list_str, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                if isinstance(parsed, list):
                    return parsed
        except:
            pass
        
        # Fallback: construct from SQL result
        if isinstance(sql_result, list) and len(sql_result) > 0:
            result_list = []
            
            # Check if it's a list of strings (like categories)
            if "list[str]" in format_hint.lower() or format_hint == "list":
                for row in sql_result:
                    # Get first column value
                    val = list(row.values())[0]
                    result_list.append(str(val))
                return result_list
            
            # List of dicts with product and revenue
            for row in sql_result:
                if "product" in format_hint and "revenue" in format_hint:
                    product = (row.get("ProductName") or 
                              row.get("product") or 
                              row.get("Product") or "")
                    
                    revenue = (row.get("TotalRevenue") or 
                              row.get("total_revenue") or
                              row.get("revenue") or 
                              row.get("Revenue") or 0)
                    
                    result_list.append({
                        "product": str(product),
                        "revenue": round(float(revenue), 2)
                    })
            
            return result_list
        
        return []
    
    # Default: if answer is "Error" or empty, fallback to retrieved docs or SQL result
    if answer.lower() == "error" or not answer:
        if retrieved_docs and isinstance(retrieved_docs, list) and len(retrieved_docs) > 0:
            return retrieved_docs[0].get("content", "")
        if isinstance(sql_result, list) and len(sql_result) > 0:
            return str(sql_result[0])
            
    return answer


def extract_format_hint_from_question(question: str) -> str:
    """
    Extract the expected format from the question text.
    
    Args:
        question: Question text containing format instructions
        
    Returns:
        Format hint string (int, float, dict pattern, or list pattern)
    """
    question_lower = question.lower()
    
    # Check for explicit format instructions
    if "return an integer" in question_lower:
        return "int"
    
    if "return a float" in question_lower or "rounded to 2 decimals" in question_lower:
        return "float"
    
    # Check for dict patterns
    if "return {" in question_lower:
        # Extract the pattern
        match = re.search(r'return\s+(\{[^}]+\})', question_lower)
        if match:
            return match.group(1)
    
    # Check for list patterns  
    if "return list[" in question_lower:
        match = re.search(r'return\s+(list\[[^\]]+\])', question_lower)
        if match:
            return match.group(1)
    
    if "return list of" in question_lower or "return a list" in question_lower:
        return "list"
    
    return "str"