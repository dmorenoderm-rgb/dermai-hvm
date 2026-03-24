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
    estado_director TEXT,
    estado_farmacia TEXT,
    fecha TEXT,
    fecha_director TEXT,
    fecha_farmacia TEXT
)
""")
conn.commit()

# ======================
# LOGIN SIMPLE
# ======================
USUARIOS = {
    "director": {"password": "123", "rol": "Director"},
    "farmacia": {"password": "123", "rol": "Farmacia"},
    "derma": {"password": "123", "rol": "Dermatólogo"},
}

if "user" not in st.session_state:
    st.session_state.user = None

st.sidebar.subheader("Login")
user = st.sidebar.text_input("Usuario")
password = st.sidebar.text_input("Contraseña", type="password")

if st.sidebar.button("Entrar"):
    if user in USUARIOS and USUARIOS[user]["password"] == password:
        st.session_state.user = {
            "username": user,
            "role": USUARIOS[user]["rol"]
        }
        st.rerun()
    else:
        st.sidebar.error("Credenciales incorrectas")

if st.session_state.user is None:
    st.stop()

usuario = st.session_state.user["username"]
role = st.session_state.user["role"]

st.sidebar.success(f"Usuario: {usuario}")
st.sidebar.info(f"Rol: {role}")

if st.sidebar.button("Cerrar sesión"):
    st.session_state.user = None
    st.rerun()

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
        "Bimekizumab 320 mg/8 semanas",
    ],
    "Alopecia areata": [
        "Baricitinib 2 mg",
        "Baricitinib 4 mg"
    ],
    "Dermatitis atópica": [
        "Dupilumab 300 mg/2 semanas",
        "Tralokinumab 300 mg/2 semanas",
        "Upadacitinib 15 mg",
        "Upadacitinib 30 mg"
    ]
}

# ======================
# NUEVA SOLICITUD
# ======================
if role == "Dermatólogo":
    st.subheader("Nueva solicitud")

    paciente = st.text_input("Paciente (AN + 10 dígitos)", value="AN")
    solicitante = st.selectbox("Solicitante", ["Dra. Carrizosa", "Dr. Pérez", "Dra. López"])
    enfermedad = st.selectbox("Enfermedad", list(protocolos.keys()))
    tratamiento = st.selectbox("Tratamiento", protocolos[enfermedad])

    if st.button("Enviar solicitud"):
        paciente = paciente.strip().upper()

        if not re.fullmatch(r"AN\d{10}", paciente):
            st.error("Formato incorrecto")
        else:
            c.execute("""
            INSERT INTO requests VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                str(uuid.uuid4()),
                paciente,
                solicitante,
                enfermedad,
                tratamiento,
                "Pendiente",
                "",
                datetime.now().strftime("%d/%m/%Y %H:%M"),
                "",
                ""
            ))
            conn.commit()
            st.success("Solicitud creada")
            st.rerun()

# ======================
# ESTADO GLOBAL
# ======================
def estado_global(r):
    if r["estado_director"] == "Pendiente":
        return "Pendiente Director"
    elif r["estado_director"] == "No validado":
        return "No validado Director"
    elif r["estado_farmacia"] == "":
        return "Pendiente Farmacia"
    elif r["estado_farmacia"] == "No validado":
        return "No validado Farmacia"
    elif r["estado_farmacia"] == "Validado":
        return "Validado"
    return ""

# ======================
# TABLA PRINCIPAL (SOLO UNA)
# ======================
st.subheader("Solicitudes")

df = pd.read_sql_query("SELECT * FROM requests ORDER BY fecha DESC", conn)

if not df.empty:
    df["Estado"] = df.apply(estado_global, axis=1)

    st.dataframe(
        df[["paciente","solicitante","enfermedad","tratamiento","Estado"]],
        use_container_width=True
    )

# ======================
# ZONA DE ACCIÓN (SIN DUPLICAR)
# ======================
st.subheader("Acciones")

for i, r in df.iterrows():

    # FILTROS POR ROL (CLAVE PARA QUE NO DUPLIQUE)
    if role == "Director" and r["estado_director"] != "Pendiente":
        continue

    if role == "Farmacia" and (r["estado_director"] != "Validado" or r["estado_farmacia"] != ""):
        continue

    st.write("---")
    st.write(f"{r['paciente']} | {r['tratamiento']}")

    # DIRECTOR
    if role == "Director":
        col1, col2 = st.columns(2)

        if col1.button("Validar", key=f"val_{i}"):
            c.execute("""
            UPDATE requests SET
                estado_director='Validado',
                fecha_director=?
            WHERE id=?
            """, (datetime.now().strftime("%d/%m/%Y %H:%M"), r["id"]))
            conn.commit()
            st.rerun()

        if col2.button("No validado", key=f"noval_{i}"):
            c.execute("""
            UPDATE requests SET
                estado_director='No validado',
                fecha_director=?
            WHERE id=?
            """, (datetime.now().strftime("%d/%m/%Y %H:%M"), r["id"]))
            conn.commit()
            st.rerun()

    # FARMACIA
    if role == "Farmacia":
        col1, col2 = st.columns(2)

        if col1.button("Validar", key=f"fval_{i}"):
            c.execute("""
            UPDATE requests SET
                estado_farmacia='Validado',
                fecha_farmacia=?
            WHERE id=?
            """, (datetime.now().strftime("%d/%m/%Y %H:%M"), r["id"]))
            conn.commit()
            st.rerun()

        if col2.button("No validado", key=f"fnoval_{i}"):
            c.execute("""
            UPDATE requests SET
                estado_farmacia='No validado',
                fecha_farmacia=?
            WHERE id=?
            """, (datetime.now().strftime("%d/%m/%Y %H:%M"), r["id"]))
            conn.commit()
            st.rerun()

    # FECHAS
    if r["fecha_director"]:
        st.write(f"👨‍⚕️ Director: {r['fecha_director']}")
    if r["fecha_farmacia"]:
        st.write(f"💊 Farmacia: {r['fecha_farmacia']}")
