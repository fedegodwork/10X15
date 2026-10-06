import streamlit as st
import fitz  # PyMuPDF
import io
import re
import base64

st.set_page_config(page_title="Generador 10x15 Universal", page_icon="🏷️", layout="centered")

st.title("🏷️️ Generador de Etiquetas 10x15")
st.write("Mapeo geométrico estricto por coordenadas X/Y para consistencia total en cualquier etiqueta.")

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

        # 2. CAPTURA Y PARSEO DE METADATOS CLAVE
        texto_completo = pagina.get_text("text")
        lineas = [l.strip() for l in texto_completo.split("\n") if l.strip()]

        fecha = ""
        remitente = ""
        venta = ""
        envio = ""
        peso_bulto = ""
        observacion = ""
        cp = ""
        telefono = ""

        for l in lineas:
            l_lower = l.lower()
            if "cp:" in l_lower or "cp " in l_lower:
                m = re.search(r'CP:?\s*(\d+)', l, re.IGNORECASE)
                cp = f"CP: {m.group(1)}" if m else l
            elif "rte" in l_lower:
                remitente = re.sub(r'(?i)rte\.?:?', '', l).strip()
            elif "venta" in l_lower:
                venta = re.sub(r'(?i)venta:?', '', l).strip()
            elif "envio" in l_lower or "envío" in l_lower:
                envio = re.sub(r'(?i)env[ií]o:?', '', l).strip()
            elif "observaci" in l_lower or "ref:" in l_lower:
                observacion = l
            elif "kg" in l_lower or "bulto" in l_lower:
                peso_bulto = l.upper()
            elif re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', l):
                if not fecha: fecha = l
            elif ("+" in l or l.startswith("11") or l.startswith("15")) and len(re.sub(r'\D', '', l)) >= 8:
                if not telefono: telefono = l

        # 3. EXTRAER LOCALIDAD, DESTINATARIO Y DIRECCIÓN POR GEOMETRÍA (PALABRAS Y COORDENADAS)
        words = pagina.get_text("words")  # (x0, y0, x1, y1, word, block_no, line_no, word_no)
        
        words_loc = []
        words_dest = []
        words_dir = []

        # Coordenadas relativas de la etiqueta apaisada original
        # W_orig, H_orig
        w_orig = r_pag.width
        h_orig = r_pag.height

        for w in words:
            txt = w[4].strip()
            x0, y0 = w[0], w[1]

            # Ignorar palabras fijas de sistema o encabezados que ensucian
            if txt.upper() in ["GOXP", "LOGÍSTICA", "LOGISTICA", "JYJ", "J&J", "DESTINATARIO", "REMITENTE"]:
                continue
            if any(k in txt.lower() for k in ["rte:", "venta:", "envio:", "observaci", "total"]):
                continue

            # A. ZONA LOCALIDAD: Arriba Izquierda (X < 32% del ancho original, Y < 30% del alto)
            if x0 < w_orig * 0.32 and y0 < h_orig * 0.30:
                if not re.search(r'\d', txt) and "/" not in txt:
                    words_loc.append(w)

            # B. ZONA DESTINATARIO: Centro Superior (32% < X < 68% del ancho, Y < 35% del alto)
            elif w_orig * 0.28 <= x0 <= w_orig * 0.68 and y0 < h_orig * 0.38:
                if not re.search(r'\d', txt) and "/" not in txt and "+" not in txt:
                    words_dest.append(w)

            # C. ZONA DIRECCIÓN: Centro Medio/Inferior
            elif w_orig * 0.25 <= x0 <= w_orig * 0.70 and y0 >= h_orig * 0.38:
                if "cp:" not in txt.lower() and "+" not in txt and "11" not in txt:
                    words_dir.append(w)

        # Ordenar palabras por coordenada Y (renglón) y X (secuencia)
        def armar_texto(lista_words):
            if not lista_words: return ""
            # Agrupar por renglón aproximado Y
            filas = {}
            for w in lista_words:
                y_key = round(w[1] / 6) * 6
                filas.setdefault(y_key, []).append(w)
            
            lineas_res = []
            for y_k in sorted(filas.keys()):
                palabras_f = sorted(filas[y_k], key=lambda x: x[0])
                lineas_res.append(" ".join([w[4] for w in palabras_f]))
            return " ".join(lineas_res).strip()

        localidad = armar_texto(words_loc).upper()
        destinatario = armar_texto(words_dest).upper()
        direccion = armar_texto(words_dir)

        # Respaldo si alguna coordenada se solapó
        if not destinatario and len(words_loc) > 0:
            # Si se confundió localidad con destinatario
            destinatario = localidad
            localidad = ""

        # 4. CONSTRUCCIÓN DE LA HOJA 10x15
        nueva_pag = doc_destino.new_page(width=ANCHO, height=ALTO)
        m = 10
        y_cursor = m

        # ENCABEZADO: LOGO + BULTO
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

    st.success("¡Etiqueta procesada con éxito!")

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
        ">🖨️ Imprimir en Térmica</button>
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
