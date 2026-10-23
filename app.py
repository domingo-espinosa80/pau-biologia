import os
import html
import sqlite3
import base64
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# Configuración de página
st.set_page_config(
    page_title="PAU Biología - Banco de Ejercicios",
    page_icon="🔬",
    layout="wide"
)

# Rutas locales dentro de Streamlit
DB_NAME = "pau_biologia.db"
CARPETA_IMAGENES = "imagenes_ejercicios"

@st.cache_data
def cargar_datos():
    if not os.path.exists(DB_NAME):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM ejercicios ORDER BY anio DESC, comunidad ASC, numero_ejercicio ASC", conn)
    conn.close()
    return df

def obtener_base64_imagen(ruta_img):
    if not ruta_img or str(ruta_img).strip() == "" or str(ruta_img).lower() == "none":
        return None

    ruta_final = str(ruta_img).strip()
    if not os.path.exists(ruta_final):
        nombre_archivo = os.path.basename(ruta_final)
        ruta_final = os.path.join(CARPETA_IMAGENES, nombre_archivo)

    if os.path.exists(ruta_final):
        try:
            ext = os.path.splitext(ruta_final)[1].lower().replace('.', '')
            mime = "jpeg" if ext in ["jpg", "jpeg"] else ("png" if ext == "png" else "png")
            with open(ruta_final, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                return f"data:image/{mime};base64,{encoded_string}"
        except Exception:
            return None
    return None

# Título Principal
st.title("🔬 Banco de Ejercicios PAU Biología")

df_master = cargar_datos()

if df_master.empty:
    st.error("⚠️ No se encontró la base de datos `pau_biologia.db`. Asegúrate de haber subido el archivo al repositorio.")
    st.stop()

# ===========================================================================
# FILTROS DE BÚSQUEDA
# ===========================================================================
with st.expander("🎛️ Filtros de Búsqueda y Paginación", expanded=True):
    col1, col2, col3, col4 = st.columns(4)
    
    comunidades = ["Todas"] + sorted([str(c) for c in df_master['comunidad'].dropna().unique() if str(c).strip()])
    
    anios_raw = []
    for a in df_master['anio'].dropna().unique():
        try:
            val_str = str(a).split('.')[0].strip()
            if val_str and val_str.isdigit():
                anios_raw.append(int(val_str))
        except Exception:
            pass
    anios = ["Todos"] + [str(a) for a in sorted(list(set(anios_raw)), reverse=True)]

    col_bloque = 'bloque_saberes' if 'bloque_saberes' in df_master.columns else ('bloque' if 'bloque' in df_master.columns else None)
    if col_bloque:
        bloques = ["Todos"] + sorted([str(b) for b in df_master[col_bloque].dropna().unique() if str(b).strip()])
    else:
        bloques = ["Todos"]

    with col1:
        sel_comunidad = st.selectbox("Comunidad Autónoma", comunidades)
    with col2:
        sel_anio = st.selectbox("Año", anios)
    with col3:
        sel_bloque = st.selectbox("Bloque", bloques)
    with col4:
        input_texto = st.text_input("Buscar palabra clave", placeholder="Ej: mitocondria, ADN...")

    col_p1, col_p2 = st.columns([2, 2])
    with col_p1:
        por_pagina = st.selectbox("Ejercicios por vista", ["10", "20", "50", "Todos"], index=1)

# Aplicar filtros al DataFrame
df_filtrado = df_master.copy()

if sel_comunidad != "Todas":
    df_filtrado = df_filtrado[df_filtrado['comunidad'].astype(str) == str(sel_comunidad)]

if sel_anio != "Todos":
    df_filtrado['anio_clean'] = df_filtrado['anio'].astype(str).str.split('.').str[0].str.strip()
    df_filtrado = df_filtrado[df_filtrado['anio_clean'] == str(sel_anio).strip()]

if sel_bloque != "Todos" and col_bloque:
    df_filtrado = df_filtrado[df_filtrado[col_bloque].astype(str) == str(sel_bloque)]

if input_texto.strip():
    df_filtrado = df_filtrado[df_filtrado['texto_literal'].astype(str).str.contains(input_texto.strip(), case=False, na=False)]

total_resultados = len(df_filtrado)

# Paginación
if por_pagina != "Todos":
    limite = int(por_pagina)
    total_paginas = max(1, (total_resultados + limite - 1) // limite)
    
    col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
    with col_nav2:
        pagina_actual = st.number_input(f"Página (1 de {total_paginas})", min_value=1, max_value=total_paginas, value=1)
    
    inicio = (pagina_actual - 1) * limite
    fin = inicio + limite
    df_corte = df_filtrado.iloc[inicio:fin]
    st.info(f"Mostrando **{len(df_corte)}** de **{total_resultados}** ejercicios filtrados")
else:
    pagina_actual = 1
    total_paginas = 1
    inicio = 0
    df_corte = df_filtrado
    st.info(f"Mostrando los **{total_resultados}** ejercicios filtrados")

if total_resultados == 0:
    st.warning("🔍 No se encontraron ejercicios con los filtros seleccionados.")
    st.stop()

# ===========================================================================
# GENERACIÓN DEL HTML DE RESULTADOS E IMPRESIÓN
# ===========================================================================
html_items = []

for idx_pos, (_, row) in enumerate(df_corte.iterrows(), start=1):
    idx_global = inicio + idx_pos
    ej_id = str(row.get('id', idx_global))
    comunidad_txt = html.escape(str(row.get('comunidad', 'Desconocida')))
    anio_txt = str(row.get('anio', '----')).split('.')[0]
    convocatoria_txt = html.escape(str(row.get('convocatoria', 'Desconocida')))
    ej_num_orig = html.escape(str(row.get('numero_ejercicio', '1')))
    opcion_txt = html.escape(str(row.get('opcion', 'Única')))

    bloque_val = row.get('bloque_saberes') if 'bloque_saberes' in row else row.get('bloque', 'Otros')
    bloque_txt = html.escape(str(bloque_val if pd.notnull(bloque_val) else 'Otros'))
    subtema_txt = html.escape(str(row.get('subtema', 'General') if pd.notnull(row.get('subtema')) else 'General'))
    texto_enunciado = html.escape(str(row.get('texto_literal', ''))).replace('\n', '<br>')

    tiene_img = row.get('tiene_imagen') in [1, '1', True, 'True']
    ruta_img = row.get('ruta_imagen')

    img_html = ""
    badge_html = ""

    if tiene_img or (ruta_img and str(ruta_img).lower() != 'none'):
        b64_img = obtener_base64_imagen(ruta_img)
        if b64_img:
            badge_html = '<span style="background:#dbeafe; color:#1e40af; padding:2px 8px; border-radius:12px; font-size:0.8em; font-weight:600;">📷 Con imagen</span>'
            img_html = f"""
            <div style="margin-top: 15px; text-align: center; background: #ffffff; padding: 10px; border: 1px solid #e2e8f0; border-radius: 6px;">
                <img src="{b64_img}" style="max-width: 100%; max-height: 450px; border-radius: 4px;" alt="Esquema" />
            </div>
            """
        else:
            badge_html = '<span style="background:#f1f5f9; color:#64748b; padding:2px 8px; border-radius:12px; font-size:0.8em;">⚠️ Imagen no hallada</span>'
    else:
        badge_html = '<span style="background:#f1f5f9; color:#64748b; padding:2px 8px; border-radius:12px; font-size:0.8em;">📄 Solo texto</span>'

    item_html = f"""
    <div class="ej-item" style="background:#ffffff; color:#111827; border:1px solid #cbd5e1; border-radius:8px; padding:20px; margin-bottom:20px; box-shadow:0 2px 4px rgba(0,0,0,0.06); font-family:system-ui, -apple-system, sans-serif;">
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px; flex-wrap:wrap;">
            <input type="checkbox" class="ej-check" id="check_{ej_id}" onchange="actualizarContadorPAU()" style="width:18px; height:18px; cursor:pointer;" />
            <span style="background:#1e40af; color:#ffffff; font-weight:bold; padding:2px 8px; border-radius:4px; font-size:0.9em;">Pregunta {idx_global} de {total_resultados}</span>
            <label for="check_{ej_id}" style="color:#0d47a1; font-size:1.1em; font-weight:bold; cursor:pointer;">
                📌 [{comunidad_txt}] — Año {anio_txt} ({convocatoria_txt}) | Ej. {ej_num_orig} (Opción {opcion_txt})
            </label>
            {badge_html}
        </div>
        <div style="color:#4b5563; font-size:0.88em; margin-bottom:12px;">
            <b>Bloque:</b> {bloque_txt} | <b>Subtema:</b> {subtema_txt}
        </div>
        <div style="font-size:1em; line-height:1.6; color:#1f2937; background:#f8fafc; padding:12px; border-radius:6px; border-left:4px solid #2563eb;">
            {texto_enunciado}
        </div>
        {img_html}
    </div>
    """
    html_items.append(item_html)

todo_el_contenido = "".join(html_items)

# Componente JS e HTML de renderizado + Impresión limpia
full_component = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background-color: #f8fafc;
            font-family: system-ui, -apple-system, sans-serif;
        }}
        .floating-bar {{
            position: fixed;
            bottom: 15px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 99999;
            background: #ffffff;
            padding: 8px 20px;
            border-radius: 50px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            border: 1px solid #cbd5e1;
            display: flex;
            align-items: center;
            gap: 12px;
            white-space: nowrap;
        }}
        .floating-bar button {{
            background-color: #f1f5f9;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.88em;
            font-weight: 600;
            cursor: pointer;
        }}
        .floating-bar .btn-print {{
            background-color: #2563eb !important;
            color: #ffffff !important;
            border: none !important;
        }}
    </style>
    <script>
        function marcarTodosPAU() {{
            document.querySelectorAll('.ej-check').forEach(cb => {{ cb.checked = true; }});
            actualizarContadorPAU();
        }}
        function desmarcarTodosPAU() {{
            document.querySelectorAll('.ej-check').forEach(cb => {{ cb.checked = false; }});
            actualizarContadorPAU();
        }}
        function actualizarContadorPAU() {{
            const count = document.querySelectorAll('.ej-check:checked').length;
            document.getElementById('cnt-lbl').innerText = count;
        }}
        function imprimirLimpioPAU() {{
            const checkboxes = document.querySelectorAll('.ej-check:checked');
            if (checkboxes.length === 0) {{
                alert('⚠️ Por favor, selecciona al menos un ejercicio marcando su casilla.');
                return;
            }}

            let printFrame = document.getElementById('pau-print-frame');
            if (printFrame) printFrame.remove();

            printFrame = document.createElement('iframe');
            printFrame.id = 'pau-print-frame';
            printFrame.style.position = 'fixed';
            printFrame.style.right = '0';
            printFrame.style.bottom = '0';
            printFrame.style.width = '0';
            printFrame.style.height = '0';
            printFrame.style.border = '0';
            document.body.appendChild(printFrame);

            const frameDoc = printFrame.contentWindow.document;
            frameDoc.open();

            let htmlContent = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>Ejercicios Seleccionados - PAU Biología</title>
                <style>
                    @page {{ margin: 15mm; size: A4; }}
                    body {{ font-family: system-ui, sans-serif; color: #111827; margin: 0; padding: 0; }}
                    .ej-item-print {{ border: 1px solid #cbd5e1; border-radius: 8px; padding: 18px; margin-bottom: 25px; page-break-inside: avoid; }}
                    .print-badge {{ background-color: #0f172a; color: #ffffff; font-weight: bold; padding: 3px 10px; border-radius: 4px; font-size: 0.9em; }}
                    .ej-title {{ color: #0d47a1; font-size: 1.05em; font-weight: bold; }}
                    .ej-text {{ font-size: 0.98em; line-height: 1.5; color: #1f2937; background-color: #f8fafc; padding: 12px; border-radius: 6px; border-left: 4px solid #2563eb; margin-top: 8px; }}
                    img {{ max-width: 100%; max-height: 450px; display: block; margin: 12px auto; }}
                </style>
            </head>
            <body>`;

            checkboxes.forEach((cb, idx) => {{
                const origItem = cb.closest('.ej-item');
                if (origItem) {{
                    const titleText = origItem.querySelector('label') ? origItem.querySelector('label').innerText : '';
                    const textContent = origItem.querySelector('div[style*="background:#f8fafc"]') ? origItem.querySelector('div[style*="background:#f8fafc"]').innerHTML : '';
                    const imgContainer = origItem.querySelector('img');
                    const imgHtml = imgContainer ? `<div style="text-align:center;"><img src="${{imgContainer.src}}" /></div>` : '';

                    htmlContent += `
                    <div class="ej-item-print">
                        <div style="display:flex; align-items:center; gap:10px;">
                            <span class="print-badge">Ejercicio ${{idx + 1}} de ${{checkboxes.length}}</span>
                            <span class="ej-title">${{titleText}}</span>
                        </div>
                        <div class="ej-text">${{textContent}}</div>
                        ${{imgHtml}}
                    </div>`;
                }}
            }});

            htmlContent += `</body></html>`;
            frameDoc.write(htmlContent);
            frameDoc.close();

            setTimeout(() => {{
                printFrame.contentWindow.focus();
                printFrame.contentWindow.print();
            }}, 400);
        }}
    </script>
</head>
<body>
    <div style="padding-bottom: 80px;">
        {todo_el_contenido}
    </div>
    <div class="floating-bar">
        <button type="button" onclick="marcarTodosPAU()">☑️ Todos</button>
        <button type="button" onclick="desmarcarTodosPAU()">☐ Ninguno</button>
        <span style="font-weight:bold; font-size:0.9em;">Seleccionados: <span id="cnt-lbl" style="color:#2563eb;">0</span></span>
        <button type="button" class="btn-print" onclick="imprimirLimpioPAU()">📄 Imprimir Seleccionados</button>
    </div>
</body>
</html>
"""

components.html(full_component, height=800, scrolling=True)

# ===========================================================================
# ANALÍTICA CON UMAMI (Estadísticas de visitas por región/ciudad)
# ===========================================================================
UMAMI_ID = "f9fb4674-7907-4c00-aaff-02ee12cb21b6"

umami_code = f"""
<script async src="https://cloud.umami.is/script.js" data-website-id="{UMAMI_ID}"></script>
"""
components.html(umami_code, height=0, width=0)
