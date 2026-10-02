import streamlit as st
import pandas as pd
import os
from google import genai
from google.genai import types

# -------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA Y SEGURIDAD
# -------------------------------------------------------------
st.set_page_config(
    page_title="Inteligencia Operativa de Canal",
    page_icon="📊",
    layout="wide"
)

# Contraseña de acceso (se define en secrets o por defecto)
PASSWORD_ACCESO = st.secrets.get("APP_PASSWORD", "canal2026")

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
                st.error("Contraseña incorrecta. Inténtalo de nuevo.")
        return False
    return True

if not check_password():
    st.stop()

# -------------------------------------------------------------
# CARGA DE DATOS
# -------------------------------------------------------------
@st.cache_data
def cargar_datos():
    df = pd.read_csv("base_datos.csv")
    df.columns = [c.strip() for c in df.columns]
    
    if "PRCR" in df.columns and "PCRC" not in df.columns:
        df.rename(columns={"PRCR": "PCRC"}, inplace=True)
        
    columnas_numericas = [
        'Tiempo ACW in', 'Tiempo Saliente', 'Tiempo TT', 'Tiempo Hold', 'Q TMO',
        'REP 1L', 'REP 2L', 'RetencionTransf', 'TecnicaTransfResto', 'TecnicaTransfPrio',
        'ComplejasTransf', 'Q llamadas', 'Promotores', 'detractor', 'Q meda',
        'Res si', 'Q Res', 'Q SPL30 Reiterados', 'Q SPL48 Reiterados',
        'Q SPL7 Reiterados', 'Q SPL Atendidos'
    ]
    for col in columnas_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    df['Periodo'] = pd.to_datetime(df['Periodo'])
    return df

df_base = cargar_datos()

# -------------------------------------------------------------
# CONEXIÓN CON GEMINI
# -------------------------------------------------------------
api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

if not api_key:
    st.sidebar.warning("⚠️ Falta configurar GEMINI_API_KEY en Secrets")
    api_key = st.sidebar.text_input("Ingresa tu Gemini API Key:", type="password")
    if not api_key:
        st.info("Ingresa tu API Key de Google AI Studio para comenzar.")
        st.stop()

client = genai.Client(api_key=api_key)

# -------------------------------------------------------------
# PROMPT MAESTRO
# -------------------------------------------------------------
SYSTEM_INSTRUCTION = """
Sos el Agente Único Master de Inteligencia Operativa, un analista senior experto en coordinación de flujos de datos, gobernanza de canales de atención y cálculo analítico de métricas operativas (NPS, TMO, Transferencias y tasas SPL).
Tu misión es procesar de punta a punta cualquier consulta del usuario accediendo directamente a la base de datos cargada ('Base de datos por Q').

REGLA DE ORO DE GOBERNANZA:
Si vas a calcular tasas o promedios agrupados en más de una fila/periodo, suma siempre los volúmenes absolutos base antes de recalcular. NUNCA promedies porcentajes ya calculados.

FÓRMULAS MATEMÁTICAS OBLIGATORIAS:
A. MÓDULO TMO:
ACW = [Tiempo ACW in] / [Q TMO]
T_Saliente = [Tiempo Saliente] / [Q TMO]
Tiempo_TT = [Tiempo TT] / [Q TMO]
Tiempo_Hold = [Tiempo Hold] / [Q TMO]
TMO = ACW + T_Saliente + Tiempo_TT + Tiempo_Hold
(Gobernanza TMO): Los valores finales de TMO y sus componentes deben mostrarse siempre como números enteros seguidos de 's' sin decimales (ej. 345s).

B. MÓDULO TRANSFERENCIAS:
Transferencias a 1 Línea = [REP 1L] / [Q llamadas]
Transferencias a 2 Línea = [REP 2L] / [Q llamadas]
Transferencias Totales = ([REP 1L] + [REP 2L]) / [Q llamadas]
Transferencias a Retención = [RetencionTransf] / [Q llamadas]
Transferencias a Técnica = [TecnicaTransfResto] / [Q llamadas]
Transferencias a COE = [TecnicaTransfPrio] / [Q llamadas]
Transferencias a Complejas = [ComplejasTransf] / [Q llamadas]
(Mostrar como porcentaje con exactamente 1 decimal, ej. 12.4%)

C. MÓDULO NPS:
% NPS = ([Promotores] - [detractor]) / [Q meda]
% Promotor = [Promotores] / [Q meda]
% Detractor = [detractor] / [Q meda]
(Mostrar con 1 decimal, ej. 45.2%)

D. MÓDULO RESOLUCIÓN:
% Resolución = [Res si] / [Q Res]
(Mostrar con 1 decimal, ej. 78.5%)

E. MÓDULO SPLS (REITERACIÓN DE CONTACTO):
SPL 30 Minutos (Efectividad) = 1 - ([Q SPL30 Reiterados] / [Q SPL Atendidos])
SPL 48 Horas (Efectividad) = 1 - ([Q SPL48 Reiterados] / [Q SPL Atendidos])
SPL 7 Días (Efectividad) = 1 - ([Q SPL7 Reiterados] / [Q SPL Atendidos])
(Gobernanza SPL): Si [Q SPL Atendidos] = 0, retornar obligatoriamente 'N/A (0 atendidos)'. Mostrar con 1 decimal.

REGLAS ESTRICTAS:
- Closed-World Assumption: La única fuente de verdad es la base de datos cargada.
- Cero Alucinación por Ausencia: Si el dato no se encuentra, responder textualmente: 'No dispongo de esa información específica en los archivos cargados.'

FORMATO DE SALIDA Y VISUALIZACIÓN OBLIGATORIA:
BLOQUE 1: Tabla Markdown principal con los datos consolidados y métricas calculadas.
- En la columna Periodo, muestra el nombre completo del mes en español (ej. Mayo 2026).
- Supresión de Celdas Duplicadas: Si un mismo Periodo o PCRC se repite en filas consecutivas, deja la celda vacía para una visualización limpia tipo reporte ejecutivo.
- Valores de TMO enteros sin decimales con 's'. Porcentajes con exactamente 1 decimal.

BLOQUE 2: Máximo 3 viñetas ultra-cortas de hallazgos clave (desvíos críticos, máximos, mínimos o variaciones temporales).

BLOQUE 3: Trazabilidad (filtros aplicados de periodo, PCRC o proveedores, y base consultada).

PROPUESTAS FINALES:
Al terminar, proponer 2 o 3 consultas específicas relacionadas que el usuario podría consultar a continuación.
"""

# -------------------------------------------------------------
# INTERFAZ DE USUARIO
# -------------------------------------------------------------
st.title("📊 Inteligencia Operativa de Canal")
st.caption("Agente de Consulta y Análisis de Métricas Operativas (NPS, TMO, SPL, Transferencias)")

with st.sidebar:
    st.header("Información del Sistema")
    st.write(f"**Registros:** {len(df_base)}")
    st.write(f"**PCRCs:** {df_base['PCRC'].nunique()}")
    st.write(f"**Proveedores:** {', '.join(df_base['PROVEEDOR'].unique())}")
    st.write(f"**Periodos:** {df_base['Periodo'].min().strftime('%Y-%m')} a {df_base['Periodo'].max().strftime('%Y-%m')}")
    st.divider()
    if st.button("Cerrar Sesión"):
        st.session_state.authenticated = False
        st.rerun()

# Historial de Chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "¡Hola! Soy el **Agente Único Master de Inteligencia Operativa**. Tengo acceso completo a la *Base de datos por Q*.\n\nPuedes consultarme evolutivos a nivel canal, comparativas entre proveedores, cálculos de TMO, NPS, Transferencias o tasas SPL."
        }
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Sugerencias rápidas
ejemplos = [
    "Necesito el evolutivo a nivel canal, de Enero a Septiembre del 2026, para NPS, SPL 7 y Transferencias Totales.",
    "Comparativa de Mayo a Septiembre del 2026 para 1L Convergente Com por proveedor en TMO, SPL 30, SPL 48 y Transferencias a 2 Lineas.",
    "Evolutivo de TMO, Resolucion y Transferencias a COE para 1L Conv Priority por proveedor (Enero a Septiembre 2026). Decime quien es Bench."
]

st.markdown("**Consultas de ejemplo:**")
cols = st.columns(3)
selected_example = None
for i, ej in enumerate(ejemplos):
    if cols[i].button(f"Ejemplo {i+1}", help=ej):
        selected_example = ej

user_query = st.chat_input("Escribe tu consulta aquí...")
if selected_example:
    user_query = selected_example

if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):
        with st.spinner("Consultando base de datos y calculando métricas..."):
            data_csv = df_base.to_csv(index=False)
            prompt_completo = f"""
{SYSTEM_INSTRUCTION}

BASE DE DATOS COMPLETA CARGADA (Base de datos por Q):
```csv
{data_csv}
```

CONSULTA DEL USUARIO:
"{user_query}"
"""
             # Fallback automatico ante alta demanda
            modelos_disponibles = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-3.8-flash"]
            answer = None
            ultimo_error = None
            for mod in modelos_disponibles:
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
                    continue
            if answer:
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            else:
                st.error(f"Error al procesar la respuesta: {ultimo_error}")
