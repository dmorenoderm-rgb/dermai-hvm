import streamlit as st
import sqlite3
import uuid
from datetime import datetime
import pandas as pd
import re

st.set_page_config(layout="wide")
st.title("DerMAI PRO")

# ======================
# DB
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
# LOGIN SIMPLE
# ======================
roles = ["Dermatólogo", "Director", "Farmacia"]
role = st.sidebar.selectbox("Acceso", roles)

if role in ["Director", "Farmacia"]:
    password = st.sidebar.text_input("Contraseña", type="password")
    if password != "123":
        st.warning("Acceso restringido")
        st.stop()

# ======================
# SOLICITANTES
# ======================
solicitantes = [
    "Dra. Carrizosa","Dra. Conejo-Mir","Dr. de la Torre","Dra. Eiris",
    "Dra. Fernández Orland","Dra. Ferrándiz","Dra. García Morales",
    "Dr. Marcos","Dra. Ojeda","Dr. Ruiz de Casas","Dra. Ruz",
    "Dra. Sánchez del Campo","Dr. Sánchez Leiro","Dra. Serrano"
]

# ======================
# PROTOCOLOS COMPLETOS
# ======================
protocolos = {
    "Psoriasis en placas": [
        "Adalimumab 40 mg/2 semanas",
        "Ustekinumab 45 mg/12 semanas",
        "Ustekinumab 90 mg/12 semanas",
        "Secukinumab 300 mg/4 semanas",
        "Ixekizumab 80 mg/4 semanas",
        "Guselkumab 100 mg/8 semanas",
        "Risankizumab 150 mg/12 semanas",
        "Tildrakizumab 100 mg/12 semanas",
        "Bimekizumab 320 mg/8 semanas"
    ],
    "Dermatitis atópica": [
        "Dupilumab 300 mg/2 semanas",
        "Tralokinumab 300 mg/2 semanas",
        "Lebrikizumab 250 mg/2 semanas",
        "Upadacitinib 15 mg",
        "Upadacitinib 30 mg",
        "Baricitinib 2 mg",
        "Baricitinib 4 mg"
    ],
    "Hidradenitis supurativa": [
        "Adalimumab semanal",
        "Secukinumab 300 mg",
        "Bimekizumab 320 mg"
    ],
    "Urticaria crónica espontánea": [
        "Omalizumab 300 mg"
    ],
    "Alopecia areata": [
        "Baricitinib 2 mg",
        "Baricitinib 4 mg",
        "Ritlecitinib 50 mg"
    ],
    "Vitíligo": [
        "Ruxolitinib crema"
    ],
    "Melanoma": [
        "Nivolumab",
        "Pembrolizumab"
    ],
    "Carcinoma basocelular": [
        "Vismodegib",
        "Sonidegib"
    ],
    "Carcinoma escamoso cutáneo": [
        "Cemiplimab",
        "Pembrolizumab"
    ]
}

# ======================
# NUEVA SOLICITUD
# ======================
if role == "Dermatólogo":

    st.subheader("Nueva solicitud")

    paciente = st.text_input("Paciente (AN + 10 dígitos)", value="AN")
    solicitante = st.selectbox("Solicitante", solicitantes)
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
# ESTADO
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
# ACCIONES
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

    if r["fecha_director"]:
        st.write(f"Director: {r['fecha_director']}")
    if r["fecha_farmacia"]:
        st.write(f"Farmacia: {r['fecha_farmacia']}")
