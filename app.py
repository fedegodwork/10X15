import streamlit as st
import fitz  # PyMuPDF
import io
import re

st.set_page_config(page_title="Generador de Etiquetas 10x15", page_icon="🏷️", layout="centered")

st.title("🏷️ Generador de Etiquetas 10x15")
st.write("Lee los datos de tu etiqueta original y genera una nueva etiqueta estilo 10x15 cm.")

archivo_subido = st.file_uploader("Seleccionar archivo PDF", type=["pdf"])

if archivo_subido:
    # Dimensiones 10x15 cm en puntos
    ANCHO = 100 * 2.83465  # 283.465 pt
    ALTO = 150 * 2.83465   # 425.197 pt

    bytes_pdf = archivo_subido.read()
    doc_origen = fitz.open(stream=bytes_pdf, filetype="pdf")
    doc_destino = fitz.open()

    for pagina in doc_origen:
        # 1. Extraer imágenes (QR y Logo)
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

        # 2. Extraer texto por líneas
        texto_pag = pagina.get_text("text")
        lineas = [l.strip() for l in texto_pag.split("\n") if l.strip()]

        # Valores por defecto para evitar cuelgues
        localidad = lineas[0] if len(lineas) > 0 else "DESTINO"
        destinatario = lineas[1] if len(lineas) > 1 else ""
        telefono = ""
        peso_bulto = ""
        direccion = ""
        cp = ""
        observacion = ""
        fecha = ""
        remitente = ""
        venta = ""
        envio = ""

        # Parser por palabras clave
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
            elif "calle" in l_lower or "av" in l_lower or "boulevard" in l_lower or "piso" in l_lower or "n°" in l_lower:
                if not direccion:
                    direccion = l

        if not direccion and len(lineas) > 4:
            direccion = lineas[4]

        # 3. Diseñar nueva página 10x15 desde cero
        nueva_pag = doc_destino.new_page(width=ANCHO, height=ALTO)
        m = 10  # Margen

        # A. QR
        if qr_pix:
            tam_qr = 155
            rect_qr = fitz.Rect(m, m, m + tam_qr, m + tam_qr)
            nueva_pag.insert_image(rect_qr, pixmap=qr_pix)

        # B. Encabezado Localidad
        rect_loc = fitz.Rect(m + 160, m + 15, ANCHO - m, m + 80)
        nueva_pag.insert_textbox(rect_loc, localidad.upper(), fontsize=11, fontname="helv-bold")

        y = m + 165
        nueva_pag.draw_line(fitz.Point(m, y), fitz.Point(ANCHO - m, y), color=(0, 0, 0), width=1)

        # C. Bloque Destinatario
        y += 12
        nueva_pag.insert_text(fitz.Point(m, y), "Destinatario", fontsize=8, fontname="helv")
        y += 16

        if destinatario:
            nueva_pag.insert_text(fitz.Point(m, y), destinatario.upper(), fontsize=10.5, fontname="helv-bold")
            y += 14

        if telefono:
            nueva_pag.insert_text(fitz.Point(m, y), telefono, fontsize=8.5
