import streamlit as st
import sqlite3
import uuid
from datetime import datetime
import pandas as pd
import re

st.title("DerMAI PRO")

conn = sqlite3.connect("data.db", check_same_thread=False)
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS requests (id TEXT, paciente TEXT, enfermedad TEXT)")
conn.commit()

# FORMULARIO
paciente = st.text_input("Paciente (AN + 10 dígitos)")
enfermedad = st.selectbox("Enfermedad", ["Psoriasis", "Dermatitis"])

if st.button("Enviar"):
    if re.fullmatch(r"AN\d{10}", paciente):
        c.execute("INSERT INTO requests VALUES (?,?,?)",
                  (str(uuid.uuid4()), paciente, enfermedad))
        conn.commit()
        st.success("Guardado")
    else:
        st.error("Formato incorrecto")

# TABLA
df = pd.read_sql_query("SELECT * FROM requests", conn)
st.dataframe(df)
