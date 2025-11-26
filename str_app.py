import pymysql
import pandas as pd
import streamlit as st
from datetime import date
import altair as alt


def run_query(query, params=None):
    """Execute SQL and return a pandas DataFrame."""
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password="Rtx3090ti",
        database="mydb",
    )
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        rows = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description] if cursor.description else []
        return pd.DataFrame(rows, columns=cols)
    finally:
        conn.close()


def insert_dataframe_to_table(df, table_name):
    """Insert a pandas DataFrame into a database table."""
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password="Rtx3090ti",
        database="mydb",
    )
    try:
        cursor = conn.cursor()
        cols = ', '.join(df.columns)
        placeholders = ', '.join(['%s'] * len(df.columns))
        insert_sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"
        
        inserted = 0
        for idx, row in df.iterrows():
            try:
                cursor.execute(insert_sql, tuple(row))
                inserted += 1
            except Exception as e:
                print(f"Row {idx} failed: {e}")
        
        conn.commit()
        return inserted
    finally:
        cursor.close()
        conn.close()


st.set_page_config(
    page_title="Checkpost Dashboard",
    page_icon="🚔",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.streamlit.io/',
        'Report a bug': "https://github.com/streamlit/streamlit/issues",
        'About': "# Police Checkpost Dashboard\nBuilt with Streamlit for data analysis."
    }
)

# Custom CSS for aesthetics
st.markdown("""
<style>
    .main-header {
        font-size: 2.5em;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
        text-align: center;
    }
    .sidebar .sidebar-content {
        background-color: #ffffff;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f77b4;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">🚔 Police Checkpost Dashboard</h1>', unsafe_allow_html=True)

# ---------------------- CSV load & insert UI ----------------------
st.sidebar.markdown("---")
st.sidebar.header("CSV → DB")
csv_path_default = ""
csv_path = st.sidebar.text_input("CSV path (or leave blank to upload)", value=csv_path_default)
upload = st.sidebar.file_uploader("Or upload CSV file", type=["csv"]) 
table_name = st.sidebar.text_input("Target DB table", value="checkpost_stops")
insert_button = st.sidebar.button("Load & Insert CSV")

if insert_button:
    try:
        if upload is not None:
            df_upload = pd.read_csv(upload)
        else:
            df_upload = pd.read_csv(csv_path)

        st.sidebar.write(f"Preview ({len(df_upload)} rows):")
        st.sidebar.dataframe(df_upload.head())

        confirm = st.sidebar.checkbox("Confirm insert into DB table '" + table_name + "'", value=False)
        if confirm:
            with st.spinner("Inserting rows into DB — this may take a moment..."):
                inserted = insert_dataframe_to_table(df_upload, table_name)
            st.sidebar.success(f"Inserted {inserted} rows into `{table_name}`")
            st.sidebar.write("Consider validating inserted rows in the table before re-running.")
    except Exception as e:
        st.sidebar.error(f"Insert failed: {e}")

# ------------------------------------------------------------------

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    start_date = st.date_input("Start date", value=date(2015, 1, 1))
    end_date = st.date_input("End date", value=date.today())
    gender = st.selectbox("Driver gender", options=["All", "Male", "Female", "Unknown"])
    violation_contains = st.text_input("Violation contains (substring)")
    plate = st.text_input("Vehicle plate (exact)")
    search_flag = st.selectbox("Search conducted", options=["All", "True", "False"])
    run = st.button("Run query")

# Build SQL + params (safe)
base_sql = "SELECT * FROM checkpost_stops WHERE stop_date BETWEEN %s AND %s"
params = [start_date, end_date]

if gender != "All":
    base_sql += " AND driver_gender = %s"
    params.append(gender)
if violation_contains.strip() != "":
    base_sql += " AND violation LIKE %s"
    params.append(f"%{violation_contains.strip()}%")
if plate.strip() != "":
    base_sql += " AND vehicle_number = %s"
    params.append(plate.strip())
if search_flag in ("True", "False"):
    base_sql += " AND search_conducted = %s"
    params.append(True if search_flag == "True" else False)

base_sql += " ORDER BY stop_date DESC, stop_time DESC LIMIT 1000"
sql_to_run = base_sql

# Fetch data - automatically fetch if violation_contains is filled or run button clicked
if run or violation_contains.strip() != "":
    df = run_query(sql_to_run, tuple(params))
else:
    df = run_query("SELECT * FROM checkpost_stops ORDER BY stop_date DESC, stop_time DESC LIMIT 200")

st.subheader("Recent Stops")
st.write(f"Showing {len(df)} rows (filtered).")
# Hide vehicle_plate column if it exists
if 'vehicle_plate' in df.columns:
    df_display = df.drop(columns=['vehicle_plate'])
else:
    df_display = df
st.dataframe(df_display, use_container_width=True)

# ============================================================
# 📊 PREDICTION SUMMARY - Based on query results
# ============================================================
if len(df) > 0:
    st.subheader("🔮 Prediction Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Prediction 1: Average age of stopped drivers
    with col1:
        if 'driver_age' in df.columns:
            avg_age = df['driver_age'].replace('Unknown', pd.NA).apply(pd.to_numeric, errors='coerce').mean()
            if not pd.isna(avg_age):
                st.metric("Avg Driver Age", f"{avg_age:.1f} years")
            else:
                st.metric("Avg Driver Age", "N/A")
        else:
            st.metric("Avg Driver Age", "N/A")
    
    # Prediction 2: Arrest likelihood
    with col2:
        if 'is_arrested' in df.columns:
            arrest_count = pd.to_numeric(df['is_arrested'], errors='coerce').fillna(0).sum()
            arrest_rate = (arrest_count / len(df) * 100) if len(df) > 0 else 0
            st.metric("Arrest Rate", f"{arrest_rate:.1f}%")
        else:
            st.metric("Arrest Rate", "N/A")
    
    # Prediction 3: Search likelihood
    with col3:
        if 'search_conducted' in df.columns:
            search_count = pd.to_numeric(df['search_conducted'], errors='coerce').fillna(0).sum()
            search_rate = (search_count / len(df) * 100) if len(df) > 0 else 0
            st.metric("Search Rate", f"{search_rate:.1f}%")
        else:
            st.metric("Search Rate", "N/A")
    
    # Prediction 4: Most common violation
    with col4:
        if 'violation' in df.columns:
            top_violation = df['violation'].fillna('Unknown').value_counts().idxmax()
            st.metric("Top Violation", top_violation[:20])
        else:
            st.metric("Top Violation", "N/A")
    
    # Additional insights
    st.write("---")
    st.subheader("📈 Key Insights from Filtered Data")
    
    insights = []
    
    # Insight 1: Gender distribution
    if 'driver_gender' in df.columns:
        gender_counts = df['driver_gender'].value_counts()
        if len(gender_counts) > 0:
            top_gender = gender_counts.idxmax()
            insights.append(f"👥 Most stopped drivers are **{top_gender}** ({gender_counts[top_gender]} stops)")
    
    # Insight 2: Drug-related stops
    if 'drugs_related_stop' in df.columns:
        drug_count = pd.to_numeric(df['drugs_related_stop'], errors='coerce').fillna(0).sum()
        drug_pct = (drug_count / len(df) * 100) if len(df) > 0 else 0
        insights.append(f"💊 Drug-related stops: **{drug_pct:.1f}%** of filtered results")
    
    # Insight 3: Stop duration
    if 'stop_duration' in df.columns:
        duration_counts = df['stop_duration'].fillna('Unknown').value_counts()
        if len(duration_counts) > 0:
            top_duration = duration_counts.idxmax()
            insights.append(f"⏱️ Most common stop duration: **{top_duration}**")
    
    # Insight 4: Citation vs Arrest
    if 'stop_outcome' in df.columns:
        outcome_counts = df['stop_outcome'].fillna('Unknown').value_counts()
        if len(outcome_counts) > 0:
            top_outcome = outcome_counts.idxmax()
            insights.append(f"📋 Most common outcome: **{top_outcome}**")
    
    # Insight 5: High-risk profile
    if 'is_arrested' in df.columns and 'search_conducted' in df.columns:
        high_risk = df[(pd.to_numeric(df['search_conducted'], errors='coerce').fillna(0) == 1) & 
                       (pd.to_numeric(df['is_arrested'], errors='coerce').fillna(0) == 1)]
        if len(high_risk) > 0:
            insights.append(f"🚨 High-risk stops (searched & arrested): **{len(high_risk)}** ({len(high_risk)/len(df)*100:.1f}%)")
    
    if insights:
        for insight in insights:
            st.write(f"• {insight}")
    else:
        st.info("No insights available for current filters")
# Quick metrics
st.subheader("📊 Quick Metrics")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Total (shown)", len(df))
    st.markdown('</div>', unsafe_allow_html=True)
with c2:
    if 'is_arrested' in df.columns and not df.empty:
        # Convert to numeric, handling boolean and string values
        arrests = pd.to_numeric(df['is_arrested'], errors='coerce').fillna(0).astype(int).sum()
    else:
        arrests = 0
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Arrests (shown)", arrests)
    st.markdown('</div>', unsafe_allow_html=True)
with c3:
    if 'search_conducted' in df.columns and not df.empty:
        # Convert to numeric, handling boolean and string values
        searches = pd.to_numeric(df['search_conducted'], errors='coerce').fillna(0).astype(int).sum()
    else:
        searches = 0
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Searches (shown)", searches)
    st.markdown('</div>', unsafe_allow_html=True)

# Violation distribution (fixed)
st.subheader("Violation Distribution")
if 'violation' in df.columns and not df['violation'].isnull().all() and len(df) > 0:
    vc = df['violation'].fillna('Unknown').value_counts().reset_index()
    vc.columns = ['violation', 'count']   # ensure good names
    vc = vc.sort_values('count', ascending=False).head(20)
    chart = alt.Chart(vc).mark_bar().encode(
        x=alt.X('count:Q', title='Count'),
        y=alt.Y('violation:N', sort='-x', title='Violation')
    ).properties(height=400)
    st.altair_chart(chart, use_container_width=True)
else:
    st.info("No violation data available for charting.")

# Time-series of stops by day
if 'stop_date' in df.columns and len(df) > 0:
    try:
        ts = df.groupby('stop_date').size().reset_index(name='count')
        ts['stop_date'] = pd.to_datetime(ts['stop_date'])
        tchart = alt.Chart(ts).mark_line(point=True).encode(
            x=alt.X('stop_date:T', title='Date'),
            y=alt.Y('count:Q', title='Stops')
        ).properties(height=250)
        st.altair_chart(tchart, use_container_width=True)
    except Exception:
        st.info("Unable to render time-series (check stop_date values).")

# Alerts: repeated vehicles (SQL-level)
st.subheader("Automated Alerts")
rep_sql = """
SELECT vehicle_number, COUNT(*) as cnt
FROM checkpost_stops
WHERE vehicle_number IS NOT NULL
  AND vehicle_number <> ''
  AND stop_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY vehicle_number
HAVING cnt >= 2
ORDER BY cnt DESC
LIMIT 50;
"""
try:
    repeated = run_query(rep_sql)
    if not repeated.empty:
        st.warning("Repeated vehicle stops in last 30 days")
        st.table(repeated)
    else:
        st.info("No repeated vehicle alerts in last 30 days")
except Exception as e:
    st.warning(f"Could not fetch repeated vehicle data: {e}")

# High-risk: searches that led to arrests
try:
    if set(['search_conducted','is_arrested']).issubset(df.columns) and not df.empty:
        sr = df[(df['search_conducted'] == True) & (df['is_arrested'] == True)]
        if not sr.empty:
            st.error("Search -> Arrest events (high-risk)")
            # Only show columns that exist in the dataframe
            available_cols = [col for col in ['stop_date','stop_time','vehicle_number','violation','officer_id','stop_outcome'] if col in df.columns]
            st.dataframe(sr[available_cols])
        else:
            st.info("No Search->Arrest events in filtered results.")
except Exception as e:
    st.warning(f"Could not fetch high-risk data: {e}")

st.caption("Tip: Tune rules & thresholds per local policy.")

st.divider()

# ============================================================
# 📊 SQL ANALYTICS PANELS
# ============================================================

st.header("📊 Advanced SQL Analytics Panels")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🚗 Vehicle-Based",
    "🧑 Demographic-Based",
    "⏱ Time & Duration Based",
    "⚖️ Violation-Based",
    "🌍 Location-Based",
    "🔬 Complex Analytics"
])

with tab1:
    st.subheader("Vehicle-Based Analytics")
    q = st.selectbox("Choose query:", [
        "Top 10 vehicles in drug-related stops",
        "Vehicles most frequently searched"
    ], key="vehicle_q")

    if q == "Top 10 vehicles in drug-related stops":
        sql = """
        SELECT vehicle_number,
               COUNT(*) AS drug_stop_count
        FROM checkpost_stops
        WHERE drugs_related_stop = 1
        GROUP BY vehicle_number
        ORDER BY drug_stop_count DESC
        LIMIT 10;
        """
        try:
            df2 = run_query(sql)
            st.subheader("🚗 Top 10 Drug-Related Vehicle Plates")
            st.table(df2)
        except Exception as e:
            st.warning(f"Query failed: {e}")

    if q == "Vehicles most frequently searched":
        sql = """
        SELECT vehicle_number,
               COUNT(*) AS searches
        FROM checkpost_stops
        WHERE search_conducted = 1
        GROUP BY vehicle_number
        ORDER BY searches DESC
        LIMIT 20;
        """
        try:
            df2 = run_query(sql)
            st.subheader("🚓 Vehicles Most Frequently Searched")
            st.table(df2)
        except Exception as e:
            st.warning(f"Query failed: {e}")

with tab2:
    st.subheader("Demographic-Based Analytics")
    q = st.selectbox("Choose query:", [
        "Age group with highest arrest rate",
        "Gender distribution per country",
        "Race + Gender with highest search rate"
    ], key="demo_q")

    if q == "Age group with highest arrest rate":
        sql = """
        SELECT age_group,
               total_stops,
               arrests,
               ROUND(100.0 * arrests / NULLIF(total_stops,0), 2) AS arrest_rate_pct
        FROM (
          SELECT
            CASE
              WHEN driver_age < 18 THEN '<18'
              WHEN driver_age BETWEEN 18 AND 24 THEN '18-24'
              WHEN driver_age BETWEEN 25 AND 34 THEN '25-34'
              WHEN driver_age BETWEEN 35 AND 44 THEN '35-44'
              WHEN driver_age >= 45 THEN '45+'
              ELSE 'Unknown'
            END AS age_group,

            
            COUNT(*) AS total_stops,
            SUM(is_arrested = 1) AS arrests
          FROM checkpost_stops
          WHERE driver_age IS NOT NULL
          GROUP BY age_group
        ) t
        ORDER BY arrest_rate_pct DESC;
        """
        try:
            df2 = run_query(sql)
            st.subheader("🧑 Age Group with Highest Arrest Rate")
            st.bar_chart(df2, x="age_group", y="arrest_rate_pct")
            st.table(df2)
        except Exception as e:
            st.warning(f"Query failed: {e}")

    if q == "Gender distribution per country":
        sql = """
        SELECT country_name,
               driver_gender,
               COUNT(*) AS stops
        FROM checkpost_stops
        GROUP BY country_name, driver_gender
        ORDER BY country_name, stops DESC;
        """
        try:
            df2 = run_query(sql)
            st.subheader("🧍 Gender Distribution by Country")
            st.table(df2)
        except Exception as e:
            st.warning(f"Query failed: {e}")

    if q == "Race + Gender with highest search rate":
        sql = """
        SELECT driver_race, driver_gender,
               COUNT(*) AS total_stops,
               SUM(search_conducted = 1) AS searches,
               ROUND(100.0 * SUM(search_conducted = 1) / NULLIF(COUNT(*),0),2) AS search_rate_pct
        FROM checkpost_stops
        GROUP BY driver_race, driver_gender
        HAVING total_stops >= 10
        ORDER BY search_rate_pct DESC;
        """
        try:
            df2 = run_query(sql)
            st.subheader("🧑 Race × Gender Search Rate")
            st.table(df2)
        except Exception as e:
            st.warning(f"Query failed: {e}")

with tab3:
    st.subheader("Time & Duration Based Analytics")
    q = st.selectbox("Choose query:", [
        "Hour of day with most stops",
        "Average stop duration per violation",
        "Are night stops more likely to lead to arrests?"
    ], key="time_q")

    if q == "Hour of day with most stops":
        sql = """
        SELECT HOUR(stop_time) AS hour_of_day,
               COUNT(*) AS stops
        FROM checkpost_stops
        GROUP BY hour_of_day
        ORDER BY stops DESC;
        """
        try:
            df2 = run_query(sql)
            st.subheader("🕒 Traffic Stops by Hour of Day")
            st.bar_chart(df2, x="hour_of_day", y="stops")
        except Exception as e:
            st.warning(f"Query failed: {e}")

    if q == "Average stop duration per violation":
        sql = """
        SELECT violation,
               COUNT(*) AS stops,
               ROUND(AVG(
                 CASE stop_duration
                     WHEN '<5 minutes' THEN 2.5
                     WHEN '6-15 minutes' THEN 10
                     WHEN '16-30 minutes' THEN 23
                     ELSE NULL
                 END
               ),1) AS avg_duration
        FROM checkpost_stops
        GROUP BY violation;
        """
        try:
            df2 = run_query(sql)
            st.subheader("⏱ Avg Stop Duration by Violation")
            st.table(df2)
        except Exception as e:
            st.warning(f"Query failed: {e}")

    if q == "Are night stops more likely to lead to arrests?":
        sql = """
        SELECT period,
               total_stops,
               arrests,
               ROUND(100.0 * arrests / NULLIF(total_stops,0),2) AS arrest_rate_pct
        FROM (
          SELECT
            CASE WHEN HOUR(stop_time) BETWEEN 20 AND 23
                      OR HOUR(stop_time) BETWEEN 0 AND 5 THEN 'Night'
                 ELSE 'Day'
            END AS period,
            COUNT(*) AS total_stops,
            SUM(is_arrested = 1) AS arrests
          FROM checkpost_stops
          GROUP BY period
        ) t;
        """
        try:
            df2 = run_query(sql)
            st.subheader("🌙 Night Arrest Probability")
            st.bar_chart(df2, x="period", y="arrest_rate_pct")
            st.table(df2)
        except Exception as e:
            st.warning(f"Query failed: {e}")

with tab4:
    st.subheader("Violation-Based Analytics")
    q = st.selectbox("Choose query:", [
        "Violations linked to searches/arrests",
        "Violations common among <25 drivers",
        "Violations with almost no searches/arrests"
    ], key="violation_q")

    if q == "Violations linked to searches/arrests":
        sql = """
        SELECT violation,
               COUNT(*) AS total_stops,
               SUM(search_conducted = 1) AS searches,
               SUM(is_arrested = 1) AS arrests,
               ROUND(100.0 * SUM(search_conducted = 1) / NULLIF(COUNT(*),0),2) AS search_rate_pct,
               ROUND(100.0 * SUM(is_arrested = 1) / NULLIF(COUNT(*),0),2) AS arrest_rate_pct
        FROM checkpost_stops
        GROUP BY violation
        ORDER BY search_rate_pct DESC;
        """
        try:
            df2 = run_query(sql)
            st.subheader("⚖️ Search & Arrest Rates by Violation")
            st.table(df2)
        except Exception as e:
            st.warning(f"Query failed: {e}")

    if q == "Violations common among <25 drivers":
        sql = """
        SELECT violation,
               COUNT(*) AS stops_under_25
        FROM checkpost_stops
        WHERE driver_age < 25
        GROUP BY violation
        ORDER BY stops_under_25 DESC;
        """
        try:
            df2 = run_query(sql)
            st.subheader("👦 Violations Among Drivers <25")
            st.table(df2)
        except Exception as e:
            st.warning(f"Query failed: {e}")

    if q == "Violations with almost no searches/arrests":
        sql = """
        SELECT violation,
               COUNT(*) AS total_stops,
               SUM(search_conducted = 1) AS searches,
               SUM(is_arrested = 1) AS arrests
        FROM checkpost_stops
        GROUP BY violation
        HAVING total_stops >= 20
        ORDER BY searches ASC, arrests ASC;
        """
        try:
            df2 = run_query(sql)
            st.subheader("🟢 Safe Violations (Rarely lead to search/arrest)")
            st.table(df2)
        except Exception as e:
            st.warning(f"Query failed: {e}")

with tab5:
    st.subheader("Location-Based Analytics")
    q = st.selectbox("Choose query:", [
        "Countries with highest drug-related stops",
        "Arrest rate by country and violation",
        "Countries with most searches"
    ], key="location_q")

    if q == "Countries with highest drug-related stops":
        sql = """
        SELECT country_name,
               COUNT(*) AS total_stops,
               SUM(drugs_related_stop = 1) AS drug_stops,
               ROUND(100.0 * SUM(drugs_related_stop = 1) / NULLIF(COUNT(*),0),2) AS drug_rate
        FROM checkpost_stops
        GROUP BY country_name
        ORDER BY drug_rate DESC;
        """
        try:
            df2 = run_query(sql)
            st.subheader("🌍 Drug-Related Stop Rates by Country")
            st.table(df2)
        except Exception as e:
            st.warning(f"Query failed: {e}")

    if q == "Arrest rate by country and violation":
        sql = """
        SELECT country_name, violation,
               COUNT(*) AS total_stops,
               SUM(is_arrested = 1) AS arrests,
               ROUND(100.0 * SUM(is_arrested = 1) / NULLIF(COUNT(*),0),2) AS arrest_rate
        FROM checkpost_stops
        GROUP BY country_name, violation
        HAVING total_stops >= 10
        ORDER BY arrest_rate DESC;
        """
        try:
            df2 = run_query(sql)
            st.subheader("⚖️ Arrest Rate by Country & Violation")
            st.table(df2)
        except Exception as e:
            st.warning(f"Query failed: {e}")

    if q == "Countries with most searches":
        sql = """
        SELECT country_name,
               COUNT(*) AS total_stops,
               SUM(search_conducted = 1) AS searches
        FROM checkpost_stops
        GROUP BY country_name
        ORDER BY searches DESC;
        """
        try:
            df2 = run_query(sql)
            st.subheader("🔍 Search Volume by Country")
            st.table(df2)
        except Exception as e:
            st.warning(f"Query failed: {e}")

with tab6:
    st.subheader("Complex Analytics")
    q = st.selectbox("Choose query:", [
        "Yearly stops & arrests by country",
        "Violation trends by age & race",
        "Time period analysis (Year/Month/Hour)",
        "High search/arrest rate violations",
        "Driver demographics by country",
        "Top 5 violations by arrest rate"
    ], key="complex_q")

    if q == "Yearly stops & arrests by country":
        sql = """
        WITH yearly AS (
          SELECT
            country_name,
            YEAR(stop_date) AS year,
            COUNT(*) AS stops,
            SUM(is_arrested = 1) AS arrests
          FROM checkpost_stops
          GROUP BY country_name, YEAR(stop_date)
        )
        SELECT
          country_name, year, stops, arrests,
          ROUND(100.0 * arrests / NULLIF(stops,0),2) AS arrest_rate
        FROM yearly
        ORDER BY country_name, year DESC;
        """
        try:
            df2 = run_query(sql)
            st.subheader("📅 Yearly Stops & Arrests by Country")
            st.table(df2)
        except Exception as e:
            st.warning(f"Query failed: {e}")

    if q == "Violation trends by age & race":
        sql = """
        SELECT driver_age, driver_race, violation, COUNT(*) AS cnt
        FROM checkpost_stops
        WHERE driver_age IS NOT NULL
        GROUP BY driver_age, driver_race, violation
        ORDER BY cnt DESC
        LIMIT 200;
        """
        try:
            df2 = run_query(sql)
            st.subheader("📈 Violation Trends (Age × Race)")
            st.table(df2)
        except Exception as e:
            st.warning(f"Query failed: {e}")

    if q == "Time period analysis (Year/Month/Hour)":
        sql = """
        SELECT YEAR(stop_date) AS year,
               MONTH(stop_date) AS month,
               HOUR(stop_time) AS hour,
               COUNT(*) AS stops
        FROM checkpost_stops
        GROUP BY year, month, hour
        ORDER BY year DESC, month DESC, hour;
        """
        try:
            df2 = run_query(sql)
            st.subheader("⏱ Time Period Analysis")
            st.table(df2)
        except Exception as e:
            st.warning(f"Query failed: {e}")

    if q == "High search/arrest rate violations":
        sql = """
        SELECT violation,
               COUNT(*) AS total_stops,
               SUM(search_conducted = 1) AS searches,
               SUM(is_arrested = 1) AS arrests,
               ROUND(100.0 * SUM(search_conducted = 1)/COUNT(*),2) AS search_rate,
               ROUND(100.0 * SUM(is_arrested = 1)/COUNT(*),2) AS arrest_rate
        FROM checkpost_stops
        GROUP BY violation
        ORDER BY search_rate DESC, arrest_rate DESC;
        """
        try:
            df2 = run_query(sql)
            st.subheader("🔥 High Search/Arrest Rate Violations")
            st.table(df2)
        except Exception as e:
            st.warning(f"Query failed: {e}")

    if q == "Driver demographics by country":
        sql = """
        SELECT country_name,
               COUNT(*) AS stops,
               ROUND(AVG(driver_age),1) AS avg_age,
               SUM(driver_gender='Male') AS male,
               SUM(driver_gender='Female') AS female
        FROM checkpost_stops
        GROUP BY country_name
        ORDER BY stops DESC;
        """
        try:
            df2 = run_query(sql)
            st.subheader("👥 Driver Demographics by Country")
            st.table(df2)
        except Exception as e:
            st.warning(f"Query failed: {e}")

    if q == "Top 5 violations by arrest rate":
        sql = """
        SELECT violation,
               COUNT(*) AS total_stops,
               SUM(is_arrested = 1) AS arrests,
               ROUND(100.0 * SUM(is_arrested = 1)/COUNT(*),2) AS arrest_rate
        FROM checkpost_stops
        GROUP BY violation
        ORDER BY arrest_rate DESC
        LIMIT 5;
        """
        try:
            df2 = run_query(sql)
            st.subheader("🚨 Top 5 High-Arrest Violations")
            st.table(df2)
        except Exception as e:
            st.warning(f"Query failed: {e}")
