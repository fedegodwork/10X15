import streamlit as st
import fitz  # PyMuPDF
import io
import re
import base64

st.set_page_config(page_title="Generador 10x15 Universal", page_icon="🏷️", layout="centered")

st.title("🏷️ Generador de Etiquetas 10x15")
st.write("Mapeo dinámico por coordenadas para máxima consistencia entre diferentes formatos de etiqueta.")

archivo_subido = st.file_uploader("Seleccionar archivo PDF", type=["pdf"])

if archivo_subido:
    ANCHO = 100 * 2.83465  # 100 mm (283.465 pt)
    ALTO = 150 * 2.83465   # 150 mm (425.197 pt)

    bytes_pdf = archivo_subido.read()
    doc_origen = fitz.open(stream=bytes_pdf, filetype="pdf")
    doc_destino = fitz.open()

    for pagina in doc_origen:
        r_pag = pagina.rect

        # 1. EXTRAER IMÁGENES (QR Y LOGO)
        imagenes = []
        try:
            for img_info in pagina.get_images():
                xref = img_info[0]
                pix = fitz.Pixmap(doc_origen, xref)
                if pix.alpha:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                imagenes.append(pix)
        except Exception:
            pass

        qr_pix = imagenes[0] if len(imagenes) > 0 else None
        logo_pix = imagenes[1] if len(imagenes) > 1 else None

        # 2. PARSEO DE DATOS POR DICCIONARIO Y PALABRAS CLAVE
        texto_completo = pagina.get_text("text")
        lineas = [l.strip() for l in texto_completo.split("\n") if l.strip()]

        localidad = ""
        destinatario = ""
        telefono = ""
        peso_bulto = ""
        direccion = ""
        cp = ""
        observacion = ""
        fecha = ""
        remitente = ""
        venta = ""
        envio = ""

        palabras_ignorar = [
            "goxp", "logística", "logistica", "jyj", "j&j", 
            "destinatario", "remitente", "campos extra", "total a cobrar"
        ]

        # A. Mapeo de metadatos mediante patrones
        for l in lineas:
            l_lower = l.lower()
            if "cp:" in l_lower or "cp " in l_lower:
                cp_match = re.search(r'CP:?\s*(\d+)', l, re.IGNORECASE)
                cp = f"CP: {cp_match.group(1)}" if cp_match else l
            elif "rte" in l_lower:
                remitente = re.sub(r'(?i)rte\.?:?', '', l).strip()
            elif "venta" in l_lower:
                venta = re.sub(r'(?i)venta:?', '', l).strip()
            elif "envio" in l_lower or "envío" in l_lower:
                envio = re.sub(r'(?i)env[ií]o:?', '', l).strip()
            elif "observaci" in l_lower or "ref:" in l_lower:
                if not observacion or observacion.lower() == "sin información":
                    observacion = l
            elif "kg" in l_lower or "bulto" in l_lower:
                peso_bulto = l.upper()
            elif re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', l):
                if not fecha:
                    fecha = l
            elif ("+" in l or l.startswith("11") or l.startswith("15")) and len(re.sub(r'\D', '', l)) >= 8:
                if not telefono:
                    telefono = l

        # B. Extracción de Localidad y Destinatario por Coordenadas Espaciales (Words)
        words = pagina.get_text("words")  # (x0, y0, x1, y1, word, block_no, line_no, word_no)

        # Agrupar palabras de la columna central/izquierda por líneas
        lineas_coord = {}
        for w in words:
            word_txt = w[4].strip()
            # Ignorar palabras de marcas o basuras del sistema
            if any(ign in word_txt.lower() for ign in palabras_ignorar):
                continue
            if any(k in word_txt.lower() for k in ["rte:", "venta:", "envio:", "cp:", "total"]):
                continue

            y_approx = round(w[1] / 10) * 10
            lineas_coord.setdefault(y_approx, []).append(w)

        # Ordenar líneas verticalmente
        lineas_ordenadas = []
        for y_key in sorted(lineas_coord.keys()):
            palabras_linea = sorted(lineas_coord[y_key], key=lambda x: x[0])
            texto_linea = " ".join([w[4] for w in palabras_linea]).strip()
            if texto_linea:
                lineas_ordenadas.append(texto_linea)

        # La localidad es la palabra/zona en mayúsculas sin números
        for l in lineas_ordenadas:
            if not re.search(r'\d', l) and len(l) >= 3 and l.isupper():
                if not localidad:
                    localidad = l
                    break

        # Filtrar líneas para Destinatario y Dirección
        lineas_limpias = []
        for l in lineas_ordenadas:
            if l == localidad or any(k in l.lower() for k in ["sin información", "campos extra", "cobrar", "$"]):
                continue
            if re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', l) or "+" in l or l.startswith("11"):
                continue
            lineas_limpias.append(l)

        if len(lineas_limpias) > 0:
            destinatario = lineas_limpias[0].upper()
        if len(lineas_limpias) > 1:
            direccion = " ".join(lineas_limpias[1:])

        # 3. CONSTRUCCIÓN DE LA ETIQUETA 10x15
        nueva_pag = doc_destino.new_page(width=ANCHO, height=ALTO)
        m = 10
        y_cursor = m

        # ENCABEZADO
        if logo_pix:
            aspecto = logo_pix.width / logo_pix.height
            alto_logo = 32
            ancho_logo = alto_logo * aspecto
            rect_logo = fitz.Rect(m, y_cursor, m + ancho_logo, y_cursor + alto_logo)
            nueva_pag.insert_image(rect_logo, pixmap=logo_pix)

        txt_bulto = peso_bulto if peso_bulto else "BULTO 1/1"
        nueva_pag.insert_text(fitz.Point(ANCHO - m - 90, y_cursor + 20), txt_bulto, fontsize=11, fontname="hebo")

        y_cursor += 38

        # FRANJA DE LOCALIDAD
        if localidad:
            alto_franja = 28
            rect_franja = fitz.Rect(m, y_cursor, ANCHO - m, y_cursor + alto_franja)
            nueva_pag.draw_rect(rect_franja, color=(0, 0, 0), fill=(0, 0, 0))
            nueva_pag.insert_textbox(
                rect_franja, 
                localidad, 
                fontsize=13, 
                fontname="hebo", 
                color=(1, 1, 1), 
                align=1
            )
            y_cursor += alto_franja + 12

        # QR Y SEGUIMIENTO
        tam_qr = 120
        if qr_pix:
            rect_qr = fitz.Rect(m, y_cursor, m + tam_qr, y_cursor + tam_qr)
            nueva_pag.insert_image(rect_qr, pixmap=qr_pix)

        x_datos = m + tam_qr + 12
        y_datos = y_cursor + 5

        if fecha:
            nueva_pag.insert_text(fitz.Point(x_datos, y_datos), f"Fecha: {fecha}", fontsize=9, fontname="hebo")
            y_datos += 18
            nueva_pag.draw_line(fitz.Point(x_datos, y_datos - 6), fitz.Point(ANCHO - m, y_datos - 6), color=(0.8, 0.8, 0.8), width=0.5)

        if remitente:
            nueva_pag.insert_text(fitz.Point(x_datos, y_datos), f"Rte.: {remitente}", fontsize=8.5, fontname="helv")
            y_datos += 18
            nueva_pag.draw_line(fitz.Point(x_datos, y_datos - 6), fitz.Point(ANCHO - m, y_datos - 6), color=(0.8, 0.8, 0.8), width=0.5)

        if venta:
            nueva_pag.insert_text(fitz.Point(x_datos, y_datos), f"Venta: {venta}", fontsize=8.5, fontname="hebo")
            y_datos += 18
            nueva_pag.draw_line(fitz.Point(x_datos, y_datos - 6), fitz.Point(ANCHO - m, y_datos - 6), color=(0.8, 0.8, 0.8), width=0.5)

        if envio:
            nueva_pag.insert_text(fitz.Point(x_datos, y_datos), f"Envio: {envio}", fontsize=8.5, fontname="hebo")

        y_cursor += tam_qr + 10
        nueva_pag.draw_line(fitz.Point(m, y_cursor), fitz.Point(ANCHO - m, y_cursor), color=(0, 0, 0), width=1)

        # DESTINATARIO Y DIRECCIÓN
        y_cursor += 12
        nueva_pag.insert_text(fitz.Point(m, y_cursor), "Destinatario", fontsize=8, fontname="helv")
        y_cursor += 16

        if destinatario:
            nueva_pag.insert_text(fitz.Point(m, y_cursor), destinatario, fontsize=12, fontname="hebo")
            y_cursor += 15

        if telefono:
            nueva_pag.insert_text(fitz.Point(m, y_cursor), telefono, fontsize=9.5, fontname="helv")
            y_cursor += 16

        if direccion:
            texto_dir = f"{direccion} {cp}".strip()
            rect_dir = fitz.Rect(m, y_cursor, ANCHO - m, y_cursor + 32)
            nueva_pag.insert_textbox(rect_dir, texto_dir, fontsize=10, fontname="hebo")
            y_cursor += 34

        if observacion:
            rect_obs = fitz.Rect(m, y_cursor, ANCHO - m, ALTO - m)
            nueva_pag.insert_textbox(rect_obs, observacion, fontsize=8.5, fontname="helv")

    output_buffer = io.BytesIO()
    doc_destino.save(output_buffer)
    pdf_bytes = output_buffer.getvalue()
    doc_destino.close()
    doc_origen.close()

    st.success("¡Etiqueta lista!")

    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    nombre_archivo = f"10x15_{archivo_subido.name}"

    html_botones = f"""
    <div style="display: flex; gap: 15px; width: 100%; margin-top: 5px;">
        <a href="data:application/pdf;base64,{base64_pdf}" download="{nombre_archivo}" style="
            flex: 1;
            background-color: #ff4b4b;
            color: white;
            padding: 12px;
            font-size: 15px;
            border-radius: 8px;
            text-align: center;
            text-decoration: none;
            font-weight: bold;
            box-sizing: border-box;
            display: inline-block;
            font-family: sans-serif;
        ">📥 Descargar PDF 10x15</a>

        <button onclick="imprimirPDF()" style="
            flex: 1;
            background-color: #28a745;
            color: white;
            padding: 12px;
            font-size: 15px;
            border: none;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
            box-sizing: border-box;
            font-family: sans-serif;
        ">🖨️️ Imprimir en Térmica</button>
    </div>

    <script>
    function imprimirPDF() {{
        var pdfData = "data:application/pdf;base64,{base64_pdf}";
        var iframe = document.createElement('iframe');
        iframe.style.display = "none";
        iframe.src = pdfData;
        document.body.appendChild(iframe);
        iframe.contentWindow.focus();
        iframe.contentWindow.print();
    }}
    </script>
    """
    st.components.v1.html(html_botones, height=65)
