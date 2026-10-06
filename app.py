import streamlit as st
import fitz  # PyMuPDF
import io
import re

st.set_page_config(page_title="Generador 10x15 Pro", page_icon="🏷️", layout="centered")

st.title("🏷️ Generador de Etiquetas 10x15")
st.write("Procesa la etiqueta sin perder información y recrea el formato 10x15 cm.")

archivo_subido = st.file_uploader("Seleccionar archivo PDF", type=["pdf"])

if archivo_subido:
    # Dimensiones 10x15 cm en puntos (100x150 mm)
    ANCHO = 100 * 2.83465  # 283.465 pt
    ALTO = 150 * 2.83465   # 425.197 pt

    bytes_pdf = archivo_subido.read()
    doc_origen = fitz.open(stream=bytes_pdf, filetype="pdf")
    doc_destino = fitz.open()

    for pagina in doc_origen:
        # 1. Extraer imágenes físicas (QR y Logo)
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

        # 2. Leer todas las líneas de texto
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

        lineas_no_clasificadas = []

        # Clasificación por patrones
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
            elif re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', l):
                fecha = l
            elif "+" in l or l.startswith("11") or l.startswith("15") or "phone" in l_lower:
                if not telefono:
                    telefono = l
            elif l_lower in ["destinatario", "remitente"]:
                continue
            else:
                lineas_no_clasificadas.append(l)

        # Asignación inteligente de remanentes para no perder destinatario ni localidad
        if len(lineas_no_clasificadas) > 0:
            destinatario = lineas_no_clasificadas[0].upper()
        if len(lineas_no_clasificadas) > 1:
            localidad = lineas_no_clasificadas[1].upper()
        if len(lineas_no_clasificadas) > 2:
            direccion = " ".join(lineas_no_clasificadas[2:])

        # 3. Diseñar nueva página 10x15 (Estructura Modelo Vellón)
        nueva_pag = doc_destino.new_page(width=ANCHO, height=ALTO)
        m = 10  # Margen externo

        # A. QR Grande Arriba a la Izquierda
        tam_qr = 130
        if qr_pix:
            rect_qr = fitz.Rect(m, m, m + tam_qr, m + tam_qr)
            nueva_pag.insert_image(rect_qr, pixmap=qr_pix)

        x_der = m + tam_qr + 10
        y_der = m + 5

        # B. Logo y Localidad a la Derecha del QR
        if logo_pix:
            rect_logo = fitz.Rect(x_der, y_der, ANCHO - m, y_der + 30)
            nueva_pag.insert_image(rect_logo, pixmap=logo_pix)
            y_der += 35

        if localidad:
            rect_loc = fitz.Rect(x_der, y_der, ANCHO - m, m + tam_qr)
            nueva_pag.insert_textbox(rect_loc, localidad, fontsize=12, fontname="hebo")

        # Línea divisora
        y = m + tam_qr + 10
        nueva_pag.draw_line(fitz.Point(m, y), fitz.Point(ANCHO - m, y), color=(0, 0, 0), width=1)

        # C. Bloque Destinatario (Centro)
        y += 12
        nueva_pag.insert_text(fitz.Point(m, y), "Destinatario", fontsize=8, fontname="helv")
        y += 16

        if destinatario:
            nueva_pag.insert_text(fitz.Point(m, y), destinatario, fontsize=11, fontname="hebo")
            y += 14

        if telefono:
            nueva_pag.insert_text(fitz.Point(m, y), telefono, fontsize=8.5, fontname="helv")

        # Fecha y Bulto alineados a la derecha
        if fecha:
            nueva_pag.insert_text(fitz.Point(ANCHO - m - 60, y - 14), fecha, fontsize=8.5, fontname="helv")
        if peso_bulto:
            nueva_pag.insert_text(fitz.Point(ANCHO - m - 60, y), peso_bulto, fontsize=8.5, fontname="hebo")

        y += 14
        nueva_pag.draw_line(fitz.Point(m, y), fitz.Point(ANCHO - m, y), color=(0, 0, 0), width=1)

        # D. Bloque Inferior: Datos de Envío y Dirección
        y += 12
        if remitente:
            nueva_pag.insert_text(fitz.Point(m, y), f"Rte.: {remitente}", fontsize=8, fontname="helv")
            y += 11
        if venta:
            nueva_pag.insert_text(fitz.Point(m, y), f"Venta: {venta}", fontsize=8, fontname="helv")
            y += 11
        if envio:
            nueva_pag.insert_text(fitz.Point(m, y), f"Envio: {envio}", fontsize=8, fontname="helv")
            y += 13

        if direccion:
            texto_dir = f"{direccion} {cp}".strip()
            rect_dir = fitz.Rect(m, y, ANCHO - m, y + 25)
            nueva_pag.insert_textbox(rect_dir, texto_dir, fontsize=9, fontname="hebo")
            y += 28

        if observacion:
            rect_obs = fitz.Rect(m, y, ANCHO - m, ALTO - m)
            nueva_pag.insert_textbox(rect_obs, observacion, fontsize=8, fontname="helv")

    output_buffer = io.BytesIO()
    doc_destino.save(output_buffer)
    doc_destino.close()
    doc_origen.close()

    st.success("¡Etiqueta reestructurada correctamente a 10x15 cm!")

    st.download_button(
        label="📥 Descargar PDF 10x15",
        data=output_buffer.getvalue(),
        file_name=f"10x15_{archivo_subido.name}",
        mime="application/pdf",
        type="primary"
    )
