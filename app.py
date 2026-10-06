import streamlit as st
import fitz  # PyMuPDF
import io
import re

st.set_page_config(page_title="Generador 10x15 Pro", page_icon="🏷️", layout="centered")

st.title("🏷️ Generador de Etiquetas 10x15")
st.write("Lee dinámicamente tu etiqueta y recrea el formato exacto en 10x15 cm.")

archivo_subido = st.file_uploader("Seleccionar archivo PDF", type=["pdf"])

if archivo_subido:
    ANCHO = 100 * 2.83465  # 283.465 pt (100 mm)
    ALTO = 150 * 2.83465   # 425.197 pt (150 mm)

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

        # 2. LECTURA COMPLETA DE TEXTO LÍNEA POR LÍNEA
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

        # Mapeo explicito de metadatos
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
                peso_bulto = l
                lineas_conocidas.append(l)
            elif "/" in l and len(l) <= 10:
                fecha = l
                lineas_conocidas.append(l)
            elif "+" in l or l.startswith("11") or l.startswith("15"):
                if not telefono:
                    telefono = l
                    lineas_conocidas.append(l)

        # Buscar Localidad (primer texto en mayúsculas sin números que coincida o esté al principio)
        for l in lineas:
            if l not in lineas_conocidas and not re.search(r'\d', l) and l.upper() not in ["GOXP", "LOGÍSTICA", "LOGISTICA", "DESTINATARIO"]:
                localidad = l.upper()
                lineas_conocidas.append(l)
                break

        # Todo lo que queda libre y no es marca/encabezado ES el Destinatario y la Dirección
        lineas_entrega = []
        for l in lineas:
            if l in lineas_conocidas:
                continue
            if l.upper() in ["GOXP", "LOGÍSTICA", "LOGISTICA", "DESTINATARIO"]:
                continue
            lineas_entrega.append(l)

        if len(lineas_entrega) > 0:
            destinatario = lineas_entrega[0].upper()
        if len(lineas_entrega) > 1:
            direccion = " ".join(lineas_entrega[1:])

        # 3. CONSTRUCCIÓN DE LA HOJA 10x15
        nueva_pag = doc_destino.new_page(width=ANCHO, height=ALTO)
        m = 10  # Margen

        # A. ENCABEZADO: QR (Izquierda) + Logo (Derecha)
        tam_qr = 115
        if qr_pix:
            rect_qr = fitz.Rect(m, m, m + tam_qr, m + tam_qr)
            nueva_pag.insert_image(rect_qr, pixmap=qr_pix)

        x_der = m + tam_qr + 10
        ancho_der = ANCHO - m - x_der
        y_der = m

        if logo_pix:
            aspecto = logo_pix.width / logo_pix.height
            ancho_l = ancho_der
            alto_l = ancho_l / aspecto
            if alto_l > 50:
                alto_l = 50
                ancho_l = alto_l * aspecto
            rect_logo = fitz.Rect(x_der, y_der, x_der + ancho_l, y_der + alto_l)
            nueva_pag.insert_image(rect_logo, pixmap=logo_pix)
            y_der += alto_l + 8

        if localidad:
            rect_loc = fitz.Rect(x_der, y_der, ANCHO - m, m + tam_qr)
            nueva_pag.insert_textbox(rect_loc, localidad, fontsize=11.5, fontname="hebo")

        # Línea divisora 1
        y = m + tam_qr + 8
        nueva_pag.draw_line(fitz.Point(m, y), fitz.Point(ANCHO - m, y), color=(0, 0, 0), width=1)

        # B. BLOQUE DESTINATARIO
        y += 10
        nueva_pag.insert_text(fitz.Point(m, y), "Destinatario", fontsize=8, fontname="helv")
        y += 16

        if destinatario:
            nueva_pag.insert_text(fitz.Point(m, y), destinatario, fontsize=12, fontname="hebo")
            y += 15

        if telefono:
            nueva_pag.insert_text(fitz.Point(m, y), telefono, fontsize=9, fontname="helv")

        if fecha:
            nueva_pag.insert_text(fitz.Point(ANCHO - m - 65, y - 15), fecha, fontsize=8.5, fontname="helv")
        if peso_bulto:
            nueva_pag.insert_text(fitz.Point(ANCHO - m - 65, y), peso_bulto, fontsize=8.5, fontname="hebo")

        # Línea divisora 2
        y += 15
        nueva_pag.draw_line(fitz.Point(m, y), fitz.Point(ANCHO - m, y), color=(0, 0, 0), width=1)

        # C. BLOQUE INFERIOR: SEGUIMIENTO, DIRECCIÓN Y OBSERVACIONES
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

        # DIRECCIÓN DE ENTREGA (IMPRESCINDIBLE)
        if direccion:
            texto_dir = f"{direccion} {cp}".strip()
            rect_dir = fitz.Rect(m, y, ANCHO - m, y + 32)
            nueva_pag.insert_textbox(rect_dir, texto_dir, fontsize=10, fontname="hebo")
            y += 34

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
