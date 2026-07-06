# Weekly and Monthly Summaries

The summary commands read daily CSV files from `data/articles-YYYY-MM-DD.csv`.

## Weekly summary

By default, the weekly command aggregates the previous full week, Monday through Sunday, and writes a CSV to `data/weekly/`.

```powershell
python weekly_aggregate.py
```

You can also target a specific ISO week or a custom date range:

```powershell
python weekly_aggregate.py --week 2026-W23
python weekly_aggregate.py --start-date 2026-06-01 --end-date 2026-06-07
```

## Monthly summary

By default, the monthly command aggregates the previous month and writes an Excel workbook to `data/monthly/`.

```powershell
python monthly_news_stats.py
python monthly_news_stats.py --month 2026-06
```

The workbook contains:

- `Articles`: deduplicated article details.
- `Source Summary`: counts by source, domain, sub-domain, and future category.
- `Domain Summary`: counts by domain and sub-domain.
- `Daily Summary`: counts by day.
- `Category Placeholder`: reserved for later classification output.

Classification is intentionally left blank for now. The detail output already includes `category` and `category_method`, so later work can fill in the selected field taxonomy and classification method without changing the summary file shape.
