import streamlit as st
import fitz  # PyMuPDF
import io
import re

st.set_page_config(page_title="Generador 10x15 Pro", page_icon="🏷️", layout="centered")

st.title("🏷️ Generador de Etiquetas 10x15")
st.write("Procesa cualquier etiqueta sin omitir el destinatario ni requerir librerías extra.")

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

        # --- 2. EXTRAER PALABRAS Y COORDENADAS ---
        words = pagina.get_text("words")  # (x0, y0, x1, y1, word, block_no, line_no, word_no)
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

        # Extracción de Localidad (Esq. superior izquierda original)
        words_loc = [w[4] for w in words if w[0] < r_pag.width * 0.30 and w[1] < r_pag.height * 0.25]
        if words_loc:
            localidad = " ".join(words_loc).upper()

        # Extracción del Destinatario y Dirección usando la columna central por coordenadas
        words_centro = [w for w in words if r_pag.width * 0.25 <= w[0] <= r_pag.width * 0.68]
        
        # Agrupar por líneas (Y parecida)
        lineas_centro_dict = {}
        for w in words_centro:
            y_key = round(w[1] / 7) * 7
            lineas_centro_dict.setdefault(y_key, []).append(w)

        lineas_centro_ordenadas = [
            " ".join([w[4] for w in sorted(lineas_centro_dict[k], key=lambda x: x[0])])
            for k in sorted(lineas_centro_dict.keys())
        ]

        # Filtrar líneas que no sean metadatos
        lineas_limpias = []
        for l in lineas_centro_ordenadas:
            if any(k in l.lower() for k in ["kg", "+54", "observaci", "cp:", "venta:", "rte:"]) or l.upper() == localidad:
                continue
            lineas_limpias.append(l)

        if len(lineas_limpias) > 0:
            destinatario = lineas_limpias[0].upper()
        if len(lineas_limpias) > 1:
            direccion = " ".join(lineas_limpias[1:])

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

        # B. Logo y Localidad a la Derecha
        if logo_pix:
            rect_logo = fitz.Rect(x_der, y_der, ANCHO - m, y_der + 32)
            nueva_pag.insert_image(rect_logo, pixmap=logo_pix)
            y_der += 38

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

        if destinatario:
            nueva_pag.insert_text(fitz.Point(m, y), destinatario, fontsize=11.5, fontname="hebo")
            y += 15

        if telefono:
            nueva_pag.insert_text(fitz.Point(m, y), telefono, fontsize=9, fontname="helv")

        # Fecha y Peso/Bulto alineados a la derecha
        if fecha:
            nueva_pag.insert_text(fitz.Point(ANCHO - m - 65, y - 15), fecha, fontsize=8.5, fontname="helv")
        if peso_bulto:
            nueva_pag.insert_text(fitz.Point(ANCHO - m - 65, y), peso_bulto, fontsize=8.5, fontname="hebo")

        y += 15
        nueva_pag.draw_line(fitz.Point(m, y), fitz.Point(ANCHO - m, y), color=(0, 0, 0), width=1)

        # D. Bloque Inferior
        y += 12
        if remitente:
            nueva_pag.insert_text(fitz.Point(m, y), f"Rte.: {remitente}", fontsize=8.5, fontname="helv")
            y += 12
        if venta:
            nueva_pag.insert_text(fitz.Point(m, y), f"Venta: {venta}", fontsize=8.5, fontname="helv")
            y += 12
        if envio:
            nueva_pag.insert_text(fitz.Point(m, y), f"Envio: {envio}", fontsize=8.5, fontname="helv")
            y += 14

        if direccion:
            texto_dir = f"{direccion} {cp}".strip()
            rect_dir = fitz.Rect(m, y, ANCHO - m, y + 28)
            nueva_pag.insert_textbox(rect_dir, texto_dir, fontsize=9.5, fontname="hebo")
            y += 30

        if observacion:
            rect_obs = fitz.Rect(m, y, ANCHO - m, ALTO - m)
            nueva_pag.insert_textbox(rect_obs, observacion, fontsize=8, fontname="helv")

    # Guardar PDF resultante
    output_buffer = io.BytesIO()
    doc_destino.save(output_buffer)
    doc_destino.close()
    doc_origen.close()

    st.success("¡Etiqueta rediseñada con éxito a 10x15 cm!")

    st.download_button(
        label="📥 Descargar PDF 10x15",
        data=output_buffer.getvalue(),
        file_name=f"10x15_{archivo_subido.name}",
        mime="application/pdf",
        type="primary"
    )
