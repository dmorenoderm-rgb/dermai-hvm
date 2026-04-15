import io
import re
import uuid
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

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
# GOOGLE SHEETS DB
# ======================
SHEET_HEADERS = [
    "id",
    "paciente",
    "solicitante",
    "enfermedad",
    "tratamiento",
    "estado",
    "comentario",
    "fecha",
    "fecha_director",
    "fecha_farmacia",
]

def get_gsheet_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds_dict = {
        "type": st.secrets["gcp_service_account"]["type"],
        "project_id": st.secrets["gcp_service_account"]["project_id"],
        "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
        "private_key": st.secrets["gcp_service_account"]["private_key"],
        "client_email": st.secrets["gcp_service_account"]["client_email"],
        "client_id": st.secrets["gcp_service_account"]["client_id"],
        "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
        "token_uri": st.secrets["gcp_service_account"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"],
    }

    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

def get_worksheet():
    client = get_gsheet_client()
    spreadsheet_id = st.secrets["google_sheet"]["spreadsheet_id"]
    sheet_name = st.secrets["google_sheet"]["worksheet_name"]
    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet(sheet_name)
    ensure_sheet_headers(worksheet)
    return worksheet

def ensure_sheet_headers(worksheet):
    values = worksheet.get_all_values()
    if not values:
        worksheet.append_row(SHEET_HEADERS)

def get_requests_df():
    worksheet = get_worksheet()
    records = worksheet.get_all_records()

    if not records:
        return pd.DataFrame(columns=SHEET_HEADERS)

    df = pd.DataFrame(records)

    for col in SHEET_HEADERS:
        if col not in df.columns:
            df[col] = ""

    df = df[SHEET_HEADERS].fillna("")
    return df

def find_sheet_row_by_id(worksheet, request_id):
    ids = worksheet.col_values(1)  # columna A = id, fila 1 = cabecera
    for idx, val in enumerate(ids[1:], start=2):
        if val == request_id:
            return idx
    return None

def append_request(record):
    worksheet = get_worksheet()
    row = [record.get(col, "") for col in SHEET_HEADERS]
    worksheet.append_row(row)

def update_request_by_id(request_id, updates):
    worksheet = get_worksheet()
    row_num = find_sheet_row_by_id(worksheet, request_id)
    if row_num is None:
        raise ValueError("No se encontró la solicitud.")

    current_row = worksheet.row_values(row_num)
    if len(current_row) < len(SHEET_HEADERS):
        current_row += [""] * (len(SHEET_HEADERS) - len(current_row))

    row_dict = dict(zip(SHEET_HEADERS, current_row))
    for key, value in updates.items():
        if key in row_dict:
            row_dict[key] = value

    new_row = [row_dict.get(col, "") for col in SHEET_HEADERS]
    worksheet.update(f"A{row_num}:J{row_num}", [new_row])

def delete_request_by_id(request_id):
    worksheet = get_worksheet()
    row_num = find_sheet_row_by_id(worksheet, request_id)
    if row_num is None:
        raise ValueError("No se encontró la solicitud.")
    worksheet.delete_rows(row_num)

def sort_requests_df(df):
    if df.empty:
        return df.copy()

    df = df.copy()
    df["_fecha_sort"] = pd.to_datetime(df["fecha"], format="%d/%m/%Y %H:%M", errors="coerce")
    df = df.sort_values("_fecha_sort", ascending=False).drop(columns=["_fecha_sort"])
    return df

# ======================
# DATOS
# ======================
solicitantes = [
    "Seleccionar", "Dra. Carrizosa", "Dra. Conejo-Mir", "Dr. de la Torre", "Dra. Eiris",
    "Dra. Fernández Orland", "Dra. Ferrándiz", "Dra. García Morales",
    "Dr. Marcos", "Dra. Ojeda", "Dr. Ruiz de Casas", "Dra. Ruz",
    "Dra. Sánchez del Campo", "Dr. Sánchez Leiro", "Dra. Serrano",
]

protocolos = {
    "Seleccionar": [],
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
        "indicacion": "Hidradenitis supurativa moderada-grave (Hurley II–III) con afectación inflamatoria activa y fracaso de tratamiento antibiótico sistémico convencional.",
        "objetivo": "HiSCR (reducción ≥50% de abscesos y nódulos inflamatorios, sin aumento de abscesos ni fístulas) a las 12–16 semanas."
    },
    "Urticaria crónica espontánea": {
        "indicacion": "Urticaria crónica espontánea moderada-grave con mal control pese a antihistamínicos H1 a dosis altas (x4).",
        "objetivo": "UAS7 ≤6 (idealmente 0) a las 12–16 semanas."
    },
    "Alopecia areata": {
        "indicacion": "Alopecia areata grave SALT ≥50 o afectación extensa del cuero cabelludo y/o cejas/pestañas, episodios de repoblación <8 años, y fracaso de tratamientos previos (tópicos, intralesionales, sistémico convencional).",
        "objetivo": "Mejoría SALT ≤20 o reducción ≥50% del SALT a las 24–36 semanas."
    },
    "Vitíligo": {
        "indicacion": "Vitíligo no segmentario cérvicofacial con afectación extensa >10% de superficie corporal refractario a tratamientos tópicos convencionales (corticoides tópicos potentes, inhibidores de calcineurina).",
        "objetivo": "Repigmentación ≥50% facial (F-VASI50) a las 24 semanas."
    },
    "Eccema crónico de manos": {
        "indicacion": "Eccema crónico de manos moderado-grave, persistente, con afectación funcional y/o impacto en calidad de vida, en pacientes con respuesta inadecuada, intolerancia o contraindicación a corticoides tópicos.",
        "objetivo": "Mejoría significativa ≥75% en HECSI/EHE, con NRS prurito ↓≥4 puntos o ≤3 en semana 16."
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
        elif solicitante == "Seleccionar":
            st.error("Selecciona un solicitante")
        elif enfermedad == "Seleccionar":
            st.error("Selecciona una enfermedad")
        elif not tratamiento:
            st.error("Selecciona un tratamiento")
        else:
            append_request({
                "id": str(uuid.uuid4()),
                "paciente": paciente,
                "solicitante": solicitante,
                "enfermedad": enfermedad,
                "tratamiento": tratamiento,
                "estado": "Pendiente Director",
                "comentario": "",
                "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "fecha_director": "",
                "fecha_farmacia": "",
            })
            st.success("Solicitud creada")
            st.rerun()

# ======================
# LISTADO
# ======================
st.subheader("Solicitudes")

df = get_requests_df()
df = sort_requests_df(df)

if df.empty:
    st.info("No hay solicitudes registradas.")
else:
    df_display = df.copy()
    df_display["fecha"] = df_display["fecha"].fillna("")
    df_display["fecha_director"] = df_display["fecha_director"].fillna("")
    df_display["fecha_farmacia"] = df_display["fecha_farmacia"].fillna("")
    df_display["comentario"] = df_display["comentario"].fillna("")

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
                "estado_detalle",
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
if role == "Director" and not df.empty:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Solicitudes")

    st.download_button(
        label="📥 Descargar Excel",
        data=output.getvalue(),
        file_name="solicitudes_dermai.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ======================
# ACCIONES DIRECTOR
# ======================
if role == "Director" and not df.empty:
    st.subheader("Pendientes de validación")

    pendientes_dir = df[df["estado"] == "Pendiente Director"]

    if pendientes_dir.empty:
        st.info("No hay solicitudes pendientes del director.")
    else:
        for i, r in pendientes_dir.iterrows():
            st.write("---")
            st.write(f"Paciente: {r['paciente']} | {r['tratamiento']} | Estado: {r['estado']}")

            comentario = st.text_input("Motivo (opcional)", key=f"dir_{r['id']}")

            col1, col2 = st.columns(2)

            if col1.button("Validar", key=f"val_{r['id']}"):
                update_request_by_id(
                    r["id"],
                    {
                        "estado": "Pendiente Farmacia",
                        "fecha_director": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    }
                )
                st.rerun()

            if col2.button("No validado", key=f"noval_{r['id']}"):
                update_request_by_id(
                    r["id"],
                    {
                        "estado": "No validado",
                        "comentario": comentario,
                        "fecha_director": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    }
                )
                st.rerun()

# ======================
# ELIMINAR REGISTRO
# ======================
if role == "Director" and not df.empty:
    st.subheader("Eliminar solicitud")

    df_delete = df.copy()
    df_delete["label"] = (
        df_delete["paciente"].astype(str) + " | " +
        df_delete["solicitante"].astype(str) + " | " +
        df_delete["tratamiento"].astype(str) + " | " +
        df_delete["fecha"].astype(str)
    )

    seleccion = st.selectbox(
        "Selecciona la solicitud a eliminar",
        df_delete["label"].tolist()
    )

    fila = df_delete[df_delete["label"] == seleccion].iloc[0]

    st.warning(
        f"⚠️ Vas a eliminar:\n\n"
        f"Paciente: {fila['paciente']}\n"
        f"Solicitante: {fila['solicitante']}\n"
        f"Tratamiento: {fila['tratamiento']}\n"
        f"Fecha: {fila['fecha']}"
    )

    if st.button("🗑️ Eliminar solicitud"):
        delete_request_by_id(fila["id"])
        st.success("Registro eliminado")
        st.rerun()

# ======================
# FARMACIA
# ======================
if role == "Farmacia" and not df.empty:
    st.subheader("Pendientes de farmacia")

    pendientes_far = df[df["estado"] == "Pendiente Farmacia"]

    if pendientes_far.empty:
        st.info("No hay solicitudes pendientes de farmacia.")
    else:
        for i, r in pendientes_far.iterrows():
            st.write("---")
            st.write(f"{r['paciente']} | {r['tratamiento']}")

            comentario = st.text_input("Motivo (opcional)", key=f"far_{r['id']}")

            col1, col2 = st.columns(2)

            if col1.button("Autorizado", key=f"disp_{r['id']}"):
                update_request_by_id(
                    r["id"],
                    {
                        "estado": "Autorizado",
                        "fecha_farmacia": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    }
                )
                st.rerun()

            if col2.button("No validado", key=f"rech_{r['id']}"):
                update_request_by_id(
                    r["id"],
                    {
                        "estado": "No validado",
                        "comentario": comentario,
                        "fecha_farmacia": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    }
                )
                st.rerun()
