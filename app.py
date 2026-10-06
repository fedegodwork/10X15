import streamlit as st
import fitz  # PyMuPDF
import io
import re

st.set_page_config(page_title="Generador 10x15 Pro", page_icon="🏷️", layout="centered")

st.title("🏷️ Generador de Etiquetas 10x15")
st.write("Genera la maqueta con la disposición exacta de zonas y bloques.")

archivo_subido = st.file_uploader("Seleccionar archivo PDF", type=["pdf"])

if archivo_subido:
    ANCHO = 100 * 2.83465  # 100 mm en puntos (283.465 pt)
    ALTO = 150 * 2.83465   # 150 mm en puntos (425.197 pt)

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

        # 2. LECTURA Y PARSEO DE DATOS
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

        lineas_conocidas = []
        for l in lineas:
            l_lower = l.lower()
            if "cp:" in l_lower or "cp " in l_lower:
                cp = l
                lineas_conocidas.append(l)
            elif "rte" in l_lower:
                remitente = re.sub(r'(?i)rte\.?:?', '', l).strip()
                lineas_conocidas.append(l)
            elif "venta" in l_lower:
                venta = re.sub(r'(?i)venta:?', '', l).strip()
                lineas_conocidas.append(l)
            elif "envio" in l_lower or "envío" in l_lower:
                envio = re.sub(r'(?i)env[ií]o:?', '', l).strip()
                lineas_conocidas.append(l)
            elif "observaci" in l_lower or "ref:" in l_lower:
                observacion = l
                lineas_conocidas.append(l)
            elif "kg" in l_lower or "bulto" in l_lower:
                peso_bulto = l.upper()
                lineas_conocidas.append(l)
            elif "/" in l and len(l) <= 10:
                fecha = l
                lineas_conocidas.append(l)
            elif "+" in l or l.startswith("11") or l.startswith("15"):
                if not telefono:
                    telefono = l
                    lineas_conocidas.append(l)

        # Buscar Localidad
        for l in lineas:
            if l not in lineas_conocidas and not re.search(r'\d', l) and l.upper() not in ["GOXP", "LOGÍSTICA", "LOGISTICA", "DESTINATARIO"]:
                localidad = l.upper()
                lineas_conocidas.append(l)
                break

        # Destinatario y Dirección
        lineas_entrega = []
        for l in lineas:
            if l in lineas_conocidas or l.upper() in ["GOXP", "LOGÍSTICA", "LOGISTICA", "DESTINATARIO"]:
                continue
            lineas_entrega.append(l)

        if len(lineas_entrega) > 0:
            destinatario = lineas_entrega[0].upper()
        if len(lineas_entrega) > 1:
            direccion = " ".join(lineas_entrega[1:])

        # 3. DISEÑAR ETIQUETA 10x15 (DISEÑO EXACTO FOTO 2)
        nueva_pag = doc_destino.new_page(width=ANCHO, height=ALTO)
        m = 10  # Margen externo
        y_cursor = m

        # --- SECCIÓN 1: ENCABEZADO (LOGO A LA IZQ | BULTO A LA DER) ---
        if logo_pix:
            aspecto = logo_pix.width / logo_pix.height
            alto_logo = 32
            ancho_logo = alto_logo * aspecto
            rect_logo = fitz.Rect(m, y_cursor, m + ancho_logo, y_cursor + alto_logo)
            nueva_pag.insert_image(rect_logo, pixmap=logo_pix)

        if peso_bulto:
            txt_bulto = peso_bulto if "BULTO" in peso_bulto else f"BULTO {peso_bulto}"
            nueva_pag.insert_text(fitz.Point(ANCHO - m - 90, y_cursor + 20), txt_bulto, fontsize=11, fontname="hebo")

        y_cursor += 38

        # --- SECCIÓN 2: FRANJA DE LOCALIDAD (ANCHO COMPLETO, FONDO NEGRO) ---
        if localidad:
            alto_franja = 28
            rect_franja = fitz.Rect(m, y_cursor, ANCHO - m, y_cursor + alto_franja)
            
            # Dibujar rectángulo negro con esquinas levemente redondeadas
            nueva_pag.draw_rect(rect_franja, color=(0, 0, 0), fill=(0, 0, 0), radius=3)
            
            # Texto centrado blanco grande
            nueva_pag.insert_textbox(
                rect_franja, 
                localidad, 
                fontsize=13, 
                fontname="hebo", 
                color=(1, 1, 1), 
                align=1
            )
            y_cursor += alto_franja + 12

        # --- SECCIÓN 3: QR (IZQUIERDA) + DATOS DE SEGUIMIENTO (DERECHA) ---
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

        # --- SECCIÓN 4: DESTINATARIO Y DIRECCIÓN DE ENTREGA ---
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
    doc_destino.close()
    doc_origen.close()

    st.success("¡Etiqueta adaptada con éxito al formato 10x15 cm!")

    st.download_button(
        label="📥 Descargar PDF 10x15",
        data=output_buffer.getvalue(),
        file_name=f"10x15_{archivo_subido.name}",
        mime="application/pdf",
        type="primary"
    )
