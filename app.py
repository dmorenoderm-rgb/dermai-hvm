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
st.markdown("""
<div style='text-align:center;'>

<h1 style='color:#00B050; margin-bottom:5px;'>
DerMAI PRO
</h1>

<p style='color:#00B050; font-size:20px; margin:0;'>
Unidad de Dermatología MQyV
</p>

<p style='color:#00B050; font-size:18px; margin-top:5px;'>
Hospital Universitario Virgen Macarena
</p>

</div>
""", unsafe_allow_html=True)

# ======================
# LOGIN
# ======================
USERS = {
    "derma": {"pass": "123", "role": "Dermatólogo"},
    "director": {"pass": "000", "role": "Director"},
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
        "Secukinumab 150 mg/4 semanas",
        "Secukinumab 300 mg/4 semanas",
        "Ixekizumab 80 mg/4 semanas",
        "Guselkumab 100 mg/8 semanas",
        "Risankizumab 150 mg/12 semanas",
        "Tildrakizumab 100 mg/12 semanas",
        "Tildrakizumab 200 mg/12 semanas",
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
        "Adalimumab 40 mg/sem",
        "Adalimumab 80 mg/sem",
        "Adalimumab 40 mg/2sem",
        "Adalimumab 80 mg/2sem",
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
    "Carcinoma de células basales": [
        "Vismodegib 150 mg diario",
        "Sonidegib 200 mg diario",
    ],
    "Carcinoma de células escamosas": [
        "Cemiplimab 350 mg/3 semanas",
        "Pembrolizumab 200 mg/3 semanas",
        "Pembrolizumab 400 mg/6 semanas",
    ],
    "Linfoma cutáneo de células T": [
        "Bexaroteno 150-300mg/m2/d",
        "Clormetina tópica",
    ],
    "Eccema crónico de manos": [
        "Delgocitinib 20mg/g crema",
    ],
}

recomendaciones = {
    "Psoriasis en placas": "Adalimumab < Ustekinumab < Tildrakizumab < Bimekizumab",
    "Dermatitis atópica": "Dupilumab = Lebrikizumab < Upadacitinib",
    "Hidradenitis supurativa": "Adalimumab < Secukinumab < Bimekizumab",
    "Urticaria crónica espontánea": "Omalizumab biosimilar",
    "Alopecia areata": "Ritlecitinib",
    "Vitíligo": "Ruxolitinib crema",
    "Melanoma": "Anti-PD1 Pembrolizumab",
    "Carcinoma de células basales": "Sonidegib < Vismodegib",
    "Carcinoma de células escamosas": "Cemiplimab < Pembrolizumab",
    "Linfoma cutáneo de células T": "Metotrexato < Bexaroteno",
    "Eccema crónico de manos": "Corticoides tópicos < Alitretinoína < Delgocitinib",
}

criterios = {
    "Dermatitis atópica": {
        "indicacion": "Dermatitis atópica grave (EASI ≥21, BSA ≥10% o IGA ≥3), contraindicación o intolerancia a tratamiento tópico adecuado y a ciclosporina (o no candidato a la misma).",
        "objetivo": "EASI-75 a las 16 semanas."
    },
    "Psoriasis en placas": {
        "indicacion": "Psoriasis moderada-grave (PASI ≥10 o BSA ≥10% o DLQI ≥10) candidato a tratamiento sistémico.",
        "objetivo": "PASI-90 a las 16 semanas."
    },
    "Hidradenitis supurativa": {
        "indicación": "Hidradenitis supurativa moderada-grave (Hurley II–III) con afectación inflamatoria activa y fracaso de tratamiento antibiótico sistémico convencional.",
        "objetivo": "HiSCR (reducción ≥50% de abscesos y nódulos inflamatorios, sin aumento de abscesos ni fístulas) a las 12–16 semanas."
    },
    "Urticaria crónica espontánea": {
        "indicación": "Urticaria crónica espontánea moderada-grave con mal control pese a antihistamínicos H1 a dosis altas (x4).",
        "objetivo": "UAS7 ≤6 (idealmente 0) a las 12–16 semanas."
    },
    "Alopecia areata": {
        "indicación": "Alopecia areata grave SALT ≥50 o afectación extensa del cuero cabelludo y/o cejas/pestañas, episodios de repoblación <8 años, y fracaso de tratamientos previos (tópicos, intralesionales, sistémico convencional).",
        "objetivo": "Mejoría SALT ≤20 o reducción ≥50% del SALT a las 24–36 semanas."
    },
    "Vitíligo": {
        "indicación": "Vitíligo no segmentario cérvicofacial con afectación extensa >10% de superficie corporal refractario a tratamientos tópicos convecnionales (corticoides tópicos potentes, inhibidores de calcineurina).",
        "objetivo": "Repigmentación ≥50% facial (F-VASI50] a las 24 semanas."
    },
    "Eccema crónico de manos": {
        "indicación": "Eccema crónico de manos moderado–grave, persistente, con afectación funcional y/o impacto en calidad de vida, en pacientes con respuesta inadecuada, intolerancia o contraindicación a corticoides tópicos.",
        "objetivo": "Mejoría significativa ↓≥75% en HECSI/EHE, con NRS prurito ↓≥4 puntos o ≤3 en semana 16."
    },
}
    
# ======================
# FORMULARIO
# ======================
if role == "Dermatólogo":

    st.subheader("Nueva solicitud")

    paciente = st.text_input("Paciente (AN + 10 dígitos)")
    solicitante = st.selectbox("Solicitante", solicitantes)
    enfermedad = st.selectbox("Enfermedad", list(protocolos.keys()))
    data = criterios.get(enfermedad.strip())

    if isinstance(data, dict):
    
        indicacion = data.get("indicacion", "")
        objetivo = data.get("objetivo", "")

        if indicacion:
            st.markdown(f"**Indicación:** {indicacion}")

        if objetivo:
            st.markdown(f"**Objetivo terapéutico:** {objetivo}")
    if enfermedad in recomendaciones:
        st.info(f"📊 Recomendación: {recomendaciones[enfermedad]}")
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
df_display = df.copy()

df_display["fecha"] = df_display["fecha"].fillna("")
df_display["fecha_director"] = df_display["fecha_director"].fillna("")
df_display["fecha_farmacia"] = df_display["fecha_farmacia"].fillna("")

if not df.empty:

    df_display = df.copy()

df_display["fecha"] = df_display["fecha"].fillna("")
df_display["fecha_director"] = df_display["fecha_director"].fillna("")
df_display["fecha_farmacia"] = df_display["fecha_farmacia"].fillna("")

df_display["estado_detalle"] = df_display.apply(
    lambda x: f"{x['estado']} ({x['comentario']})"
    if x["estado"] == "No validado" and x["comentario"]
    else x["estado"],
    axis=1
)

st.dataframe(
    df_display[
        [
            "paciente",
            "solicitante",
            "enfermedad",
            "tratamiento",
            "estado_detalle",   # 👈 esto mantiene comentarios
            "fecha",
            "fecha_director",
            "fecha_farmacia"
        ]
    ],
    use_container_width=True
)

# ======================
# DESCARGAR EXCEL (SOLO DIRECTOR)
# ======================
if role == "Director":

    import io

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Solicitudes')

    excel_data = output.getvalue()

    st.download_button(
        label="📥 Descargar Excel",
        data=excel_data,
        file_name="solicitudes_dermai.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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

        if col1.button("Autorizado", key=f"disp_{i}"):
            c.execute(
                "UPDATE requests SET estado=?, fecha_farmacia=? WHERE id=?",
                ("Autorizado", datetime.now().strftime("%d/%m/%Y %H:%M"), r["id"])
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
