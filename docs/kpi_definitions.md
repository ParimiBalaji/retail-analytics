# KPI Definitions

## Average Order Value (AOV)

**Definition:** The average revenue per order in a given period.

**Formula:**
```
AOV = SUM(UnitPrice * Quantity * (1 - Discount)) / COUNT(DISTINCT OrderID)
```

**SQL Implementation:**
```sql
SELECT ROUND(
    SUM(oi.UnitPrice * oi.Quantity * (1 - oi.Discount)) / COUNT(DISTINCT o.OrderID),
    2
) AS AOV
FROM orders o
JOIN order_items oi ON o.OrderID = oi.OrderID
WHERE [date filter here]
-- IMPORTANT: No GROUP BY clause when calculating AOV across all orders
```

**Common Mistakes:**
- ❌ Adding `GROUP BY o.OrderID` - this calculates per-order, not average
- ❌ Using `AVG()` function - must use SUM/COUNT formula

---

## Gross Margin

**Definition:** Revenue minus cost of goods sold (COGS).

**Formula:**
```
GM = SUM((UnitPrice - CostOfGoods) * Quantity * (1 - Discount))
```

**Cost Assumption:** If CostOfGoods is not available in the database, approximate it as **70% of UnitPrice**. This means the gross margin is **30% of revenue**.

**SQL Implementation (with 70% cost assumption):**
```sql
SELECT c.CompanyName,
       ROUND(SUM((oi.UnitPrice * 0.3) * oi.Quantity * (1 - oi.Discount)), 2) AS gross_margin
FROM customers c
JOIN orders o ON c.CustomerID = o.CustomerID  
JOIN order_items oi ON o.OrderID = oi.OrderID
WHERE [date filter here]
GROUP BY c.CompanyName
ORDER BY gross_margin DESC
```

**Calculation Breakdown:**
- If UnitPrice = $100, then CostOfGoods = $70 (assumed)
- Margin per unit = $100 - $70 = $30
- As percentage: $30/$100 = 30% = 0.3
- Formula simplification: `(UnitPrice - UnitPrice*0.7) = UnitPrice * 0.3`

**Common Mistakes:**
- ❌ Using nested SUM: `SUM(price - SUM(price*0.7))` - causes SQLite syntax error
- ✅ Correct: `SUM((price * 0.3) * quantity * (1-discount))`
- ❌ Forgetting to multiply by quantity and discount factor