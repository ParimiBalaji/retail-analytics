# Northwind Marketing Calendar (year (y))

## Summer Beverages
- **Campaign Period: JUNE ONLY**
- Start Date: yyyy-06-01
- End Date: yyyy-06-30
- Duration: 1 month (June only, NOT July or August)
- SQL Date Filter: `strftime('%Y-%m', o.OrderDate) = 'yyyy-06'`
- **CRITICAL: Do NOT include July (yyyy-07) or August (yyyy-08) in this campaign**
- Focus Categories: Beverages and Condiments
- Notes: Despite the name "Summer Beverages", this is a June-only promotion

## Winter Classics
- **Campaign Period: DECEMBER ONLY**
- Start Date: yyyy-12-01
- End Date: yyyy-12-31
- Duration: 1 month (December only)
- SQL Date Filter: `strftime('%Y-%m', o.OrderDate) = 'yyyy-12'`
- Focus Categories: Dairy Products and Confections
- Notes: Holiday gifting promotion for December