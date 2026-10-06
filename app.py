import streamlit as st
import fitz  # PyMuPDF
import io
import re

st.set_page_config(page_title="Generador de Etiquetas 10x15", page_icon="🏷️", layout="centered")

st.title("🏷️ Generador de Etiquetas 10x15")
st.write("Genera la estructura exacta de maqueta 10x15 cm alineada con el modelo estándar.")

archivo_subido = st.file_uploader("Seleccionar archivo PDF", type=["pdf"])

if archivo_subido:
    # Dimensiones 10x15 cm en puntos (100x150 mm)
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

        # Mapeo dinámico de datos
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
            elif any(k in l_lower for k in ["boulevard", "calle", "av", "piso", "canning", "barrio"]):
                if not direccion:
                    direccion = l
            elif "esteban" in l_lower or "echeverria" in l_lower or "solano" in l_lower:
                localidad = l.upper()

        # Asignaciones de respaldo si alguna variable falló en el reconocimiento
        if not localidad and len(lineas) > 0: localidad = lineas[0].upper()
        if not destinatario and len(lineas) > 1: destinatario = lineas[1].upper()
        if not direccion and len(lineas) > 4: direccion = lineas[4]

        # 3. Diseñar nueva página 10x15 (Estructura Modelo Vellón)
        nueva_pag = doc_destino.new_page(width=ANCHO, height=ALTO)
        m = 8  # Margen general

        # --- SECCIÓN SUPERIOR: QR a la izquierda, Logo y Localidad a la derecha ---
        tam_qr = 135
        if qr_pix:
            rect_qr = fitz.Rect(m, m, m + tam_qr, m + tam_qr)
            nueva_pag.insert_image(rect_qr, pixmap=qr_pix)

        x_der = m + tam_qr + 10
        y_der = m + 5

        # Logo de empresa arriba a la derecha
        if logo_pix:
            rect_logo = fitz.Rect(x_der, y_der, ANCHO - m, y_der + 35)
            nueva_pag.insert_image(rect_logo, pixmap=logo_pix)
            y_der += 42

        # Localidad / Zona destacada en gigante a la derecha del QR
        if localidad:
            rect_loc = fitz.Rect(x_der, y_der, ANCHO - m, m + tam_qr)
            nueva_pag.insert_textbox(rect_loc, localidad, fontsize=13, fontname="hebo")

        # Línea divisora bajo el QR
        y_cursor = m + tam_qr + 8
        nueva_pag.draw_line(fitz.Point(m, y_cursor), fitz.Point(ANCHO - m, y_cursor), color=(0, 0, 0), width=1)

        # --- SECCIÓN CENTRAL: Destinatario ---
        y_cursor += 10
        nueva_pag.insert_text(fitz.Point(m, y_cursor), "Destinatario", fontsize=8, fontname="helv")
        y_cursor += 16

        if destinatario:
            nueva_pag.insert_text(fitz.Point(m, y_cursor), destinatario, fontsize=12, fontname="hebo")
            y_cursor += 15

        if telefono:
            nueva_pag.insert_text(fitz.Point(m, y_cursor), telefono, fontsize=9.5, fontname="helv")

        # Fecha y Peso alineados a la derecha
        if fecha:
            nueva_pag.insert_text(fitz.Point(ANCHO - m - 65, y_cursor - 15), fecha, fontsize=9, fontname="helv")
        if peso_bulto:
            nueva_pag.insert_text(fitz.Point(ANCHO - m - 65, y_cursor), peso_bulto, fontsize=9, fontname="hebo")

        y_cursor += 15
        nueva_pag.draw_line(fitz.Point(m, y_cursor), fitz.Point(ANCHO - m, y_cursor), color=(0, 0, 0), width=1)

        # --- SECCIÓN INFERIOR: Rte, Venta, Envío, Dirección y Observación ---
        y_cursor += 10

        if remitente:
            nueva_pag.insert_text(fitz.Point(m, y_cursor), f"Rte.: {remitente}", fontsize=8.5, fontname="helv")
            y_cursor += 12
        if venta:
            nueva_pag.insert_text(fitz.Point(m, y_cursor), f"Venta: {venta}", fontsize=8.5, fontname="helv")
            y_cursor += 12
        if envio:
            nueva_pag.insert_text(fitz.Point(m, y_cursor), f"Envio: {envio}", fontsize=8.5, fontname="helv")
            y_cursor += 15

        # Dirección destacada en negrita
        if direccion:
            texto_dir = f"{direccion} {cp}".strip()
            rect_dir = fitz.Rect(m, y_cursor, ANCHO - m, y_cursor + 30)
            nueva_pag.insert_textbox(rect_dir, texto_dir, fontsize=9.5, fontname="hebo")
            y_cursor += 32

        # Observación al pie
        if observacion:
            rect_obs = fitz.Rect(m, y_cursor, ANCHO - m, ALTO - m)
            nueva_pag.insert_textbox(rect_obs, observacion, fontsize=8, fontname="helv")

    # Guardar PDF resultante
    output_buffer = io.BytesIO()
    doc_destino.save(output_buffer)
    doc_destino.close()
    doc_origen.close()

    st.success("¡Etiqueta maquetada correctamente en formato 10x15 cm!")

    st.download_button(
        label="📥 Descargar PDF 10x15",
        data=output_buffer.getvalue(),
        file_name=f"10x15_{archivo_subido.name}",
        mime="application/pdf",
        type="primary"
    )
