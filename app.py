import streamlit as st
import fitz  # PyMuPDF
import io
import re

st.set_page_config(page_title="Generador 10x15 Pro", page_icon="🏷️", layout="centered")

st.title("🏷️ Generador de Etiquetas 10x15")
st.write("Lee dinámicamente tu etiqueta y recrea el formato exacto en 10x15 cm.")

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

        # -------------------------------------------------------------
        # 1. EXTRAER IMÁGENES (QR Y LOGO)
        # -------------------------------------------------------------
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

        # -------------------------------------------------------------
        # 2. CAPTURA Y PARSEO ROBUSTO DE DATOS
        # -------------------------------------------------------------
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

        # Mapeo explicito por expresiones clave
        lineas_descarte = []
        for l in lineas:
            l_lower = l.lower()
            if "cp:" in l_lower or "cp " in l_lower:
                cp = l
                lineas_descarte.append(l)
            elif "rte" in l_lower:
                remitente = re.sub(r'(?i)rte\.?:?', '', l).strip()
                lineas_descarte.append(l)
            elif "venta" in l_lower:
                venta = re.sub(r'(?i)venta:?', '', l).strip()
                lineas_descarte.append(l)
            elif "envio" in l_lower or "envío" in l_lower:
                envio = re.sub(r'(?i)env[ií]o:?', '', l).strip()
                lineas_descarte.append(l)
            elif "observaci" in l_lower or "ref:" in l_lower:
                observacion = l
                lineas_descarte.append(l)
            elif "kg" in l_lower or "bulto" in l_lower:
                peso_bulto = l
                lineas_descarte.append(l)
            elif re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', l):
                fecha = l
                lineas_descarte.append(l)
            elif "+" in l or l.startswith("11") or l.startswith("15"):
                if not telefono:
                    telefono = l
                    lineas_descarte.append(l)

        # Captura de Localidad (Suele ser la primera línea en mayúsculas sin números)
        for l in lineas:
            if l not in lineas_descarte and not re.search(r'\d', l):
                if any(zone in l.lower() for zone in ["esteban", "echeverria", "solano", "quilmes", "lanus", "avellaneda", "san isidro", "caba", "zona"]):
                    localidad = l.upper()
                    lineas_descarte.append(l)
                    break

        if not localidad:
            for l in lineas:
                if l not in lineas_descarte and l.isupper() and len(l) > 3 and not re.search(r'\d', l):
                    localidad = l
                    lineas_descarte.append(l)
                    break

        # Captura de Destinatario y Dirección entre las líneas restantes
        lineas_restantes = [l for l in lineas if l not in lineas_descarte and l.lower() not in ["destinatario", "remitente"]]

        if len(lineas_restantes) > 0:
            destinatario = lineas_restantes[0].upper()
        if len(lineas_restantes) > 1:
            direccion = " ".join(lineas_restantes[1:])

        # -------------------------------------------------------------
        # 3. CONSTRUCCIÓN DE LA NUEVA ETIQUETA 10x15
        # -------------------------------------------------------------
        nueva_pag = doc_destino.new_page(width=ANCHO, height=ALTO)
        m = 10  # Margen externo

        # A. QR e Imagen del Logo (Tamaños similares en el encabezado)
        tam_encabezado = 115

        # QR Arriba a la Izquierda
        if qr_pix:
            rect_qr = fitz.Rect(m, m, m + tam_encabezado, m + tam_encabezado)
            nueva_pag.insert_image(rect_qr, pixmap=qr_pix)

        x_der = m + tam_encabezado + 10
        ancho_disponible_der = ANCHO - m - x_der

        # Logo Arriba a la Derecha (Escalado simétrico con el QR)
        y_der = m
        if logo_pix:
            aspecto = logo_pix.width / logo_pix.height
            ancho_logo = ancho_disponible_der
            alto_logo = ancho_logo / aspecto
            
            if alto_logo > 55:
                alto_logo = 55
                ancho_logo = alto_logo * aspecto

            rect_logo = fitz.Rect(x_der, y_der, x_der + ancho_logo, y_der + alto_logo)
            nueva_pag.insert_image(rect_logo, pixmap=logo_pix)
            y_der += alto_logo + 10

        # Localidad debajo del Logo (a la derecha)
        if localidad:
            rect_loc = fitz.Rect(x_der, y_der, ANCHO - m, m + tam_encabezado)
            nueva_pag.insert_textbox(rect_loc, localidad, fontsize=12, fontname="hebo")

        # Línea divisora del encabezado
        y = m + tam_encabezado + 8
        nueva_pag.draw_line(fitz.Point(m, y), fitz.Point(ANCHO - m, y), color=(0, 0, 0), width=1)

        # B. Bloque Destinatario (Centro)
        y += 10
        nueva_pag.insert_text(fitz.Point(m, y), "Destinatario", fontsize=8, fontname="helv")
        y += 16

        if destinatario:
            nueva_pag.insert_text(fitz.Point(m, y), destinatario, fontsize=11.5, fontname="hebo")
            y += 15

        if telefono:
            nueva_pag.insert_text(fitz.Point(m, y), telefono, fontsize=9, fontname="helv")

        # Fecha y Peso alineados a la derecha
        if fecha:
            nueva_pag.insert_text(fitz.Point(ANCHO - m - 65, y - 15), fecha, fontsize=8.5, fontname="helv")
        if peso_bulto:
            nueva_pag.insert_text(fitz.Point(ANCHO - m - 65, y), peso_bulto, fontsize=8.5, fontname="hebo")

        y += 15
        nueva_pag.draw_line(fitz.Point(m, y), fitz.Point(ANCHO - m, y), color=(0, 0, 0), width=1)

        # C. Bloque Inferior: Datos de Envío, Dirección y Observaciones
        y += 10
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
