import streamlit as st
import sqlite3
import uuid
from datetime import datetime
import pandas as pd
import re

st.set_page_config(layout="wide")
st.title("DerMAI PRO")

# ======================
# DB LIMPIA Y ESTABLE
# ======================
conn = sqlite3.connect("data.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS requests (
    id TEXT PRIMARY KEY,
    paciente TEXT,
    solicitante TEXT,
    enfermedad TEXT,
    tratamiento TEXT,
    estado TEXT,
    fecha TEXT,
    fecha_director TEXT,
    fecha_farmacia TEXT
)
""")
conn.commit()

# ======================
# LOGIN
# ======================
USERS = {
    "derma": "Dermatólogo",
    "director": "Director",
    "farmacia": "Farmacia"
}

user = st.sidebar.selectbox("Usuario", list(USERS.keys()))
role = USERS[user]

st.sidebar.write(f"Rol: {role}")

# ======================
# PROTOCOLOS COMPLETOS
# ======================
protocolos = {
    "Psoriasis en placas": [
        "Adalimumab",
        "Ustekinumab",
        "Secukinumab",
        "Ixekizumab",
        "Guselkumab",
        "Risankizumab",
        "Tildrakizumab",
        "Bimekizumab"
    ],
    "Dermatitis atópica": [
        "Dupilumab",
        "Tralokinumab",
        "Upadacitinib",
        "Baricitinib"
    ],
    "Hidradenitis supurativa": [
        "Adalimumab",
        "Secukinumab",
        "Bimekizumab"
    ],
    "Alopecia areata": [
        "Baricitinib",
        "Ritlecitinib"
    ],
    "Melanoma": [
        "Nivolumab",
        "Pembrolizumab"
    ]
}

# ======================
# NUEVA SOLICITUD
# ======================
if role == "Dermatólogo":

    st.subheader("Nueva solicitud")

    paciente = st.text_input("Paciente (AN + 10 dígitos)", value="AN")
    solicitante = st.text_input("Solicitante")
    enfermedad = st.selectbox("Enfermedad", list(protocolos.keys()))
    tratamiento = st.selectbox("Tratamiento", protocolos[enfermedad])

    if st.button("Enviar"):
        if not re.fullmatch(r"AN\d{10}", paciente.strip().upper()):
            st.error("Formato incorrecto")
        else:
            c.execute("""
            INSERT INTO requests VALUES (?,?,?,?,?,?,?, ?,?)
            """, (
                str(uuid.uuid4()),
                paciente.strip().upper(),
                solicitante,
                enfermedad,
                tratamiento,
                "Pendiente Director",
                datetime.now().strftime("%d/%m/%Y %H:%M"),
                "",
                ""
            ))
            conn.commit()
            st.success("Solicitud creada")
            st.rerun()

# ======================
# ESTADO CLARO
# ======================
def estado(r):
    if r["estado"] == "Pendiente Director":
        return "Pendiente Director"
    if r["estado"] == "No validado Director":
        return "No validado Director"
    if r["estado"] == "Pendiente Farmacia":
        return "Pendiente Farmacia"
    if r["estado"] == "No validado Farmacia":
        return "No validado Farmacia"
    if r["estado"] == "Validado":
        return "Validado"
    return r["estado"]

# ======================
# TABLA
# ======================
st.subheader("Solicitudes")

df = pd.read_sql_query("SELECT * FROM requests ORDER BY fecha DESC", conn)

if not df.empty:
    df["Estado"] = df.apply(estado, axis=1)

    st.dataframe(
        df[["paciente","solicitante","enfermedad","tratamiento","Estado"]],
        use_container_width=True
    )

# ======================
# ACCIONES (SIN DUPLICADOS)
# ======================
st.subheader("Acciones")

for i, r in df.iterrows():

    if role == "Director" and r["estado"] != "Pendiente Director":
        continue

    if role == "Farmacia" and r["estado"] != "Pendiente Farmacia":
        continue

    st.write("---")
    st.write(f"{r['paciente']} | {r['tratamiento']}")

    # DIRECTOR
    if role == "Director":
        col1, col2 = st.columns(2)

        if col1.button("Validar", key=f"dval_{i}"):
            c.execute("""
            UPDATE requests SET estado='Pendiente Farmacia', fecha_director=? WHERE id=?
            """, (datetime.now().strftime("%d/%m/%Y %H:%M"), r["id"]))
            conn.commit()
            st.rerun()

        if col2.button("No validado", key=f"dno_{i}"):
            c.execute("""
            UPDATE requests SET estado='No validado Director', fecha_director=? WHERE id=?
            """, (datetime.now().strftime("%d/%m/%Y %H:%M"), r["id"]))
            conn.commit()
            st.rerun()

    # FARMACIA
    if role == "Farmacia":
        col1, col2 = st.columns(2)

        if col1.button("Validar", key=f"fval_{i}"):
            c.execute("""
            UPDATE requests SET estado='Validado', fecha_farmacia=? WHERE id=?
            """, (datetime.now().strftime("%d/%m/%Y %H:%M"), r["id"]))
            conn.commit()
            st.rerun()

        if col2.button("No validado", key=f"fno_{i}"):
            c.execute("""
            UPDATE requests SET estado='No validado Farmacia', fecha_farmacia=? WHERE id=?
            """, (datetime.now().strftime("%d/%m/%Y %H:%M"), r["id"]))
            conn.commit()
            st.rerun()

    # FECHAS
    if r["fecha_director"]:
        st.write(f"Director: {r['fecha_director']}")
    if r["fecha_farmacia"]:
        st.write(f"Farmacia: {r['fecha_farmacia']}")
