# SecureCheck-A-Python-SQL-Digital-Ledger-for-Police-Post-Logs
Police check posts require a centralized system for logging, tracking, and analyzing vehicle movements. Currently, manual logging and inefficient databases slow down security processes. This project aims to build an SQL-based check post database with a Python-powered dashboard for real-time insights and alerts.
# Police Check-Post Project — Quick Start

## Requirements
- Python 3.8+
- PostgreSQL or MySQL
- pip packages: pandas, sqlalchemy, psycopg2-binary (Postgres) or pymysql (MySQL), streamlit, plotly

## Files
- /mnt/data/traffic_stops_cleaned.csv  (cleaned dataset)
- traffic_stops_cleanup_report.txt     (cleanup report & CREATE TABLE SQL)
- load_to_db.py                        (script to upload CSV to DB)
- app.py                               (Streamlit dashboard)

## Steps
1. Create DB and user (Postgres or MySQL)
2. Create table (use SQL in cleanup report)
3. Run `python load_to_db.py` to upload CSV
4. Run `streamlit run app.py` and open http://localhost:8506
