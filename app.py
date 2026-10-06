import streamlit as st
import fitz  # PyMuPDF
import io
import re

st.set_page_config(page_title="Generador de Etiquetas 10x15", page_icon="🏷️", layout="centered")

st.title("🏷️ Generador de Etiquetas 10x15")
st.write("Lee los datos de cualquier etiqueta apaisada y recrea la etiqueta exacta en formato 10x15 cm.")

archivo_subido = st.file_uploader("Seleccionar archivo PDF", type=["pdf"])

if archivo_subido:
    # Hoja 10x15 cm en puntos (100x150 mm)
    ANCHO = 100 * 2.83465  # 283.465 pt
    ALTO = 150 * 2.83465   # 425.197 pt

    bytes_pdf = archivo_subido.read()
    doc_origen = fitz.open(stream=bytes_pdf, filetype="pdf")
    doc_destino = fitz.open()

    for pagina in doc_origen:
        # --- 1. EXTRAER IMÁGENES (QR y Logo) ---
        imagenes = []
        for img_info in pagina.get_images():
            xref = img_info[0]
            pix = fitz.Pixmap(doc_origen, xref)
            if pix.alpha:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            imagenes.append(pix)

        qr_pix = imagenes[0] if len(imagenes) > 0 else None
        logo_pix = imagenes[1] if len(imagenes) > 1 else None

        # --- 2. EXTRAER Y PARSEAR DATO POR DATO DERECHO DEL PDF ---
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

        # Mapeo universal por patrones de datos
        for i, l in enumerate(lineas):
            if "CP:" in l or "CP " in l:
                cp = l
            elif "Rte.:" in l or "Rte:" in l:
                remitente = re.sub(r'Rte\.?:?', '', l).strip()
            elif "Venta:" in l or "Venta " in l:
                venta = re.sub(r'Venta:?', '', l).strip()
            elif "Envio:" in l or "Envío:" in l:
                envio = re.sub(r'Env[ií]o:?', '', l).strip()
            elif "Observación:" in l or "Observacion:" in l or "Ref:" in l:
                observacion = l
            elif re.search(r'\d{1,2}/\d{1,2}/\d{4}', l):
                fecha = l
            elif "kg" in l.lower() or "BULTO" in l:
                peso_bulto = l
            elif re.search(r'(\+?54)?\s?11\d{8}', l.replace(" ", "")) or re.search(r'\d{8,11}', l.replace(" ", "")):
                if not telefono:
                    telefono = l
            elif i == 0 and not localidad:
                localidad = l.upper()

        # Búsqueda secundaria de Nombre y Dirección entre las líneas restantes
        lineas_restantes = [l for l in lineas if l not in [localidad, cp, remitente, venta, envio, observacion, fecha, peso_bulto, telefono] 
                           and not any(k in l for k in ["Rte", "Venta", "Envio", "CP:", "Observación"])]
        
        if len(lineas_restantes) > 0:
            destinatario = lineas_restantes[0]
        if len(lineas_restantes) > 1:
            direccion = " ".join(lineas_restantes[1:])

        # --- 3. DISEÑAR NUEVA ETIQUETA 10x15 DESDE CERO ---
        nueva_pag = doc_destino.new_page(width=ANCHO, height=ALTO)
        m = 10  # Margen externo

        # A. QR Grande Arriba (Igual a Vellón)
        if qr_pix:
            tam_qr = 160
            rect_qr = fitz.Rect(m, m, m + tam_qr, m + tam_qr)
            nueva_pag.insert_image(rect_qr, pixmap=qr_pix)

        # B. Encabezado de Localidad (Derecha del QR)
        if localidad:
            rect_loc = fitz.Rect(m + 165, m + 10, ANCHO - m, m + 60)
            nueva_pag.insert_textbox(rect_loc, localidad, fontsize=12, fontname="helv-bold", align=0)

        y_cursor = m + 170
        nueva_pag.draw_line(fitz.Point(m, y_cursor), fitz.Point(ANCHO - m, y_cursor), color=(0, 0, 0), width=1)

        # C. Bloque Destinatario (Centro)
        y_cursor += 8
        nueva_pag.insert_text(fitz.Point(m, y_cursor + 10), "Destinatario", fontsize=8, fontname="helv")
        y_cursor += 22

        if destinatario:
            nueva_pag.insert_text(fitz.Point(m, y_cursor), destinatario.upper(), fontsize=11, fontname="helv-bold")
            y_cursor += 15

        if telefono:
            nueva_pag.insert_text(fitz.Point(m, y_cursor), telefono, fontsize=9, fontname="helv")
            
        if fecha:
            nueva_pag.insert_text(fitz.Point(ANCHO - m - 70, y_cursor), fecha, fontsize=9, fontname="helv")
        y_cursor += 14

        if peso_bulto:
            nueva_pag.insert_text(fitz.Point(m, y_cursor), peso_bulto, fontsize=9, fontname="helv-bold")
            y_cursor += 14

        if direccion:
            rect_dir = fitz.Rect(m, y_cursor, ANCHO - m, y_cursor + 25)
            texto_dir = f"{direccion} {cp}".strip()
            nueva_pag.insert_textbox(rect_dir, texto_dir, fontsize=9.5, fontname="helv-bold")
            y_cursor += 28

        nueva_pag.draw_line(fitz.Point(m, y_cursor), fitz.Point(ANCHO - m, y_cursor), color=(0, 0, 0), width=1)

        # D. Bloque Inferior: Datos a la izquierda, Logo a la derecha
        y_cursor += 8
        
        # Insertar Logo abajo a la derecha
        if logo_pix:
            ancho_l = 75
            alto_l = 40
            rect_l = fitz.Rect(ANCHO - m - ancho_l, ALTO - m - alto_l, ANCHO - m, ALTO - m)
            nueva_pag.insert_image(rect_l, pixmap=logo_pix)

        # Insertar datos de seguimiento a la izquierda
        rect_info_final = fitz.Rect(m, y_cursor, ANCHO - m - 80, ALTO - m)
        lineas_finales = []
        if remitente: lineas_finales.append(f"Rte.: {remitente}")
        if venta: lineas_finales.append(f"Venta: {venta}")
        if envio: lineas_finales.append(f"Envio: {envio}")
        if observacion: lineas_finales.append(observacion)

        nueva_pag.insert_textbox(rect_info_final, "\n".join(lineas_finales), fontsize=8.5, fontname="helv")

    # Guardar PDF resultante
    output_buffer = io.BytesIO()
    doc_destino.save(output_buffer)
    doc_destino.close()
    doc_origen.close()

    st.success("¡Etiqueta rediseñada a 10x15 cm con éxito!")

    st.download_button(
        label="📥 Descargar PDF 10x15",
        data=output_buffer.getvalue(),
        file_name=f"10x15_{archivo_subido.name}",
        mime="application/pdf",
        type="primary"
    )
