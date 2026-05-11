import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import config

st.set_page_config(layout="wide", page_title="Patent Intelligence Dashboard")
st.title("📊 Global Patent Intelligence Dashboard")

@st.cache_resource
def get_connection():
    return sqlite3.connect(config.DB_PATH)

@st.cache_data
def load_query(query):
    with get_connection() as conn:
        return pd.read_sql(query, conn)

# ----- KPI Cards -----
st.subheader("📈 Overview")
col1, col2, col3 = st.columns(3)
col1.metric("Total Patents", load_query("SELECT COUNT(*) FROM patents").iloc[0,0])
col2.metric("Total Inventors", load_query("SELECT COUNT(*) FROM inventors").iloc[0,0])
col3.metric("Total Companies", load_query("SELECT COUNT(*) FROM companies").iloc[0,0])

# ----- Yearly Trend Chart -----
st.subheader("📅 Patents per Year")
yearly = load_query("SELECT year, COUNT(*) as cnt FROM patents WHERE year NOT NULL GROUP BY year ORDER BY year")
fig, ax = plt.subplots()
ax.bar(yearly['year'], yearly['cnt'], color='steelblue')
ax.set_xlabel("Year")
ax.set_ylabel("Patents")
st.pyplot(fig)

# ----- Top 10 Countries -----
st.subheader("🌍 Top 10 Countries")
countries = load_query("""
    SELECT i.country, COUNT(DISTINCT r.patent_id) as cnt
    FROM inventors i JOIN relationships r ON i.inventor_id = r.inventor_id
    WHERE i.country != ''
    GROUP BY i.country
    ORDER BY cnt DESC LIMIT 10
""")
st.dataframe(countries, use_container_width=True)

# ----- Top 5 Inventors & Companies (side‑by‑side) -----
col1, col2 = st.columns(2)
with col1:
    st.subheader("🏆 Top 5 Inventors")
    inv = load_query("""
        SELECT i.name, COUNT(r.patent_id) as cnt
        FROM inventors i JOIN relationships r ON i.inventor_id = r.inventor_id
        GROUP BY i.inventor_id ORDER BY cnt DESC LIMIT 5
    """)
    st.dataframe(inv, use_container_width=True)
with col2:
    st.subheader("🏢 Top 5 Companies")
    comp = load_query("""
        SELECT c.name, COUNT(r.patent_id) as cnt
        FROM companies c JOIN relationships r ON c.company_id = r.company_id
        GROUP BY c.company_id ORDER BY cnt DESC LIMIT 5
    """)
    st.dataframe(comp, use_container_width=True)

# ----- Search -----
st.subheader("🔍 Search Patents by Title")
search_term = st.text_input("Enter keyword")
if search_term:
    results = load_query(f"SELECT patent_id, title, year FROM patents WHERE title LIKE '%{search_term}%' LIMIT 20")
    st.dataframe(results, use_container_width=True)