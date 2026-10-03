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

# Zona horaria fija de Argentina (UTC-3)
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

# Estilo CSS de alto contraste y compresión de panel
st.markdown("""
<style>
/* Borde oscuro y visible para todos los inputs */
.stTextInput input, 
div[data-baseweb="input"], 
div[data-baseweb="base-input"] {
    background-color: #ffffff !important;
    border: 2px solid #334155 !important;
    border-radius: 8px !important;
    color: #0f172a !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
}

.stTextInput input:hover, 
div[data-baseweb="input"]:hover {
    border-color: #0f172a !important;
}

.stTextInput input:focus, 
div[data-baseweb="input"]:focus-within {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.25) !important;
}

.stTextInput label {
    font-weight: 600 !important;
    color: #1e293b !important;
}

/* Botones principales destacados */
div.stButton > button[kind="primary"] {
    background-color: #2563eb !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    border: none !important;
    padding: 0.5rem 1rem !important;
}
div.stButton > button[kind="primary"]:hover {
    background-color: #1d4ed8 !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
}

/* Reducción de espaciados en la barra lateral para evitar scroll */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    gap: 0.32rem !important;
}
[data-testid="stSidebar"] {
    padding-top: 0.8rem !important;
    padding-bottom: 0.5rem !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] {
    margin-bottom: 0.15rem !important;
}
[data-testid="stSidebar"] button {
    padding: 0.3rem 0.5rem !important;
    font-size: 0.82rem !important;
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

# Memoria global de presencia en tiempo real compartida entre todos los usuarios
@st.cache_resource
def get_presencia_global():
    return {}

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
    except Exception:
        pass

def cargar_historial_usuario(user_id):
    path_h = os.path.join(CARPETA_DATOS, f"historial_{user_id}.json")
    if os.path.exists(path_h):
        try:
            with open(path_h, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return [{
        "role": "assistant",
        "content": f"¡Hola **{st.session_state.get('user_display', 'Analista')}**! Soy tu Agente Master de Inteligencia Operativa. Consulta métricas de TMO, NPS, SPL y Transferencias por Canal, PCRC o Proveedor.",
        "chart": None
    }]

def guardar_historial_usuario(user_id, messages):
    path_h = os.path.join(CARPETA_DATOS, f"historial_{user_id}.json")
    try:
        with open(path_h, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def obtener_fecha_base(archivo_actual):
    if os.path.exists(PATH_FECHA_BASE):
        try:
            with open(PATH_FECHA_BASE, "r", encoding="utf-8") as f:
                f_txt = f.read().strip()
                if f_txt:
                    return f_txt
        except Exception:
            pass
            
    ahora_arg = datetime.now(TZ_ARG)
    fecha_defecto = ahora_arg.strftime('%d/%m/%Y %H:%M')
    guardar_fecha_base(fecha_defecto)
    return fecha_defecto

def guardar_fecha_base(fecha_str=None):
    if not fecha_str:
        fecha_str = datetime.now(TZ_ARG).strftime('%d/%m/%Y %H:%M')
    try:
        with open(PATH_FECHA_BASE, "w", encoding="utf-8") as f:
            f.write(fecha_str)
    except Exception:
        pass

# Control de Autenticación
if "general_authenticated" not in st.session_state:
    st.session_state.general_authenticated = False
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "user_display" not in st.session_state:
    st.session_state.user_display = ""
if "messages" not in st.session_state:
    st.session_state.messages = []

def check_password():
    if st.session_state.authenticated:
        return True

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        col_img, col_txt = st.columns([0.25, 0.75], vertical_alignment="center")
        with col_img:
            if os.path.exists("bot_avatar.png"):
                st.image("bot_avatar.png", width=80)
            else:
                st.markdown("## 🤖")
        with col_txt:
            st.markdown("### Inteligencia Operativa")
            st.caption("Acceso al Agente Inteligente de Canal")

        if not st.session_state.general_authenticated:
            st.info("🔒 Ingresa la contraseña general del sistema:")
            pwd = st.text_input("Contraseña de Acceso", type="password", key="general_pwd_input")
            if st.button("Continuar", key="btn_general_pwd", type="primary", use_container_width=True):
                if pwd == PASSWORD_ACCESO:
                    st.session_state.general_authenticated = True
                    st.rerun()
                else:
                    st.error("Contraseña general incorrecta.")
            return False
        else:
            st.success("✅ Acceso general validado")
            st.markdown("#### Identificación de Usuario")
            
            usuarios_db = cargar_usuarios()
            tipo_ingreso = st.radio("Elige una opción:", ["Ingresar con mi usuario", "Registrarme como nuevo usuario"], horizontal=True)

            if tipo_ingreso == "Ingresar con mi usuario":
                usuario_input = st.text_input("Usuario o Legajo:", key="login_user_input").strip()
                pin_input = st.text_input("PIN personal (4 dígitos):", type="password", max_chars=4, key="login_pin_input").strip()
                
                if st.button("Iniciar Sesión", key="btn_login", type="primary", use_container_width=True):
                    user_id = usuario_input.lower()
                    if not user_id or not pin_input:
                        st.warning("Completa tu usuario y PIN.")
                    elif user_id not in usuarios_db:
                        st.error("El usuario no existe. Selecciona 'Registrarme como nuevo usuario'.")
                    elif usuarios_db[user_id]["pin"] != pin_input:
                        st.error("PIN incorrecto.")
                    else:
                        st.session_state.authenticated = True
                        st.session_state.current_user = user_id
                        st.session_state.user_display = usuarios_db[user_id].get("nombre", usuario_input)
                        st.session_state.messages = cargar_historial_usuario(user_id)
                        st.rerun()

                return False
            else:
                st.info("Crea tu usuario personal:")
                usuario_input = st.text_input("Nombre de usuario o Legajo (Identificador):", key="reg_user_input").strip()
                nombre_real = st.text_input("Tu Nombre Completo (como quieres que te llame el bot):", key="reg_name_input").strip()
                pin_input = st.text_input("Crea un PIN numérico de 4 dígitos:", type="password", max_chars=4, key="reg_pin_input").strip()
                
                if st.button("Crear Usuario y Entrar", key="btn_register", type="primary", use_container_width=True):
                    user_id = usuario_input.lower()
                    if not user_id or not pin_input or not nombre_real:
                        st.warning("Completa todos los campos.")
                    elif not pin_input.isdigit() or len(pin_input) != 4:
                        st.warning("El PIN debe ser exactamente de 4 números.")
                    elif user_id in usuarios_db:
                        st.error("Este usuario ya existe. Por favor inicia sesión.")
                    else:
                        usuarios_db[user_id] = {
                            "nombre": nombre_real,
                            "pin": pin_input,
                            "fecha_registro": datetime.now(TZ_ARG).strftime('%d/%m/%Y %H:%M')
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

# Actualizar latido de presencia en línea del usuario actual
if st.session_state.authenticated and st.session_state.current_user:
    presencia = get_presencia_global()
    presencia[st.session_state.current_user] = {
        "nombre": st.session_state.user_display,
        "last_seen": time.time()
    }

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

        # Monitoreo de Usuarios en Línea en Tiempo Real (Exclusivo Administrador)
        st.write("---")
        st.markdown("##### 🟢 Usuarios en Línea en Tiempo Real")
        presencia_admin = get_presencia_global()
        ahora_admin = time.time()
        activos_admin = {uid: info for uid, info in presencia_admin.items() if ahora_admin - info.get("last_seen", 0) < 300}

        if activos_admin:
            st.caption(f"Hay **{len(activos_admin)}** usuario(s) navegando en este momento:")
            for uid, info in activos_admin.items():
                min_inactividad = int((ahora_admin - info.get("last_seen", 0)) / 60)
                tiempo_str = "hace instantes" if min_inactividad == 0 else f"hace {min_inactividad} min"
                st.write(f"• 🟢 **{info.get('nombre', uid)}** (`{uid}`) — *{tiempo_str}*")
        else:
            st.caption("No hay otros usuarios en línea actualmente.")

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
    transf_tec_resto = (df_grp['TecnicaTransfResto'] / q_ll) * 100
    transf_tec_prio = (df_grp['TecnicaTransfPrio'] / q_ll) * 100
    transf_comp = (df_grp['ComplejasTransf'] / q_ll) * 100
    
    q_meda = df_grp['Q meda'].replace(0, np.nan)
    nps = ((df_grp['Promotores'] - df_grp['detractor']) / q_meda) * 100
    
    q_res = df_grp['Q Res'].replace(0, np.nan)
    resolucion = (df_grp['Res si'] / q_res) * 100
    
    q_atend = df_grp['Q SPL Atendidos'].replace(0, np.nan)
    spl7 = (df_grp['Q SPL7 Reiterados'] / q_atend) * 100
    spl30 = (df_grp['Q SPL30 Reiterados'] / q_atend) * 100
    spl48 = (df_grp['Q SPL48 Reiterados'] / q_atend) * 100
    
    res = pd.DataFrame({
        'TMO (s)': tmo_seg.round(1),
        'ACW (s)': acw_seg.round(1),
        'Saliente (s)': sal_seg.round(1),
        'TT (s)': tt_seg.round(1),
        'Hold (s)': hold_seg.round(1),
        'NPS (%)': nps.round(2),
        'Resolucion (%)': resolucion.round(2),
        'SPL 7 (%)': spl7.round(2),
        'SPL 30 (%)': spl30.round(2),
        'SPL 48 (%)': spl48.round(2),
        'Transf Totales (%)': transf_tot.round(2),
        'Transf 1L (%)': transf_1l.round(2),
        'Transf 2L (%)': transf_2l.round(2),
        'Retencion Transf (%)': transf_ret.round(2),
        'Tecnica Resto (%)': transf_tec_resto.round(2),
        'Tecnica Prio (%)': transf_tec_prio.round(2),
        'Complejas Transf (%)': transf_comp.round(2),
        'Q Llamadas': df_grp['Q llamadas'].astype(int),
        'Q TMO': df_grp['Q TMO'].astype(int),
        'Q Meda NPS': df_grp['Q meda'].astype(int),
        'Q SPL Atendidos': df_grp['Q SPL Atendidos'].astype(int)
    })
    return res

@st.cache_data
def generar_tablas_consolidadas(df_entrada):
    # Nivel 1: Total Canal
    g_canal = df_entrada.groupby('Periodo_Str')[COLS_NUM].sum().reset_index()
    t_canal = computar_kpis(g_canal)
    t_canal.insert(0, 'Periodo', g_canal['Periodo_Str'])
    
    # Nivel 2: Por PCRC
    if 'PCRC' in df_entrada.columns:
        g_pcrc = df_entrada.groupby(['Periodo_Str', 'PCRC'])[COLS_NUM].sum().reset_index()
        t_pcrc = computar_kpis(g_pcrc)
        t_pcrc.insert(0, 'PCRC', g_pcrc['PCRC'])
        t_pcrc.insert(0, 'Periodo', g_pcrc['Periodo_Str'])
    else:
        t_pcrc = pd.DataFrame()
        
    # Nivel 3: Por Proveedor PURO (Global por Proveedor)
    if 'PROVEEDOR' in df_entrada.columns:
        g_prov = df_entrada.groupby(['Periodo_Str', 'PROVEEDOR'])[COLS_NUM].sum().reset_index()
        t_prov = computar_kpis(g_prov)
        t_prov.insert(0, 'PROVEEDOR', g_prov['PROVEEDOR'])
        t_prov.insert(0, 'Periodo', g_prov['Periodo_Str'])
    else:
        t_prov = pd.DataFrame()

    # Nivel 4: Por PCRC y Proveedor
    if 'PCRC' in df_entrada.columns and 'PROVEEDOR' in df_entrada.columns:
        g_pcrc_prov = df_entrada.groupby(['Periodo_Str', 'PCRC', 'PROVEEDOR'])[COLS_NUM].sum().reset_index()
        t_pcrc_prov = computar_kpis(g_pcrc_prov)
        t_pcrc_prov.insert(0, 'PROVEEDOR', g_pcrc_prov['PROVEEDOR'])
        t_pcrc_prov.insert(0, 'PCRC', g_pcrc_prov['PCRC'])
        t_pcrc_prov.insert(0, 'Periodo', g_pcrc_prov['Periodo_Str'])
    else:
        t_pcrc_prov = pd.DataFrame()
        
    return t_canal, t_pcrc, t_prov, t_pcrc_prov

tabla_canal, tabla_pcrc, tabla_prov, tabla_pcrc_prov = generar_tablas_consolidadas(df_base)

# -------------------------------------------------------------
# 4. CONTEXTO PARA GEMINI API
# -------------------------------------------------------------
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.sidebar.warning("⚠️ Falta configurar GEMINI_API_KEY")
    api_key = st.sidebar.text_input("Ingresa tu Gemini API Key:", type="password")

client = genai.Client(api_key=api_key) if api_key else None

def crear_resumen_contexto():
    c_csv = tabla_canal.to_csv(index=False)
    p_csv = tabla_pcrc.to_csv(index=False) if not tabla_pcrc.empty else "N/A"
    pr_csv = tabla_prov.to_csv(index=False) if not tabla_prov.empty else "N/A"
    pp_csv = tabla_pcrc_prov.to_csv(index=False) if not tabla_pcrc_prov.empty else "N/A"
    
    return f"""
TABLA 1 - TOTAL CANAL (Global Consolidado, 1 fila por mes):
{c_csv}

TABLA 2 - POR PCRC:
{p_csv}

TABLA 3 - POR PROVEEDOR PURO (GLOBAL POR PROVEEDOR, SIN DESGLOSE PCRC):
{pr_csv}

TABLA 4 - POR PCRC Y PROVEEDOR (DESGLOSE CRUZADO):
{pp_csv}
"""

CONTEXTO_MATEMATICO = crear_resumen_contexto()

# -------------------------------------------------------------
# 5. GENERACIÓN Y RENDERIZADO DE GRÁFICOS (PLOTLY)
# -------------------------------------------------------------
INSTRUCCIONES_GRAFICO = """
REGLA CRUCIAL PARA GRÁFICOS INTERACTIVOS:
Si el usuario te pide explícitamente ver un gráfico, evolución, tendencia, comparativa gráfica o visualizar visualmente, DEBES generar al final de tu respuesta un bloque XML exacto con el tag <chart_json> conteniendo la estructura JSON del gráfico. NO USES comillas triples adentro del tag.

Estructura JSON:
<chart_json>
{
  "tipo": "linea",
  "titulo": "Evolución de TMO por Mes",
  "x": ["2026-08", "2026-09"],
  "series": [
    {"nombre": "Total Canal", "valores": [340.5, 335.2]}
  ],
  "unidad": "seg"
}
</chart_json>

Tipos soportados:
* "linea": para evolutivos temporales a lo largo de los meses.
* "barra": para comparar PCRCs o Proveedores en un mes o período.
* "torta": para ver distribución porcentual de volumen (ej: Q Llamadas por proveedor).
"""

def dibujar_grafico(chart_data):
    if not chart_data:
        return
    try:
        tipo = str(chart_data.get("tipo", "linea")).lower()
        titulo = chart_data.get("titulo", "Gráfico de Métricas")
        eje_x = chart_data.get("x", [])
        series = chart_data.get("series", [])
        unidad = chart_data.get("unidad", "")

        if HAS_PLOTLY:
            fig = go.Figure()
            if "linea" in tipo:
                for s in series:
                    fig.add_trace(go.Scatter(
                        x=eje_x,
                        y=s.get("valores", []),
                        mode="lines+markers",
                        name=s.get("nombre", "Serie"),
                        line=dict(width=3),
                        marker=dict(size=8)
                    ))
                fig.update_layout(xaxis_title="Periodo", yaxis_title=unidad)
            elif "barra" in tipo:
                for s in series:
                    fig.add_trace(go.Bar(
                        x=eje_x,
                        y=s.get("valores", []),
                        name=s.get("nombre", "Serie")
                    ))
                fig.update_layout(barmode="group", yaxis_title=unidad)
            elif "torta" in tipo:
                labels = eje_x
                values = series[0].get("valores", []) if series else []
                fig.add_trace(go.Pie(labels=labels, values=values, hole=0.35))
            
            fig.update_layout(
                title=f"<b>{titulo}</b>",
                template="plotly_white",
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            df_chart = pd.DataFrame(index=eje_x)
            for s in series:
                df_chart[s.get("nombre", "Serie")] = s.get("valores", [])
            st.markdown(f"**📈 {titulo}**")
            if "barra" in tipo:
                st.bar_chart(df_chart)
            else:
                st.line_chart(df_chart)
    except Exception as e:
        st.warning(f"No se pudo graficar automáticamente: {e}")

# -------------------------------------------------------------
# 6. INTERFAZ DE USUARIO PRINCIPAL (EL AGENTE)
# -------------------------------------------------------------

# Encabezado con imagen del bot y título
col_avatar, col_header = st.columns([0.08, 0.92], vertical_alignment="center")
with col_avatar:
    if os.path.exists("bot_avatar.png"):
        st.image("bot_avatar.png", width=65)
    else:
        st.markdown("## 🤖")
with col_header:
    st.title("Inteligencia Operativa de Canal")
    st.caption("Agente Único Master de Inteligencia Operativa")

with st.sidebar:
    # Fila compacta: Avatar y Usuario
    col_av, col_usr = st.columns([0.28, 0.72], vertical_alignment="center")
    with col_av:
        if os.path.exists("bot_avatar.png"):
            st.image("bot_avatar.png", width=46)
        else:
            st.markdown("🤖")
    with col_usr:
        st.markdown(f"<div style='font-size: 13px; font-weight: 600; color: #1e293b; line-height: 1.2;'>👤 Usuario:<br><span style='background:#f1f5f9; padding: 2px 6px; border-radius: 4px; font-family: monospace;'>{st.session_state.get('user_display', 'Anónimo')}</span></div>", unsafe_allow_html=True)
    
    # ---------------------------------------------------------
    # BOTÓN VERDE DE USUARIOS ACTIVOS (COMPACTO)
    # ---------------------------------------------------------
    presencia = get_presencia_global()
    ahora_timestamp = time.time()
    activos_en_linea = {uid: info for uid, info in presencia.items() if ahora_timestamp - info["last_seen"] < 300}
    cant_activos = len(activos_en_linea)

    texto_activos = f"🟢 {cant_activos} {'Usuario activo' if cant_activos == 1 else 'Usuarios activos'}"
    st.markdown(f"""
    <div style="background-color: #dcfce7; border: 1.5px solid #22c55e; color: #15803d; padding: 5px 8px; border-radius: 6px; font-weight: 700; text-align: center; font-size: 12.5px; margin: 2px 0 4px 0;">
        {texto_activos}
    </div>
    """, unsafe_allow_html=True)

    # Bloque de Información del Sistema Compacto
    st.markdown("<hr style='margin: 4px 0; border: none; border-top: 1px solid #cbd5e1;'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 12px; font-weight: 700; color: #1e293b; margin-bottom: 2px;'>📊 Información del Sistema</div>", unsafe_allow_html=True)
    
    cant_pcrcs = df_base["PCRC"].nunique() if "PCRC" in df_base.columns else 0
    provs = [str(p) for p in df_base["PROVEEDOR"].dropna().unique()] if "PROVEEDOR" in df_base.columns else []
    provs_txt = ", ".join(provs)
    fecha_base_str = obtener_fecha_base(nombre_archivo_base)

    st.markdown(f"""
    <div style='font-size: 11.5px; line-height: 1.35; color: #334155;'>
        • <b>Registros:</b> <code>{len(df_base)}</code> &nbsp;|&nbsp; <b>PCRCs:</b> <code>{cant_pcrcs}</code><br>
        • <b>Proveedores:</b> {provs_txt}<br>
        • 🕒 <b>Base:</b> {fecha_base_str}<br>
        <span style='color: #64748b; font-size: 10.5px;'>⚡ <b>Powered by Mauro. R</b></span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr style='margin: 4px 0 6px 0; border: none; border-top: 1px solid #cbd5e1;'>", unsafe_allow_html=True)

    # Botones de Acción en una sola fila (2 columnas)
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("🗑️ Limpiar", use_container_width=True, help="Iniciar nueva conversación"):
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": f"¡Hola **{st.session_state.user_display}**! Comenzamos una nueva conversación. ¿Qué necesitas consultar hoy?",
                    "chart": None
                }
            ]
            guardar_historial_usuario(st.session_state.current_user, st.session_state.messages)
            st.rerun()

    with col_b2:
        if st.button("🚪 Salir", use_container_width=True, help="Cerrar sesión actual"):
            presencia = get_presencia_global()
            if st.session_state.current_user in presencia:
                del presencia[st.session_state.current_user]
            st.session_state.authenticated = False
            st.session_state.general_authenticated = False
            st.session_state.admin_authenticated = False
            st.session_state.current_user = None
            st.session_state.user_display = ""
            st.rerun()

# Renderizar historial personal del usuario
for msg in st.session_state.messages:
    avatar_actual = AVATAR_BOT if msg["role"] == "assistant" else None
    with st.chat_message(msg["role"], avatar=avatar_actual):
        st.markdown(msg["content"])
        if msg.get("chart"):
            dibujar_grafico(msg["chart"])

# Entrada de consulta
if prompt_usuario := st.chat_input("Escribe tu consulta sobre TMO, NPS, SPL o Transferencias..."):
    st.session_state.messages.append({"role": "user", "content": prompt_usuario, "chart": None})
    guardar_historial_usuario(st.session_state.current_user, st.session_state.messages)
    
    with st.chat_message("user"):
        st.markdown(prompt_usuario)

    if not client:
        with st.chat_message("assistant", avatar=AVATAR_BOT):
            st.error("No se ha configurado la API Key de Gemini. Ingrésala en el menú lateral.")
    else:
        frase_aleatoria = random.choice(FRASES_SIMPSON)
        with st.spinner(frase_aleatoria):
            historial_gemini = []
            for m in st.session_state.messages[-7:-1]:
                rol = "model" if m["role"] == "assistant" else "user"
                historial_gemini.append(f"{rol}: {m['content']}")

            prompt_completo = f"""
Eres el AGENTE MASTER DE INTELIGENCIA OPERATIVA DE CANAL.
Tu misión es brindar análisis de métricas de Contact Center exactos, profesionales y accionables.

DATOS DISPONIBLES YA CALCULADOS POR PYTHON (USA EXCLUSIVAMENTE ESTOS DATOS, NO RECALCULES NI INVENTES):
{CONTEXTO_MATEMATICO}

REGLAS FUNDAMENTALES DE NIVEL DE ANÁLISIS:
1. Si el usuario pide un análisis a "NIVEL PROVEEDOR" o "POR PROVEEDOR" de forma general (sin pedir desglose por PCRC), USA EXCLUSIVAMENTE LA TABLA 3 (PROVEEDOR PURO). NO agregues la columna PCRC ni desgloses por PCRC si no fue pedido.
2. Si pide "POR PCRC", usa la TABLA 2.
3. Si pide "POR CANAL" o "GLOBAL", usa la TABLA 1.
4. Si pide "POR PCRC Y PROVEEDOR" o un PCRC específico de un proveedor, usa la TABLA 4.

FORMATO DE RESPUESTA:
- Sé claro, profesional y estructurado con tablas Markdown cuando se comparen métricas.
- Redondea: TMO en segundos (1 decimal), NPS/SPL/Transferencias en % (2 decimales).
- Da conclusiones operativas de valor.

{INSTRUCCIONES_GRAFICO}

Historial reciente de conversación:
{chr(10).join(historial_gemini)}

Pregunta actual del usuario ({st.session_state.user_display}):
{prompt_usuario}
"""

            # Modelos oficiales vigentes con reintentos para 503
            modelos_disponibles = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3-flash-preview"]
            answer = None
            ultimo_error = None

            for mod in modelos_disponibles:
                for intento in range(3):
                    try:
                        response = client.models.generate_content(
                            model=mod,
                            contents=prompt_completo,
                        )
                        if response and response.text:
                            answer = response.text
                            break
                    except Exception as err:
                        ultimo_error = err
                        time.sleep(2.0)
                if answer:
                    break

            if answer:
                # Detectar bloque de gráfico
                chart_data = None
                match = re.search(r"<chart_json>\s*(\{.*?\})\s*</chart_json>", answer, re.DOTALL)
                if match:
                    try:
                        chart_data = json.loads(match.group(1))
                        answer_clean = re.sub(r"<chart_json>.*?</chart_json>", "", answer, flags=re.DOTALL).strip()
                    except Exception:
                        answer_clean = answer
                else:
                    answer_clean = answer

                st.markdown(answer_clean)
                if chart_data:
                    dibujar_grafico(chart_data)

                # Persistir mensaje en sesión e historial individual
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer_clean,
                    "chart": chart_data
                })
                guardar_historial_usuario(st.session_state.current_user, st.session_state.messages)
            else:
                st.error("Error al procesar la respuesta: " + str(ultimo_error))
