import streamlit as st
import fitz  # PyMuPDF
import io
import re

st.set_page_config(page_title="Generador 10x15 Pro", page_icon="🏷️", layout="centered")

st.title("🏷️ Generador de Etiquetas 10x15")
st.write("Procesa cualquier etiqueta adaptando el diseño exactamente al formato 10x15 cm.")

archivo_subido = st.file_uploader("Seleccionar archivo PDF", type=["pdf"])

if archivo_subido:
    # Dimensiones 10x15 cm en puntos (100x150 mm)
    ANCHO = 100 * 2.83465  # 283.465 pt
    ALTO = 150 * 2.83465   # 425.197 pt

    bytes_pdf = archivo_subido.read()
    doc_origen = fitz.open(stream=bytes_pdf, filetype="pdf")
    doc_destino = fitz.open()

    for pagina in doc_origen:
        r_pag = pagina.rect

        # --- 1. EXTRAER IMÁGENES (QR Y LOGO) ---
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

        # --- 2. EXTRAER Y PARSEAR TEXTO ---
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

        # Mapeo por expresiones clave
        for l in lineas:
            l_lower = l.lower()
            if "cp:" in l_lower or "cp " in l_lower:
                cp = l
            elif "rte" in l_lower:
                remitente = re.sub(r'(?i)rte\.?:?', '', l).strip()
            elif "venta" in l_lower:
                venta = re.sub(r'(?i)venta:?', '', l).strip()
            elif "envio" in l_lower or "envío" in l_lower:
                envio = re.sub(r'(?i)env[ií]o:?', '', l).strip()
            elif "observaci" in l_lower or "ref:" in l_lower:
                observacion = l
            elif "kg" in l_lower or "bulto" in l_lower:
                peso_bulto = l
            elif "/" in l and len(l) <= 10:
                fecha = l
            elif "+" in l or l.startswith("11") or l.startswith("15"):
                if not telefono:
                    telefono = l

        # Extracción por bloques vectoriales completos (Evita omitir nombres o apellidos)
        bloques = pagina.get_text("blocks") # (x0, y0, x1, y1, text, block_no, block_type)
        
        # El bloque de localidad suele estar arriba a la izquierda
        for b in bloques:
            if b[0] < r_pag.width * 0.35 and b[1] < r_pag.height * 0.30:
                txt = b[4].strip()
                if txt and not any(k in txt.lower() for k in ["http", "www", "kg"]):
                    localidad = txt.upper()
                    break

        # El bloque central contiene Destinatario y Dirección
        bloques_centro = [b for b in bloques if r_pag.width * 0.20 <= b[0] <= r_pag.width * 0.70]
        
        textos_centro = []
        for b in bloques_centro:
            lines_b = [l.strip() for l in b[4].split("\n") if l.strip()]
            for l in lines_b:
                if any(k in l.lower() for k in ["kg", "+54", "observaci", "cp:", "venta:", "rte:"]) or l.upper() == localidad:
                    continue
                textos_centro.append(l)

        if len(textos_centro) > 0:
            # Captura el nombre completo (ej: "Veronica Pugliese")
            destinatario = textos_centro[0].upper()
        if len(textos_centro) > 1:
            direccion = " ".join(textos_centro[1:])

        # --- 3. DISEÑAR ETIQUETA EN 10x15 (MODELO VELLÓN) ---
        nueva_pag = doc_destino.new_page(width=ANCHO, height=ALTO)
        m = 10  # Margen externo

        # A. QR Grande a la Izquierda
        tam_qr = 135
        if qr_pix:
            rect_qr = fitz.Rect(m, m, m + tam_qr, m + tam_qr)
            nueva_pag.insert_image(rect_qr, pixmap=qr_pix)

        x_der = m + tam_qr + 10
        y_der = m + 5

        # B. Logo Grande y Localidad a la Derecha
        if logo_pix:
            # Calcular escalado proporcional grande para el logo
            ancho_max_logo = ANCHO - m - x_der
            alto_max_logo = 50
            
            aspecto = logo_pix.width / logo_pix.height
            ancho_logo = min(ancho_max_logo, alto_max_logo * aspecto)
            alto_logo = ancho_logo / aspecto
            
            rect_logo = fitz.Rect(x_der, y_der, x_der + ancho_logo, y_der + alto_logo)
            nueva_pag.insert_image(rect_logo, pixmap=logo_pix)
            y_der += alto_logo + 10

        if localidad:
            rect_loc = fitz.Rect(x_der, y_der, ANCHO - m, m + tam_qr)
            nueva_pag.insert_textbox(rect_loc, localidad, fontsize=12, fontname="hebo")

        # Línea divisora
        y = m + tam_qr + 8
        nueva_pag.draw_line(fitz.Point(m, y), fitz.Point(ANCHO - m, y), color=(0, 0, 0), width=1)

        # C. Bloque Destinatario (Centro)
        y += 12
        nueva_pag.insert_text(fitz.Point(m, y), "Destinatario", fontsize=8, fontname="helv")
        y += 18

        if destinatario
