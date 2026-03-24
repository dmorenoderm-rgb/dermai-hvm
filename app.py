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
st.write("Gestión de Medicamentos de Alto Impacto en Dermatología")

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
pwd = st.sidebar.text_input("Contraseña", type="password")

if st.sidebar.button("Entrar"):
    if user in USERS and USERS[user]["pass"] == pwd:
        st.session_state.user = USERS[user]
        st.rerun()
    else:
        st.sidebar.error("Login incorrecto")

if not st.session_state.user:
    st.stop()

role = st.session_state.user["role"]
st.sidebar.success(f"Rol: {role}")

if st.sidebar.button("Cerrar sesión"):
    st.session_state.user = None
    st.rerun()

# ======================
# DB (ESTABLE)
# ======================
conn = sqlite3.connect("data.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS requests (
    id TEXT PRIMARY KEY,
    paciente TEXT,
    solicitante TEXT,
    enfermedad TEXT,
    tratamiento TEXT,
    estado TEXT,
    comentario TEXT,
    fecha TEXT,
    fecha_director TEXT,
    fecha_farmacia TEXT
)
""")
conn.commit()

# 🔹 AÑADIR ESTO (CLAVE)
c.execute("PRAGMA table_info(requests)")
columnas = [col[1] for col in c.fetchall()]

if "estado_director" not in columnas:
    c.execute("ALTER TABLE requests ADD COLUMN estado_director TEXT DEFAULT 'Pendiente'")

if "estado_farmacia" not in columnas:
    c.execute("ALTER TABLE requests ADD COLUMN estado_farmacia TEXT DEFAULT ''")

conn.commit()

# ======================
# DATOS
# ======================
solicitantes = [
    "Seleccionar","Dra. Carrizosa","Dra. Conejo-Mir","Dr. de la Torre","Dra. Eiris",
    "Dra. Fernández Orland","Dra. Ferrándiz","Dra. García Morales",
    "Dr. Marcos","Dra. Ojeda","Dr. Ruiz de Casas","Dra. Ruz",
    "Dra. Sánchez del Campo","Dr. Sánchez Leiro","Dra. Serrano",
]

protocolos = {
    "Seleccionar": [
    ],
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
        "Tralokinumab 300 mg/2 semanas",
        "Tralokinumab 300 mg/4 semanas",
        "Lebrikizumab 250 mg/2 semanas",
        "Lebrikizumab 250 mg/4 semanas",
        "Upadacitinib 15 mg",
        "Upadacitinib 30 mg",
        "Baricitinib 2 mg",
        "Baricitinib 4 mg",
        "Abrocitinib 100 mg",
        "Abrocitinib 200 mg",
    ],
    "Hidradenitis supurativa": [
        "Adalimumab semanal",
        "Secukinumab 300 mg/4 semanas",
        "Bimekizumab 320 mg/4 semanas",
    ],
    "Urticaria crónica espontánea": [
        "Omalizumab 300 mg/4 semanas"
    ],
    "Alopecia areata": [
        "Baricitinib 2 mg",
        "Baricitinib 4 mg",
        "Ritlecitinib 50 mg",
    ],
    "Vitíligo": [
        "Ruxolitinib crema 1,5%"
    ],
    "Melanoma": [
        "Nivolumab 240 mg/2 semanas",
        "Nivolumab 480 mg/4 semanas",
        "Pembrolizumab 200 mg/3 semanas",
        "Pembrolizumab 400 mg/6 semanas",
    ],
    "Carcinoma basocelular": [
        "Vismodegib 150 mg diario",
        "Sonidegib 200 mg diario",
    ],
    "Carcinoma escamoso cutáneo": [
        "Cemiplimab 350 mg/3 semanas",
        "Pembrolizumab 200 mg/3 semanas",
        "Pembrolizumab 400 mg/6 semanas",
    ],
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

    if st.button("Enviar solicitud"):
        if not re.fullmatch(r"AN\d{10}", paciente):
            st.error("Formato incorrecto")
        else:
            c.execute(
                "INSERT INTO requests (id, paciente, solicitante, enfermedad, tratamiento, estado, comentario, fecha, fecha_director, fecha_farmacia) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(uuid.uuid4()),
                    paciente,
                    solicitante,
                    enfermedad,
                    tratamiento,
                    "Pendiente Director",
                    "",
                    datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "",
                    ""
                )
            )
            conn.commit()
            st.success("Solicitud creada")
            st.rerun()

# ======================
# LISTADO (CLAVE)
# ======================
st.subheader("Solicitudes")

df = pd.read_sql_query("SELECT * FROM requests ORDER BY fecha DESC", conn)

if not df.empty:

    df_display = df.copy()

df_display["estado_detalle"] = df_display.apply(
    lambda x: f"{x['estado']} ({x['comentario']})"
    if x["estado"] == "No validado" and x["comentario"]
    else x["estado"],
    axis=1
)

st.dataframe(
    df_display[["paciente","solicitante","enfermedad","tratamiento","estado_detalle"]],
    use_container_width=True
)

# ======================
# ACCIONES
# ======================

if role != "Dermatólogo":

    for i, r in df.iterrows():
        
        # Mostrar solo pendientes en zona de acción
        if role == "Farmacia" and "Pendiente Farmacia" not in str(r["estado"]):
            continue

        if role == "Farmacia" and "Pendiente Farmacia" in str(r["estado"]):
            continue
    
        st.write("---")
        st.write(f"Paciente: {r['paciente']} | {r['tratamiento']} | Estado: {r['estado']}")
        if r["fecha_director"]:
            st.write(f"🩺 Validación Director: {r['fecha_director']}")

        if r["fecha_farmacia"]:
            st.write(f"💊 Farmacia: {r['fecha_farmacia']}")
            
        # DIRECTOR
        if role == "Director" and r["estado"] == "Pendiente Director":

            comentario = st.text_input("Motivo (opcional)", key=f"dir_{i}")

            col1, col2 = st.columns(2)

            if col1.button("Validar", key=f"val_{i}"):
                c.execute(
                    "UPDATE requests SET estado=?, fecha_director=? WHERE id=?",
                    ("Pendiente Farmacia", datetime.now().strftime("%d/%m/%Y %H:%M"), r["id"])
                )
                conn.commit()
                st.rerun()

            if col2.button("No validado", key=f"noval_{i}"):
                c.execute(
                    "UPDATE requests SET estado=?, comentario=?, fecha_director=? WHERE id=?",
                    ("No validado", comentario, datetime.now().strftime("%d/%m/%Y %H:%M"), r["id"])
                )
                conn.commit()
                st.rerun()

# ======================
# ELIMINAR REGISTRO (CLARO)
# ======================
if role == "Director" and not df.empty:

    st.subheader("Eliminar solicitud")

    # Crear etiqueta clara para identificar
    df["label"] = (
        df["paciente"] + " | " +
        df["solicitante"] + " | " +
        df["tratamiento"] + " | " +
        df["fecha"]
    )

    seleccion = st.selectbox(
        "Selecciona la solicitud a eliminar",
        df["label"]
    )

    # Obtener fila completa
    fila = df[df["label"] == seleccion].iloc[0]
    id_eliminar = fila["id"]

    # Mostrar claramente qué vas a borrar
    st.warning(
        f"⚠️ Vas a eliminar:\n\n"
        f"Paciente: {fila['paciente']}\n"
        f"Solicitante: {fila['solicitante']}\n"
        f"Tratamiento: {fila['tratamiento']}\n"
        f"Fecha: {fila['fecha']}"
    )

    # Confirmación simple
    if st.button("🗑️ Eliminar solicitud"):
        c.execute("DELETE FROM requests WHERE id = ?", (id_eliminar,))
        conn.commit()
        st.success("Registro eliminado")
        st.rerun()

# ======================
# FARMACIA
# ======================
if role == "Farmacia":

    for i, r in df.iterrows():

        if "Pendiente Farmacia" not in str(r["estado"]):
            continue

        st.write("---")
        st.write(f"{r['paciente']} | {r['tratamiento']}")

        comentario = st.text_input("Motivo (opcional)", key=f"far_{i}")

        col1, col2 = st.columns(2)

        if col1.button("Dispensar", key=f"disp_{i}"):
            c.execute(
                "UPDATE requests SET estado=?, fecha_farmacia=? WHERE id=?",
                ("Dispensar", datetime.now().strftime("%d/%m/%Y %H:%M"), r["id"])
            )
            conn.commit()
            st.rerun()

        if col2.button("No validado", key=f"rech_{i}"):
            c.execute(
                "UPDATE requests SET estado=?, comentario=?, fecha_farmacia=? WHERE id=?",
                ("No validado", comentario, datetime.now().strftime("%d/%m/%Y %H:%M"), r["id"])
            )
            conn.commit()
            st.rerun()
