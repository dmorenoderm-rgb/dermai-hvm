import streamlit as st
import sqlite3
import uuid
from datetime import datetime
import pandas as pd
import re

# ======================
# CONFIG
# ======================
st.set_page_config(layout="wide")
st.title("DerMAI PRO")
st.write("Gestión de Medicamentos Dermatología")

# ======================
# LOGIN
# ======================
USERS = {
    "derma": {"pass": "123", "role": "Dermatólogo"},
    "director": {"pass": "123", "role": "Director"},
    "farmacia": {"pass": "123", "role": "Farmacia"},
}

if "user" not in st.session_state:
    st.session_state.user = None

user = st.sidebar.text_input("Usuario")
pwd = st.sidebar.text_input("Password", type="password")

if st.sidebar.button("Entrar"):
    if user in USERS and USERS[user]["pass"] == pwd:
        st.session_state.user = USERS[user]
        st.rerun()
    else:
        st.sidebar.error("Login incorrecto")

if not st.session_state.user:
    st.stop()

role = st.session_state.user["role"]
st.sidebar.success(role)

# ======================
# DB (RESET LIMPIO)
# ======================
conn = sqlite3.connect("data.db", check_same_thread=False)
c = conn.cursor()

c.execute("DROP TABLE IF EXISTS requests")

c.execute(
    "CREATE TABLE requests ("
    "id TEXT,"
    "paciente TEXT,"
    "solicitante TEXT,"
    "enfermedad TEXT,"
    "tratamiento TEXT,"
    "estado TEXT,"
    "comentario TEXT,"
    "fecha TEXT)"
)

conn.commit()

# ======================
# DATOS
# ======================
solicitantes = [
    "Dra. Carrizosa","Dra. Conejo-Mir","Dr. de la Torre","Dra. Eiris",
    "Dra. Fernández Orland","Dra. Ferrándiz","Dra. García Morales",
    "Dr. Marcos","Dra. Ojeda","Dr. Ruiz de Casas","Dra. Ruz",
    "Dra. Sánchez del Campo","Dr. Sánchez Leiro","Dra. Serrano",
]

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
        "Bimekizumab 320 mg/8 semanas",
    ],
    "Dermatitis atópica": [
        "Dupilumab 300 mg/2 semanas",
        "Tralokinumab 300 mg",
        "Upadacitinib 15 mg",
        "Baricitinib 4 mg",
    ],
    "Hidradenitis supurativa": [
        "Adalimumab semanal",
        "Secukinumab 300 mg",
        "Bimekizumab 320 mg",
    ],
    "Melanoma": [
        "Nivolumab",
        "Pembrolizumab"
    ]
}

# ======================
# FORMULARIO
# ======================
if role == "Dermatólogo":

    st.subheader("Nueva solicitud")

    paciente = st.text_input("Paciente (AN + 10 dígitos)")
    solicitante = st.selectbox("Solicitante", solicitantes)
    enfermedad = st.selectbox("Enfermedad", list(protocolos.keys()))
    tratamiento = st.selectbox("Tratamiento", protocolos[enfermedad])

    if st.button("Enviar"):
        if not re.fullmatch(r"AN\d{10}", paciente):
            st.error("Formato incorrecto")
        else:
            c.execute(
                "INSERT INTO requests VALUES (?,?,?,?,?,?,?,?)",
                (
                    str(uuid.uuid4()),
                    paciente,
                    solicitante,
                    enfermedad,
                    tratamiento,
                    "Pendiente Director",
                    "",
                    datetime.now().strftime("%d/%m/%Y %H:%M"),
                ),
            )
            conn.commit()
            st.success("Solicitud creada")
            st.rerun()

# ======================
# LISTADO
# ======================
df = pd.read_sql_query("SELECT * FROM requests", conn)

st.subheader("Solicitudes")

if not df.empty:

    st.dataframe(df[["paciente","solicitante","enfermedad","tratamiento","estado"]])

    for i, r in df.iterrows():

        st.write("---")
        st.write(f"Paciente: {r['paciente']} | {r['tratamiento']} | Estado: {r['estado']}")

        # DIRECTOR
        if role == "Director" and r["estado"] == "Pendiente Director":

            comentario = st.text_input("Motivo (opcional)", key=f"dir_{i}")

            col1, col2 = st.columns(2)

            if col1.button("Validar", key=f"val_{i}"):
                c.execute("UPDATE requests SET estado='Validado' WHERE id=?", (r["id"],))
                conn.commit()
                st.rerun()

            if col2.button("No validado", key=f"noval_{i}"):
                c.execute("UPDATE requests SET estado=?, comentario=? WHERE id=?",
                          ("Rechazado Director", comentario, r["id"]))
                conn.commit()
                st.rerun()

        # FARMACIA
        if role == "Farmacia" and r["estado"] == "Validado":

            comentario = st.text_input("Motivo (opcional)", key=f"far_{i}")

            col1, col2 = st.columns(2)

            if col1.button("Dispensar", key=f"disp_{i}"):
                c.execute("UPDATE requests SET estado='Dispensado' WHERE id=?", (r["id"],))
                conn.commit()
                st.rerun()

            if col2.button("No validado", key=f"rech_{i}"):
                c.execute("UPDATE requests SET estado=?, comentario=? WHERE id=?",
                          ("Rechazado Farmacia", comentario, r["id"]))
                conn.commit()
                st.rerun()
