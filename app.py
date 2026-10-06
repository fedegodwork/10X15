import streamlit as st
import fitz  # PyMuPDF
import io
import re

st.set_page_config(page_title="Convertidor a 10x15", page_icon="🏷️", layout="centered")

st.title("🏷️ Convertidor de Etiquetas a 10x15")
st.write("Extrae la información del PDF apaisado y genera una etiqueta limpia adaptada a 10x15 cm.")

archivo_subido = st.file_uploader("Seleccionar archivo PDF", type=["pdf"])

if archivo_subido:
    # Dimensiones 10x15 cm en puntos (100x150 mm)
    ANCHO = 100 * 2.83465  # 283.465 pt
    ALTO = 150 * 2.83465   # 425.197 pt

    bytes_pdf = archivo_subido.read()
    doc_origen = fitz.open(stream=bytes_pdf, filetype="pdf")
    doc_destino = fitz.open()

    for pagina in doc_origen:
        # 1. Extraer texto completo de la página original
        texto_pag = pagina.get_text("text")
        lineas = [l.strip() for l in texto_pag.split("\n") if l.strip()]
        
        # 2. Extraer la imagen del QR original
        qr_pixmap = None
        for img in pagina.get_images():
            xref = img[0]
            base_image = doc_origen.extract_image(xref)
            qr_pixmap = fitz.Pixmap(doc_origen, xref)
            if qr_pixmap.alpha:
                qr_pixmap = fitz.Pixmap(fitz.csRGB, qr_pixmap)
            break  # Tomamos la primera imagen (QR)

        # 3. Crear nueva página 10x15 cm
        nueva_pag = doc_destino.new_page(width=ANCHO, height=ALTO)
        
        # Dibuja borde de la etiqueta
        m = 8  # Margen externo
        nueva_pag.draw_rect(fitz.Rect(m, m, ANCHO - m, ALTO - m), color=(0, 0, 0), width=1)

        # A. DIBUJAR EL QR ARRIBA (Centrado y grande)
        if qr_pixmap:
            # Cuadrado para el QR en la parte superior
            tamano_qr = 150
            x_qr = (ANCHO - tamano_qr) / 2
            rect_qr = fitz.Rect(x_qr, m + 10, x_qr + tamano_qr, m + 10 + tamano_qr)
            nueva_pag.insert_image(rect_qr, pixmap=qr_pixmap)
            
        # Línea divisora bajo el QR
        y_cursor = m + 170
        nueva_pag.draw_line(fitz.Point(m, y_cursor), fitz.Point(ANCHO - m, y_cursor), color=(0, 0, 0), width=1)

        # B. DIBUJAR LA INFORMACIÓN EXTRAÍDA
        # Si la información se extrajo, la organizamos en secciones
        y_cursor += 15
        
        # Insertar todo el texto de manera ordenada
        rect_texto = fitz.Rect(m + 10, y_cursor, ANCHO - m - 10, ALTO - m - 10)
        
        # Formateamos el texto extraído
        texto_formateado = "\n".join(lineas)
        
        nueva_pag.insert_textbox(
            rect_texto, 
            texto_formateado, 
            fontsize=9, 
            fontname="helv", 
            align=0
        )

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
