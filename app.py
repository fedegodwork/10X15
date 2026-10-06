import streamlit as st
import fitz  # PyMuPDF
import io
import re
import base64

st.set_page_config(page_title="Generador 10x15 Universal", page_icon="🏷️", layout="centered")

st.title("🏷️ Generador de Etiquetas 10x15")
st.write("Adaptador dinámico universal para impresoras térmicas.")

archivo_subido = st.file_uploader("Seleccionar archivo PDF", type=["pdf"])

if archivo_subido:
    ANCHO = 100 * 2.83465  # 100 mm (283.465 pt)
    ALTO = 150 * 2.83465   # 150 mm (425.197 pt)

    bytes_pdf = archivo_subido.read()
    doc_origen = fitz.open(stream=bytes_pdf, filetype="pdf")
    doc_destino = fitz.open()

    for pagina in doc_origen:
        r_pag = pagina.rect

        # 1. IDENTIFICACIÓN Y SEPARACIÓN CORRECTA DE QR Y LOGO
        qr_pix = None
        logo_pix = None

        try:
            for img_info in pagina.get_images():
                xref = img_info[0]
                pix = fitz.Pixmap(doc_origen, xref)
                if pix.alpha:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                
                # Un QR es casi perfectamente cuadrado (aspecto ~ 1.0)
                aspecto_img = pix.width / float(pix.height)
                if 0.85 <= aspecto_img <= 1.15 and not qr_pix:
                    qr_pix = pix
                elif not logo_pix:
                    logo_pix = pix
        except Exception:
            pass

        # 2. EXTRACCIÓN Y PARSEO DE TEXTO LÍNEA POR LÍNEA
        texto_completo = pagina.get_text("text")
        lineas_raw = [l.strip() for l in texto_completo.split("\n") if l.strip()]

        localidad = ""
        destinatario = ""
        telefono = ""
        peso_bulto = ""
        direccion = ""
        cp = ""
        observacion = "Sin información"
        fecha = ""
        remitente = ""
        venta = ""
        envio = ""

        lineas_usadas = set()

        # A. Captura de metadatos mediante Regex
        for l in lineas_raw:
            l_lower = l.lower()
            
            if ("cp:" in l_lower or "cp " in l_lower) and not cp:
                m = re.search(r'CP:?\s*(\d+)', l, re.IGNORECASE)
                cp = f"CP: {m.group(1)}" if m else l
                lineas_usadas.add(l)
            elif "rte" in l_lower and not remitente:
                remitente = re.sub(r'(?i)rte\.?:?', '', l).strip()
                lineas_usadas.add(l)
            elif "venta" in l_lower and not venta:
                venta = re.sub(r'(?i)venta:?', '', l).strip()
                lineas_usadas.add(l)
            elif ("envio" in l_lower or "envío" in l_lower) and not envio:
                envio = re.sub(r'(?i)env[ií]o:?', '', l).strip()
                lineas_usadas.add(l)
            elif ("observaci" in l_lower or "ref:" in l_lower) and observacion == "Sin información":
                observacion = l
                lineas_usadas.add(l)
            elif ("kg" in l_lower or "bulto" in l_lower) and not peso_bulto:
                peso_bulto = l.upper()
                lineas_usadas.add(l)
            elif re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', l) and not fecha:
                fecha = re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', l).group(0)
                lineas_usadas.add(l)
            elif ("+" in l or l.startswith("11") or l.startswith("15")) and len(re.sub(r'\D', '', l)) >= 8 and not telefono:
                telefono = l
                lineas_usadas.add(l)

        # B. Captura de Localidad (Evita marcas corporativas)
        palabras_ignorar = [
            "goxp", "logística", "logistica", "jyj", "j&j", 
            "destinatario", "remitente", "campos extra", "total a cobrar"
        ]

        for l in lineas_raw:
            if l in lineas_usadas or any(ign in l.lower() for ign in palabras_ignorar):
                continue
            # Buscar localidad conocida o patrones en mayúsculas sin números
            l_clean = l.strip().upper()
            if any(z in l_clean for z in ["ESTEBAN ECHEVERRIA", "ECHEVERRIA", "MORON", "MORÓN", "SOLANO", "QUILMES", "LANUS", "AVELLANEDA", "SAN ISIDRO", "CABA", "PALERMO", "MORENO", "MERLO", "SAN MARTIN", "TIGRE"]):
                localidad = l_clean
                lineas_usadas.add(l)
                break

        if not localidad:
            for l in lineas_raw:
                if l not in lineas_usadas and not re.search(r'\d', l) and len(l) >= 3:
                    if not any(ign in l.lower() for ign in palabras_ignorar):
                        localidad = l.upper()
                        lineas_usadas.add(l)
                        break

        # C. Captura Limpia de Destinatario y Dirección entre lo que sobra
        lineas_restantes = [
            l for l in lineas_raw 
            if l not in lineas_usadas and not any(ign in l.lower() for ign in palabras_ignorar)
        ]

        if len(lineas_restantes) > 0:
            destinatario = lineas_restantes[0].upper()
            lineas_usadas.add(lineas_restantes[0])

        direccion_partes = []
        for l in lineas_restantes[1:]:
            if l not in lineas_usadas:
                # Evitar que se cuelen fragmentos duplicados de Rte o Venta
                if not any(k in l.lower() for k in ["rte:", "venta:", "envio:", "fecha:"]):
                    direccion_partes.append(l)

        direccion = " ".join(direccion_partes).strip()

        # 3. DISEÑO DE LA HOJA 10x15 CM
        nueva_pag = doc_destino.new_page(width=ANCHO, height=ALTO)
        m = 10
        y_cursor = m

        # ENCABEZADO: LOGO (IZQ) Y BULTO (DER)
        if logo_pix:
            aspecto = logo_pix.width / float(logo_pix.height)
            alto_logo = 32
            ancho_logo = alto_logo * aspecto
            rect_logo = fitz.Rect(m, y_cursor, m + ancho_logo, y_cursor + alto_logo)
            nueva_pag.insert_image(rect_logo, pixmap=logo_pix)

        txt_bulto = peso_bulto if peso_bulto else "BULTO 1/1"
        nueva_pag.insert_text(fitz.Point(ANCHO - m - 90, y_cursor + 20), txt_bulto, fontsize=11, fontname="hebo")

        y_cursor += 38

        # FRANJA NEGRA DE LOCALIDAD
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

        # CÓDIGO QR GRANDE + DATOS DE SEGUIMIENTO
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

        # BLOQUE DESTINATARIO Y DIRECCIÓN
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
            texto_dir = f"{direccion} {cp}".strip() if cp and cp not in direccion else direccion
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
