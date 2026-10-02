import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import re
from datetime import datetime
from google import genai
# Librería para gráficos interactivos ejecutivos
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
# Avatar del bot: usa la imagen si existe, sino el emoji
AVATAR_BOT = "bot_avatar.png" if os.path.exists("bot_avatar.png") else "🤖"
PASSWORD_ACCESO = st.secrets.get("APP_PASSWORD", "atencion2026")
PASSWORD_ADMIN = st.secrets.get("ADMIN_PASSWORD", "pirania9")
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.title("🔒 Acceso Seguro - Inteligencia Operativa")
        st.write("Por favor, ingresa la contraseña para acceder al agente.")
        pwd = st.text_input("Contraseña:", type="password")
        if st.button("Ingresar"):
            if pwd == PASSWORD_ACCESO:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
        return False
    return True
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
    # Detectar si el encabezado real está en las primeras filas
    cols_actuales = [str(c).upper().strip() for c in df.columns]
    if not any("PERIODO" in c for c in cols_actuales):
        for i in range(min(15, len(df))):
            fila_valores = [str(v).upper().strip() for v in df.iloc[i].values]
            if any("PERIODO" in v for v in fila_valores) or any("PCRC" in v or "PRCR" in v for v in fila_valores):
                df.columns = [str(v).strip() for v in df.iloc[i].values]
                df = df.iloc[i + 1:].reset_index(drop=True)
                break
    # Estandarizar nombres de columnas clave
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
# Sección de Administrador: guarda en disco para impacto global
with st.sidebar.expander("🔒 Actualizar Base (Solo Administrador)"):
    clave_admin = st.text_input("Contraseña de administrador:", type="password", key="admin_key")
    if clave_admin == PASSWORD_ADMIN:
        st.success("Acceso de Administrador concedido.")
        archivo_subido = st.file_uploader("Subir nuevo Excel o CSV", type=["xlsx", "xls", "csv"])
        if archivo_subido is not None:
            df_nuevo = leer_archivo_robusto(archivo_subido)
            if df_nuevo is not None and "Periodo" in df_nuevo.columns:
                nombre_destino = "base_datos.xlsx" if archivo_subido.name.endswith(('.xlsx', '.xls')) else "base_datos.csv"
                with open(nombre_destino, "wb") as f:
                    f.write(archivo_subido.getbuffer())
                
                # Limpiamos la caché global
                st.cache_data.clear()
                st.success("✅ Base guardada en disco. Todos los usuarios ahora verán los datos actualizados.")
                st.rerun()
            else:
                st.error("No se pudo detectar la columna Periodo en el archivo subido.")
    elif clave_admin:
        st.error("Contraseña de administrador incorrecta.")
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
# 1. TABLA CANAL
df_canal_vol = df_base.groupby('Periodo_Str')[COLS_NUM].sum().reset_index()
df_canal_kpis = pd.concat([df_canal_vol[['Periodo_Str']], computar_kpis(df_canal_vol)], axis=1)
# 2. TABLA PCRC
if 'PCRC' in df_base.columns:
    df_pcrc_vol = df_base.groupby(['Periodo_Str', 'PCRC'])[COLS_NUM].sum().reset_index()
    df_pcrc_kpis = pd.concat([df_pcrc_vol[['Periodo_Str', 'PCRC']], computar_kpis(df_pcrc_vol)], axis=1)
else:
    df_pcrc_kpis = pd.DataFrame()
# 3. TABLA PROVEEDOR
if 'PCRC' in df_base.columns and 'PROVEEDOR' in df_base.columns:
    df_prov_vol = df_base.groupby(['Periodo_Str', 'PCRC', 'PROVEEDOR'])[COLS_NUM].sum().reset_index()
    df_prov_kpis = pd.concat([df_prov_vol[['Periodo_Str', 'PCRC', 'PROVEEDOR']], computar_kpis(df_prov_vol)], axis=1)
else:
    df_prov_kpis = pd.DataFrame()
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
# 5. PROMPT DEL AGENTE (CON SOPORTE DE GRÁFICOS)
# -------------------------------------------------------------
SYSTEM_INSTRUCTION = """
PROMPT UNIFICADO: INTELIGENCIA OPERATIVA DE CANAL
1. ROL Y MISIÓN PRINCIPAL
Sos el Agente Único Master de Inteligencia Operativa, un analista senior experto en coordinación de flujos de datos, gobernanza de canales de atención y cálculo analítico de métricas operativas (NPS, TMO, Transferencias y tasas SPL). Tu misión exclusiva es responder cualquier consulta del usuario accediendo a los datos del sistema, determinar el rango temporal, extraer las métricas requeridas sin errores y unificar todo en una respuesta ejecutiva, estructurada y limpia.
2. FUENTE DE DATOS Y NIVELES DE AGREGACIÓN
Tienes acceso a 3 tablas con los cálculos matemáticos ya consolidados bajo estricta gobernanza:
TABLA 1: NIVEL CANAL (Consolidado Global de toda la operación, sin filtros de PCRC ni Proveedor, 1 sola fila por mes).
TABLA 2: NIVEL PCRC (Desglosado por cada PCRC).
TABLA 3: NIVEL PROVEEDOR (Desglosado por PCRC y Proveedor).
REGLA CRUCIAL DE GRANULARIDAD:
- Cuando la consulta del usuario pida "a nivel canal", "del canal" o la operación general: DEBES USAR OBLIGATORIAMENTE LA TABLA 1 (NIVEL CANAL). En la tabla de respuesta debe haber UNA SOLA FILA POR MES. No incluyas PCRC ni Proveedor.
- Solo si el usuario pide explícitamente "por PCRC", "por campaña" o nombra un PCRC, usa la TABLA 2.
- Solo si el usuario pide "por proveedor" o "segmentado proveedores", usa la TABLA 3.
3. FORMATO DE SALIDA Y VISUALIZACIÓN OBLIGATORIA
Estructura rigurosamente la respuesta en tres bloques:
BLOQUE 1: Tabla Markdown principal con los datos del periodo y métricas solicitadas.
- En la columna Periodo, muestra obligatoriamente el nombre completo del mes en español (ej. Enero 2026, Febrero 2026, etc.).
- Supresión de celdas duplicadas: Cuando se desglosa por PCRC o Proveedor, deja vacía la celda si el mes o PCRC se repite en filas consecutivas.
- Formato numérico: TMO entero con 's' (ej. 485s). Porcentajes con exactamente 1 decimal (ej. 45.4%).
BLOQUE 2: Máximo 3 viñetas ultra-cortas de hallazgos clave (desvíos críticos, máximos, mínimos o variaciones temporales).
BLOQUE 3: Trazabilidad
- Filtros aplicados de periodo, PCRC o proveedores.
- Nivel de agregación aplicado (Nivel Canal, Nivel PCRC o Nivel Proveedor).
- Base consultada: Base de datos consolidada del canal.
4. GENERACIÓN DE GRÁFICOS INTERACTIVOS (A PEDIDO DEL USUARIO):
Si el usuario solicita un gráfico, curva, comparativa visual, torta o distribución (ejemplos: "graficame", "mostrame un gráfico de líneas", "haceme un gráfico de barras comparativo", "gráfico de torta", etc.):
Debes incluir obligatoriamente al final de tu respuesta un bloque JSON con este formato EXACTO:
```chart_json
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
