import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import re
import random
import time
from datetime import datetime
from google import genai

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

# Estilo CSS para que los campos de contraseña y texto se distingan claramente
st.markdown("""
<style>
div[data-baseweb="input"] {
    background-color: #f1f5f9 !important;
    border: 1.5px solid #94a3b8 !important;
    border-radius: 8px !important;
}
div[data-baseweb="input"]:hover {
    border-color: #64748b !important;
}
div[data-baseweb="input"]:focus-within {
    border-color: #2563eb !important;
    background-color: #ffffff !important;
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2) !important;
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

# Control de Acceso en Dos Pasos y Centrado en Pantalla
def check_password():
    if "general_authenticated" not in st.session_state:
        st.session_state.general_authenticated = False
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.current_user = None
        st.session_state.user_display = ""

    if st.session_state.authenticated:
        return True

    col_izq, col_centro, col_der = st.columns([1.2, 2.0, 1.2])

    with col_centro:
        if os.path.exists("bot_avatar.png"):
            ci1, ci2, ci3 = st.columns([1, 1.2, 1])
            with ci2:
                st.image("bot_avatar.png", width=120)

        # PASO 1: Contraseña General
        if not st.session_state.general_authenticated:
            st.markdown("<h2 style='text-align: center;'>🔒 Acceso al Canal</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: gray;'>Paso 1 de 2: Ingresa la contraseña general</p>", unsafe_allow_html=True)
            
            pwd = st.text_input("Contraseña General:", type="password", key="general_pwd")
            if st.button("Continuar ➡️", use_container_width=True):
                if pwd == PASSWORD_ACCESO:
                    st.session_state.general_authenticated = True
                    st.rerun()
                else:
                    st.error("Contraseña general incorrecta.")
            return False

        # PASO 2: Usuario y PIN
        else:
            st.markdown("<h2 style='text-align: center;'>👤 Tu Identificación</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: gray;'>Paso 2 de 2: Accede a tus consultas privadas</p>", unsafe_allow_html=True)
            
            usuario_input = st.text_input("Nombre de Usuario o Legajo:").strip()
            pin_input = st.text_input("PIN personal (4 dígitos):", type="password", max_chars=4).strip()
            
            col_b1, col_b2 = st.columns([2, 1])
            with col_b1:
                boton_entrar = st.button("Ingresar al Agente 🚀", use_container_width=True)
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
                        "fecha_registro": datetime.now().strftime("%d/%m/%Y %H:%M")
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
    spl7 = (1 - (df_grp['Q SPL7 Reiterados'] / q_spl)) * 100
    
    res_df = pd.DataFrame({
        'TMO': tmo_seg.round(0).fillna(0).astype(int).astype(str) + 's',
        'ACW': acw_seg.round(0).fillna(0).astype(int).astype(str) + 's',
        'T_Saliente': sal_seg.round(0).fillna(0).astype(int).astype(str) + 's',
        'Tiempo_TT': tt_seg.round(0).fillna(0).astype(int).astype(str) + 's',
        'Tiempo_Hold': hold_seg.round(0).fillna(0).astype(int).astype(str) + 's',
        'NPS': nps.round(1).astype(str) + '%',
        'Promotor': prom.round(1).astype(str) + '%',
        'Detractor': detr.round(1).astype(str) + '%',
        'Resolucion': resolucion.round(1).astype(str) + '%',
        'SPL_7': spl7.round(1).astype(str) + '%',
        'SPL_30': spl30.round(1).astype(str) + '%',
        'SPL_48': spl48.round(1).astype(str) + '%',
        'Transf_1L': transf_1l.round(1).astype(str) + '%',
        'Transf_2L': transf_2l.round(1).astype(str) + '%',
        'Transf_Totales': transf_tot.round(1).astype(str) + '%',
        'Transf_Retencion': transf_ret.round(1).astype(str) + '%',
        'Transf_Tecnica': transf_tec.round(1).astype(str) + '%',
        'Transf_COE': transf_coe.round(1).astype(str) + '%',
        'Transf_Complejas': transf_comp.round(1).astype(str) + '%'
    })
    return res_df

# 1. TABLA CANAL: Total consolidado del canal (1 fila por mes)
df_canal_vol = df_base.groupby('Periodo_Str')[COLS_NUM].sum().reset_index()
df_canal_kpis = pd.concat([df_canal_vol[['Periodo_Str']], computar_kpis(df_canal_vol)], axis=1)

# 2. TABLA PCRC: Agrupado por Periodo y PCRC
if 'PCRC' in df_base.columns:
    df_pcrc_vol = df_base.groupby(['Periodo_Str', 'PCRC'])[COLS_NUM].sum().reset_index()
    df_pcrc_kpis = pd.concat([df_pcrc_vol[['Periodo_Str', 'PCRC']], computar_kpis(df_pcrc_vol)], axis=1)
else:
    df_pcrc_kpis = pd.DataFrame()

# 3. TABLA PROVEEDOR GLOBAL (Puro): Total de cada proveedor en todo el canal (SIN columna PCRC)
if 'PROVEEDOR' in df_base.columns:
    df_prov_global_vol = df_base.groupby(['Periodo_Str', 'PROVEEDOR'])[COLS_NUM].sum().reset_index()
    df_prov_global_kpis = pd.concat([df_prov_global_vol[['Periodo_Str', 'PROVEEDOR']], computar_kpis(df_prov_global_vol)], axis=1)
else:
    df_prov_global_kpis = pd.DataFrame()

# 4. TABLA PCRC Y PROVEEDOR: Agrupado por Periodo, PCRC y PROVEEDOR
if 'PCRC' in df_base.columns and 'PROVEEDOR' in df_base.columns:
    df_pcrc_prov_vol = df_base.groupby(['Periodo_Str', 'PCRC', 'PROVEEDOR'])[COLS_NUM].sum().reset_index()
    df_pcrc_prov_kpis = pd.concat([df_pcrc_prov_vol[['Periodo_Str', 'PCRC', 'PROVEEDOR']], computar_kpis(df_pcrc_prov_vol)], axis=1)
else:
    df_pcrc_prov_kpis = pd.DataFrame()

# -------------------------------------------------------------
# 4. CONEXIÓN CON GEMINI
# -------------------------------------------------------------
api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))
if not api_key:
    st.sidebar.warning("⚠️ Falta configurar GEMINI_API_KEY")
    api_key = st.sidebar.text_input("Ingresa tu Gemini API Key:", type="password")
    if not api_key:
        st.info("Ingresa tu API Key de Google AI Studio para comenzar.")
        st.stop()

client = genai.Client(api_key=api_key)

# -------------------------------------------------------------
# 5. PROMPT DEL AGENTE
# -------------------------------------------------------------
SYSTEM_INSTRUCTION = """
PROMPT UNIFICADO: INTELIGENCIA OPERATIVA DE CANAL
1. ROL Y MISIÓN PRINCIPAL
Sos el Agente Único Master de Inteligencia Operativa, un analista senior experto en coordinación de flujos de datos, gobernanza de canales de atención y cálculo analítico de métricas operativas (NPS, TMO, Transferencias y tasas SPL). Tu misión exclusiva es responder cualquier consulta del usuario accediendo a los datos del sistema, determinar el rango temporal, extraer las métricas requeridas sin errores y unificar todo en una respuesta ejecutiva, estructurada y limpia.

2. FUENTE DE DATOS Y NIVELES DE AGREGACIÓN
Tienes acceso a 4 tablas con los cálculos matemáticos ya consolidados bajo estricta gobernanza:
TABLA 1: NIVEL CANAL (Consolidado Global de toda la operación, 1 sola fila por mes).
TABLA 2: NIVEL PCRC (Desglosado por cada PCRC).
TABLA 3: NIVEL PROVEEDOR GLOBAL (Total consolidado de cada proveedor en todo el canal, SIN desglosar por PCRC. Solo columnas Periodo, Proveedor y Métricas).
TABLA 4: NIVEL PCRC Y PROVEEDOR (Desglosado por PCRC y Proveedor a la vez).

REGLA CRUCIAL DE GRANULARIDAD:
- Cuando la consulta pida "a nivel canal", "del canal" o la operación general: USA OBLIGATORIAMENTE LA TABLA 1 (NIVEL CANAL).
- Si el usuario pide "por PCRC", "por campaña" o nombra un solo PCRC: USA LA TABLA 2 (NIVEL PCRC).
- Si el usuario pide "por proveedor", "solo proveedor", "comparativa de proveedores" o "a nivel proveedor" SIN nombrar un PCRC específico: DEBES USAR OBLIGATORIAMENTE LA TABLA 3 (NIVEL PROVEEDOR GLOBAL). En tu respuesta NO DEBE FIGURAR LA COLUMNA PCRC, solo Periodo, Proveedor y las métricas consultadas.
- Solo si el usuario pide explícitamente analizar un PCRC particular desglosado por sus proveedores (ej: "para el PCRC 1L Convergente Com segmentado por proveedor"): USA LA TABLA 4.

3. FORMATO DE SALIDA Y VISUALIZACIÓN OBLIGATORIA
Estructura rigurosamente la respuesta en tres bloques:
BLOQUE 1: Tabla Markdown principal con los datos del periodo y métricas solicitadas.
- En la columna Periodo, muestra obligatoriamente el nombre completo del mes en español (ej. Enero 2026, Febrero 2026, etc.).
- Supresión de celdas duplicadas: Cuando se desglosa por mes o proveedor, deja vacía la celda si el mes se repite en filas consecutivas.
- Formato numérico: TMO entero con 's' (ej. 485s). Porcentajes con exactamente 1 decimal (ej. 45.4%).
- Si el usuario pide resaltar mejor/peor, podés usar emojis verdes (🟢) y rojos (🔴) al lado de los valores extremos.
BLOQUE 2: Máximo 3 viñetas ultra-cortas de hallazgos clave (desvíos críticos, máximos, mínimos o variaciones temporales).
BLOQUE 3: Trazabilidad
- Filtros aplicados de periodo, PCRC o proveedores.
- Nivel de agregación aplicado (Nivel Canal, Nivel PCRC, Nivel Proveedor Global o Nivel PCRC y Proveedor).
- Base consultada: Base de datos consolidada del canal.

4. GENERACIÓN DE GRÁFICOS (A PEDIDO DEL USUARIO):
Si el usuario solicita un gráfico, curva, comparativa visual, torta o distribución (ejemplos: "graficame", "mostrame un gráfico de líneas", "haceme un gráfico de barras comparativo", "gráfico de torta", etc.):
Debes incluir al final de tu respuesta el bloque delimitado por las etiquetas <chart_json> y </chart_json> con este formato:
<chart_json>
{
  "tipo": "linea",
  "titulo": "Evolutivo de Métricas a Nivel Canal",
  "eje_x": ["Enero 2026", "Febrero 2026", "Marzo 2026"],
  "series": [
    {"nombre": "NPS", "valores": [35.2, 41.0, 39.4]},
    {"nombre": "SPL 7", "valores": [88.5, 90.1, 89.2]}
  ],
  "unidad": "%"
}
</chart_json>

Reglas para el gráfico:
- "tipo" puede ser:
  * "linea": para evolutivos temporales a lo largo de los meses.
  * "barra": para comparar proveedores, PCRCs o métricas en uno o varios periodos.
  * "torta": para distribuciones o participaciones (ej. Promotores vs Detractores). En torta, "eje_x" son las etiquetas y "series"[0]["valores"] son los valores numéricos.
- Los "valores" deben ser solo números float o int (sin '%' ni 's').
- La "unidad" puede ser "%", "s" o vacía.
- Si el usuario NO pide expresamente un gráfico o visualización, NO incluyas el bloque chart_json.

PROPUESTAS FINALES:
Al terminar, proponer 2 o 3 consultas específicas relacionadas que el usuario podría consultar a continuación.
"""

def dibujar_grafico(chart_data):
    try:
        tipo = str(chart_data.get("tipo", "linea")).lower()
        titulo = chart_data.get("titulo", "Visualización Operativa")
        eje_x = chart_data.get("eje_x", [])
        series = chart_data.get("series", [])
        unidad = chart_data.get("unidad", "")

        if HAS_PLOTLY:
            fig = go.Figure()

            # Caso 1: Torta / Dona
            if tipo in ["torta", "pie", "circular", "dona", "donut"]:
                valores_torta = series[0].get("valores", []) if series else []
                fig.add_trace(go.Pie(
                    labels=eje_x,
                    values=valores_torta,
                    hole=0.35,
                    textinfo="label+percent",
                    hovertemplate="%{label}: <b>%{value}" + (f"{unidad}" if unidad else "") + "</b><extra></extra>"
                ))
            # Caso 2: Barras
            elif tipo in ["barra", "barras", "bar"]:
                for s in series:
                    nombre = s.get("nombre", "Métrica")
                    valores = s.get("valores", [])
                    fig.add_trace(go.Bar(
                        x=eje_x,
                        y=valores,
                        name=nombre,
                        text=[f"{v}{unidad}" for v in valores],
                        textposition="auto"
                    ))
                fig.update_layout(barmode="group")
            # Caso 3: Líneas
            else:
                for s in series:
                    nombre = s.get("nombre", "Métrica")
                    valores = s.get("valores", [])
                    fig.add_trace(go.Scatter(
                        x=eje_x,
                        y=valores,
                        mode="lines+markers",
                        name=nombre,
                        line=dict(width=3),
                        marker=dict(size=8),
                        text=[f"{v}{unidad}" for v in valores]
                    ))

            fig.update_layout(
                title=dict(text=f"<b>{titulo}</b>", x=0.02, xanchor="left"),
                xaxis_title="Periodo / Segmento",
                yaxis_title=f"Valor ({unidad})" if unidad else "Valor",
                template="plotly_white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=40, r=40, t=60, b=40)
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
    if os.path.exists("bot_avatar.png"):
        st.image("bot_avatar.png", width=90)

    # Identificación del usuario activo
    st.markdown(f"👤 **Usuario:** `{st.session_state.get('user_display', 'Anónimo')}`")
    
    st.header("Información del Sistema")
    st.write("**Total de registros:**", len(df_base))
    if "PCRC" in df_base.columns:
        st.write("**PCRCs:**", df_base["PCRC"].nunique())
    if "PROVEEDOR" in df_base.columns:
        proveedores = [str(p) for p in df_base["PROVEEDOR"].dropna().unique()]
        st.write("**Proveedores:**", ", ".join(proveedores))
    
    # Fecha de actualización de la base compartida
    if nombre_archivo_base and os.path.exists(nombre_archivo_base):
        mtime = datetime.fromtimestamp(os.path.getmtime(nombre_archivo_base)).strftime('%d/%m/%Y %H:%M')
        st.caption(f"🕒 **Base actualizada:** {mtime}")
    
    st.caption("⚡ **Powered by Mauro. R**")
    st.divider()

    # Botón para limpiar su propia conversación
    if st.button("🗑️ Nueva conversación"):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": f"¡Hola **{st.session_state.user_display}**! Comenzamos una nueva conversación. ¿Qué necesitas consultar hoy?",
                "chart": None
            }
        ]
        guardar_historial_usuario(st.session_state.current_user, st.session_state.messages)
        st.rerun()

    if st.button("🚪 Cerrar Sesión"):
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

# Consultas sugeridas
ejemplos = [
    "Necesito el evolutivo a nivel canal de Enero a Septiembre del 2026 para NPS y SPL 7. Haceme un gráfico de líneas.",
    "Dame una comparativa en gráfico de barras de Mayo a Septiembre del 2026 para el PCRC 1L Convergente Com, segmentando sus proveedores en la métrica TMO.",
    "Mostrame un gráfico de torta de la distribución entre Promotores y Detractores a nivel canal en el último mes disponible."
]

st.markdown("**Búsquedas sugeridas:**")
cols = st.columns(3)
selected_example = None
for i, ej in enumerate(ejemplos):
    if cols[i].button(f"Opción {i+1}", help=ej):
        selected_example = ej

user_query = st.chat_input("Escribe tu consulta operativa...")
if selected_example:
    user_query = selected_example

if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query, "chart": None})
    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant", avatar=AVATAR_BOT):
        frase_aleatoria = random.choice(FRASES_SIMPSON)
        with st.spinner(frase_aleatoria):
            
            tablas_contexto = (
                "--- TABLA 1: NIVEL CANAL (Consolidado de toda la base, 1 fila por mes) ---\n"
                + df_canal_kpis.to_string(index=False)
                + "\n\n--- TABLA 2: NIVEL PCRC (Desglosado por Campaña / PCRC) ---\n"
                + df_pcrc_kpis.to_string(index=False)
                + "\n\n--- TABLA 3: NIVEL PROVEEDOR GLOBAL (Total consolidado de cada proveedor en el canal, SIN PCRC) ---\n"
                + df_prov_global_kpis.to_string(index=False)
                + "\n\n--- TABLA 4: NIVEL PCRC Y PROVEEDOR (Desglosado por PCRC y Proveedor) ---\n"
                + df_pcrc_prov_kpis.to_string(index=False)
            )
            prompt_completo = (
                SYSTEM_INSTRUCTION
                + "\n\nDATOS CALCULADOS DE FORMA MATEMÁTICA EXACTA:\n"
                + tablas_contexto
                + "\n\nCONSULTA EXACTA DEL USUARIO:\n"
                + user_query
            )
            
            # Lista con tus modelos y respaldo estable para evitar 503
            modelos_disponibles = [
                "gemini-3.5-flash",
                "gemini-3.8-flash",
                "gemini-3-flash-preview",
                "gemini-2.5-flash",
                "gemini-2.0-flash"
            ]
            answer = None
            ultimo_error = None

            for mod in modelos_disponibles:
                # 2 intentos con pausa breve para sortear picos de demanda
                for intento in range(2):
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
                        time.sleep(1.5)
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
