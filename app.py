import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import re
import random
import time
from datetime import datetime, timezone, timedelta
from google import genai

# Zona horaria de Argentina (UTC-3)
TZ_ARG = timezone(timedelta(hours=-3))

# Librería para gráficos interactivos
try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# -------------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA Y ACCESOS
# -------------------------------------------------------------
st.set_page_config(
    page_title="Inteligencia Operativa de Canal",
    page_icon="📊",
    layout="wide"
)

# Estilo CSS de alto contraste: Bordes oscuros y bien visibles para todos los campos
st.markdown("""
<style>
/* Borde oscuro y visible para todos los inputs */
.stTextInput input, 
div[data-baseweb="input"], 
div[data-baseweb="base-input"] {
    background-color: #ffffff !important;
    border: 2px solid #334155 !important; /* Borde oscuro bien marcado */
    border-radius: 8px !important;
    color: #0f172a !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
}

/* Al pasar el mouse */
.stTextInput input:hover, 
div[data-baseweb="input"]:hover {
    border-color: #0f172a !important;
}

/* Al hacer clic/foco para escribir */
.stTextInput input:focus, 
div[data-baseweb="input"]:focus-within {
    border-color: #2563eb !important; /* Azul vibrante */
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.25) !important;
}

/* Estilo para los títulos de los campos */
.stTextInput label {
    font-weight: 600 !important;
    color: #1e293b !important;
}
</style>
""", unsafe_allow_html=True)

AVATAR_BOT = "bot_avatar.png" if os.path.exists("bot_avatar.png") else "🤖"

PASSWORD_ACCESO = st.secrets.get("APP_PASSWORD", "atencion2026")
PASSWORD_ADMIN = st.secrets.get("ADMIN_PASSWORD", "pirania9")

# Frases aleatorias de Los Simpson para el spinner
FRASES_SIMPSON = [
    "¡A la grande le puse cuca! Estamos en ello....",
    "¿Dónde está mi submarino amarillo?",
    "¡No está aquí! ¡No está aquí! ¡No está aquí! ... Bueno, si esta Aqui..",
    "A buscar tesoros... o a morir en el intento",
    "Ya merito llega...",
    "¡Pronto... muy pronto!",
    "Mi aparato cerebral está pensando...",
    "Cargando... por favor, inserte disquete 3 de 4",
    "Homero no poder pensar ahora, está trabajando",
    "Estoy procesando la información... A ver, espérame tantito"
]

CARPETA_DATOS = "usuarios_data"
os.makedirs(CARPETA_DATOS, exist_ok=True)
PATH_USUARIOS = os.path.join(CARPETA_DATOS, "usuarios.json")
PATH_FECHA_BASE = "fecha_actualizacion.txt"

def cargar_usuarios():
    if os.path.exists(PATH_USUARIOS):
        try:
            with open(PATH_USUARIOS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def guardar_usuarios(db):
    try:
        with open(PATH_USUARIOS, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Error al guardar usuario: {e}")

def cargar_historial_usuario(user_id):
    path_hist = os.path.join(CARPETA_DATOS, f"historial_{user_id}.json")
    if os.path.exists(path_hist):
        try:
            with open(path_hist, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return [
        {
            "role": "assistant",
            "content": "¡Hola! Soy el **Agente Único Master de Inteligencia Operativa**.\n\nTengo cargada la base de datos consolidada del canal. Puedes realizarme consultas sobre TMO, NPS, Transferencias y tasas SPL a Nivel Canal, PCRC o Proveedor.\n\n💡 **Tip:** ¡También puedes pedirme gráficos de líneas, barras o tortas!",
            "chart": None
        }
    ]

def guardar_historial_usuario(user_id, messages):
    path_hist = os.path.join(CARPETA_DATOS, f"historial_{user_id}.json")
    try:
        with open(path_hist, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Error al guardar historial: {e}")

def obtener_fecha_base():
    if os.path.exists(PATH_FECHA_BASE):
        try:
            with open(PATH_FECHA_BASE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            pass
    return datetime.now(TZ_ARG).strftime('%d/%m/%Y %H:%M')

def guardar_fecha_base():
    try:
        ahora_arg = datetime.now(TZ_ARG).strftime('%d/%m/%Y %H:%M')
        with open(PATH_FECHA_BASE, "w", encoding="utf-8") as f:
            f.write(ahora_arg)
    except Exception as e:
        st.error(f"Error al registrar fecha: {e}")

# Control de Acceso en Dos Pasos, Centrado y en Tarjeta Destacada
def check_password():
    if "general_authenticated" not in st.session_state:
        st.session_state.general_authenticated = False
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.current_user = None
        st.session_state.user_display = ""

    if st.session_state.authenticated:
        return True

    col_izq, col_centro, col_der = st.columns([1.2, 1.8, 1.2])

    with col_centro:
        with st.container(border=True):
            if os.path.exists("bot_avatar.png"):
                ci1, ci2, ci3 = st.columns([1, 1.2, 1])
                with ci2:
                    st.image("bot_avatar.png", width=110)

            # PASO 1: Contraseña General
            if not st.session_state.general_authenticated:
                st.markdown("<h2 style='text-align: center; margin-bottom: 0;'>🔒 Acceso al Canal</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: #64748b;'>Paso 1 de 2: Ingresa la contraseña general</p>", unsafe_allow_html=True)
                st.write("")
                
                pwd = st.text_input("Contraseña General:", type="password", key="general_pwd", placeholder="Ingresa la contraseña aquí...")
                st.write("")
                if st.button("Continuar ➡️", type="primary", use_container_width=True):
                    if pwd == PASSWORD_ACCESO:
                        st.session_state.general_authenticated = True
                        st.rerun()
                    else:
                        st.error("Contraseña general incorrecta.")
                return False

            # PASO 2: Usuario y PIN
            else:
                st.markdown("<h2 style='text-align: center; margin-bottom: 0;'>👤 Tu Identificación</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: #64748b;'>Paso 2 de 2: Accede a tus consultas privadas</p>", unsafe_allow_html=True)
                st.write("")
                
                usuario_input = st.text_input("Nombre de Usuario o Legajo:", placeholder="Ej: mauro.r o tu legajo").strip()
                pin_input = st.text_input("PIN personal (4 dígitos):", type="password", max_chars=4, placeholder="****").strip()
                st.write("")
                
                col_b1, col_b2 = st.columns([2, 1])
                with col_b1:
                    boton_entrar = st.button("Ingresar al Agente 🚀", type="primary", use_container_width=True)
                with col_b2:
                    if st.button("⬅️ Volver", use_container_width=True):
                        st.session_state.general_authenticated = False
                        st.rerun()

                if boton_entrar:
                    if not usuario_input:
                        st.error("Ingresa tu nombre o legajo.")
                        return False
                    if not pin_input or len(pin_input) < 4 or not pin_input.isdigit():
                        st.error("El PIN debe tener exactamente 4 números.")
                        return False

                    user_id = re.sub(r'[^a-zA-Z0-9_]', '', usuario_input.lower().replace(" ", "_"))
                    usuarios_db = cargar_usuarios()

                    if user_id in usuarios_db:
                        if usuarios_db[user_id]["pin"] == pin_input:
                            st.session_state.authenticated = True
                            st.session_state.current_user = user_id
                            st.session_state.user_display = usuarios_db[user_id].get("nombre", usuario_input)
                            st.session_state.messages = cargar_historial_usuario(user_id)
                            st.rerun()
                        else:
                            st.error("El usuario ya existe, pero el PIN es incorrecto.")
                            return False
                    else:
                        usuarios_db[user_id] = {
                            "nombre": usuario_input,
                            "pin": pin_input,
                            "fecha_registro": datetime.now(TZ_ARG).strftime("%d/%m/%Y %H:%M")
                        }
                        guardar_usuarios(usuarios_db)
                        st.session_state.authenticated = True
                        st.session_state.current_user = user_id
                        st.session_state.user_display = usuario_input
                        st.session_state.messages = cargar_historial_usuario(user_id)
                        st.rerun()

                return False

if not check_password():
    st.stop()

# -------------------------------------------------------------
# 2. CARGA INTELIGENTE Y ACTUALIZACIÓN EN DISCO PARA TODOS
# -------------------------------------------------------------
def leer_archivo_robusto(origen):
    try:
        if isinstance(origen, str):
            if origen.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(origen)
            else:
                df = pd.read_csv(origen)
        else:
            if origen.name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(origen)
            else:
                df = pd.read_csv(origen)
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return None

    cols_actuales = [str(c).upper().strip() for c in df.columns]
    if not any("PERIODO" in c for c in cols_actuales):
        for i in range(min(15, len(df))):
            fila_valores = [str(v).upper().strip() for v in df.iloc[i].values]
            if any("PERIODO" in v for v in fila_valores) or any("PCRC" in v or "PRCR" in v for v in fila_valores):
                df.columns = [str(v).strip() for v in df.iloc[i].values]
                df = df.iloc[i + 1:].reset_index(drop=True)
                break

    mapa_cols = {}
    for c in df.columns:
        c_limpio = str(c).strip()
        c_u = c_limpio.upper()
        if c_u == "PERIODO":
            mapa_cols[c] = "Periodo"
        elif c_u in ["PCRC", "PRCR"]:
            mapa_cols[c] = "PCRC"
        elif c_u == "PROVEEDOR":
            mapa_cols[c] = "PROVEEDOR"
        else:
            mapa_cols[c] = c_limpio
    df = df.rename(columns=mapa_cols)
    df = df.loc[:, ~df.columns.duplicated()]
    return df

@st.cache_data
def cargar_datos_base():
    if os.path.exists("base_datos.xlsx"):
        return leer_archivo_robusto("base_datos.xlsx"), "base_datos.xlsx"
    elif os.path.exists("base_datos.csv"):
        return leer_archivo_robusto("base_datos.csv"), "base_datos.csv"
    return None, None

df_base, nombre_archivo_base = cargar_datos_base()

# Control de estado del Panel de Administrador
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

with st.sidebar.expander("🔒 Panel de Administrador"):
    if not st.session_state.admin_authenticated:
        clave_admin = st.text_input("Contraseña de administrador:", type="password", key="admin_key_input")
        if st.button("Acceder como Admin", use_container_width=True):
            if clave_admin == PASSWORD_ADMIN:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
    else:
        st.success("Acceso de Administrador concedido.")
        
        # Botón para salir y bloquear de nuevo
        if st.button("🔒 Volver y Bloquear Panel", use_container_width=True):
            st.session_state.admin_authenticated = False
            st.rerun()

        st.write("---")
        archivo_subido = st.file_uploader("Subir nuevo Excel o CSV", type=["xlsx", "xls", "csv"])
        if archivo_subido is not None:
            df_nuevo = leer_archivo_robusto(archivo_subido)
            if df_nuevo is not None and "Periodo" in df_nuevo.columns:
                nombre_destino = "base_datos.xlsx" if archivo_subido.name.endswith(('.xlsx', '.xls')) else "base_datos.csv"
                with open(nombre_destino, "wb") as f:
                    f.write(archivo_subido.getbuffer())
                
                guardar_fecha_base()
                st.cache_data.clear()
                st.success("✅ Base guardada en disco para todo el equipo.")
                st.rerun()
            else:
                st.error("No se pudo detectar la columna Periodo en el archivo subido.")
        
        # Gestión de Usuarios Registrados
        st.write("---")
        st.markdown("**👥 Usuarios registrados:**")
        db_users = cargar_usuarios()
        if db_users:
            for uid, info in db_users.items():
                st.caption(f"• **{info.get('nombre', uid)}** (Creado: {info.get('fecha_registro', 'N/D')})")
            
            st.markdown("##### 🗑️ Eliminar Usuario")
            uids_disponibles = list(db_users.keys())
            user_a_eliminar = st.selectbox(
                "Seleccionar usuario:",
                options=uids_disponibles,
                format_func=lambda u: f"{db_users[u].get('nombre', u)} ({u})"
            )
            
            if st.button("Eliminar usuario y su historial", type="secondary", use_container_width=True):
                nombre_del = db_users[user_a_eliminar].get("nombre", user_a_eliminar)
                del db_users[user_a_eliminar]
                guardar_usuarios(db_users)

                path_h = os.path.join(CARPETA_DATOS, f"historial_{user_a_eliminar}.json")
                if os.path.exists(path_h):
                    try:
                        os.remove(path_h)
                    except Exception:
                        pass

                st.success(f"Usuario '{nombre_del}' y su historial fueron eliminados.")
                st.rerun()
        else:
            st.caption("No hay usuarios registrados aún.")

if df_base is None or "Periodo" not in df_base.columns:
    st.error("No se encontró el archivo de base de datos o falta la columna 'Periodo'.")
    if df_base is not None:
        st.write("Columnas detectadas:", list(df_base.columns))
    st.stop()

# -------------------------------------------------------------
# 3. MOTOR DE CÁLCULO EXACTO EN PYTHON (CERO ALUCINACIÓN)
# -------------------------------------------------------------
COLS_NUM = [
    'Tiempo ACW in', 'Tiempo Saliente', 'Tiempo TT', 'Tiempo Hold', 'Q TMO',
    'REP 1L', 'REP 2L', 'RetencionTransf', 'TecnicaTransfResto', 'TecnicaTransfPrio',
    'ComplejasTransf', 'Q llamadas', 'Promotores', 'detractor', 'Q meda',
    'Res si', 'Q Res', 'Q SPL30 Reiterados', 'Q SPL48 Reiterados',
    'Q SPL7 Reiterados', 'Q SPL Atendidos'
]

for col in COLS_NUM:
    if col in df_base.columns:
        df_base[col] = pd.to_numeric(df_base[col], errors='coerce').fillna(0)
    else:
        df_base[col] = 0

df_base['Periodo_DT'] = pd.to_datetime(df_base['Periodo'], errors='coerce')
df_base['Periodo_Str'] = df_base['Periodo_DT'].dt.strftime('%Y-%m').fillna(df_base['Periodo'].astype(str))

def computar_kpis(df_grp):
    q_tmo = df_grp['Q TMO'].replace(0, np.nan)
    tmo_seg = (df_grp['Tiempo ACW in'] + df_grp['Tiempo Saliente'] + df_grp['Tiempo TT'] + df_grp['Tiempo Hold']) / q_tmo
    acw_seg = df_grp['Tiempo ACW in'] / q_tmo
    sal_seg = df_grp['Tiempo Saliente'] / q_tmo
    tt_seg = df_grp['Tiempo TT'] / q_tmo
    hold_seg = df_grp['Tiempo Hold'] / q_tmo
    
    q_ll = df_grp['Q llamadas'].replace(0, np.nan)
    transf_1l = (df_grp['REP 1L'] / q_ll) * 100
    transf_2l = (df_grp['REP 2L'] / q_ll) * 100
    transf_tot = ((df_grp['REP 1L'] + df_grp['REP 2L']) / q_ll) * 100
    transf_ret = (df_grp['RetencionTransf'] / q_ll) * 100
    transf_tec = (df_grp['TecnicaTransfResto'] / q_ll) * 100
    transf_coe = (df_grp['TecnicaTransfPrio'] / q_ll) * 100
    transf_comp = (df_grp['ComplejasTransf'] / q_ll) * 100
    
    q_meda = df_grp['Q meda'].replace(0, np.nan)
    nps = ((df_grp['Promotores'] - df_grp['detractor']) / q_meda) * 100
    prom = (df_grp['Promotores'] / q_meda) * 100
    detr = (df_grp['detractor'] / q_meda) * 100
    
    q_res = df_grp['Q Res'].replace(0, np.nan)
    resolucion = (df_grp['Res si'] / q_res) * 100
    
    q_spl = df_grp['Q SPL Atendidos'].replace(0, np.nan)
    spl30 = (1 - (df_grp['Q SPL30 Reiterados'] / q_spl)) * 100
    spl48 = (1 - (df_grp['Q SPL48 Reiterados'] / q_spl)) * 100
    spl7 = (1 - (df_grp
