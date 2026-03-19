import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from wordcloud import WordCloud

# 1️⃣ Conexión a la DB
conn = sqlite3.connect("./logs/logs.db")
df = pd.read_sql_query("SELECT * FROM logs", conn)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["date"] = df["timestamp"].dt.date

st.set_page_config(page_title="RAG Dashboard", layout="wide")
st.title("📊 RAG Dashboard Avanzado")

# 2️⃣ Métricas generales
st.header("📈 Métricas generales")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total consultas", len(df))
col2.metric("Tiempo promedio (s)", round(df["response_time"].mean(), 2))
col3.metric("Promedio de fuentes", round(df["num_sources"].mean(), 2))
col4.metric("Promedio longitud contexto", round(df["context_length"].mean(), 0))

# 3️⃣ Fallbacks
st.header("⚠️ Fallbacks")
fallbacks = df["answer"].str.contains("No tengo suficiente", na=False).sum()
st.metric("Respuestas sin info", fallbacks)

# 4️⃣ Consultas por día
st.header("📅 Consultas por día")
queries_per_day = df.groupby("date").size()
st.line_chart(queries_per_day)

# 5️⃣ Distribución de tiempo de respuesta
st.header("⏱️ Tiempo de respuesta")
st.bar_chart(df["response_time"])

# 6️⃣ Top preguntas recientes
st.header("💬 Preguntas recientes")
st.dataframe(df[["timestamp", "question", "response_time"]].sort_values(by="timestamp", ascending=False).head(10))

# 7️⃣ WordCloud de preguntas
st.header("🔑 Palabras más frecuentes en preguntas")
text = " ".join(df["question"].tolist())
wordcloud = WordCloud(width=800, height=400, background_color="white").generate(text)
st.image(wordcloud.to_array(), use_column_width=True)

# 8️⃣ Distribución de número de fuentes
st.header("📚 Distribución de número de fuentes")
fig, ax = plt.subplots()
df["num_sources"].hist(bins=10, ax=ax)
ax.set_xlabel("Número de fuentes")
ax.set_ylabel("Cantidad de consultas")
st.pyplot(fig)