import streamlit as st
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="Convertidor a 10x15", page_icon="🏷️", layout="centered")

st.title("🏷️ Convertidor de Etiquetas a 10x15")
st.write("Adapta y redistribuye la etiqueta para que llene completamente el formato 10x15 cm.")

archivo_subido = st.file_uploader("Seleccionar archivo PDF", type=["pdf"])

if archivo_subido:
    # Dimensiones exactas para hoja 10x15 cm (en puntos: 1 mm = 2.83465 pt)
    ANCHO_DESTINO = 100 * 2.83465  # 283.465 pt
    ALTO_DESTINO = 150 * 2.83465   # 425.197 pt

    bytes_pdf = archivo_subido.read()
    doc_origen = fitz.open(stream=bytes_pdf, filetype="pdf")
    doc_destino = fitz.open()

    for pagina in doc_origen:
        rect_pag = pagina.rect
        
        # 1. Crear nueva página 10x15 cm
        nueva_pag = doc_destino.new_page(width=ANCHO_DESTINO, height=ALTO_DESTINO)
        
        # Margen de seguridad general (3 mm)
        m = 3 * 2.83465
        
        # -------------------------------------------------------------
        # SECCIÓN 1: RECORTE DEL QR (Parte superior)
        # -------------------------------------------------------------
        # El QR en la etiqueta original está ubicado en el primer tercio vertical
        rect_qr_orig = fitz.Rect(
            rect_pag.x0, 
            rect_pag.y0, 
            rect_pag.x1, 
            rect_pag.y0 + (rect_pag.height * 0.35)
        )
        
        # Destino del QR: Ocupa desde arriba hasta casi la mitad de la hoja 10x15
        alto_qr_dest = ALTO_DESTINO * 0.42
        rect_qr_dest = fitz.Rect(m, m, ANCHO_DESTINO - m, m + alto_qr_dest)
        
        # Estirar y meter el QR bien grande arriba
        nueva_pag.show_pdf_page(rect_qr_dest, doc_origen, pagina.number, clip=rect_qr_orig)

        # -------------------------------------------------------------
        # SECCIÓN 2: RECORTE DE DATOS Y LOGO (Parte inferior)
        # -------------------------------------------------------------
        # Los datos en la etiqueta original ocupan desde el 35% hasta el final
        rect_datos_orig = fitz.Rect(
            rect_pag.x0, 
            rect_pag.y0 + (rect_pag.height * 0.33), 
            rect_pag.x1, 
            rect_pag.y1
        )
        
        # Destino de Datos: Ocupa desde donde termina el QR hasta abajo de todo
        rect_datos_dest = fitz.Rect(m, m + alto_qr_dest + 5, ANCHO_DESTINO - m, ALTO_DESTINO - m)
        
        # Ajustar la sección de datos en la mitad inferior
        nueva_pag.show_pdf_page(rect_datos_dest, doc_origen, pagina.number, clip=rect_datos_orig)

    # Guardar resultado
    output_buffer = io.BytesIO()
    doc_destino.save(output_buffer)
    doc_destino.close()
    doc_origen.close()

    st.success("¡Etiqueta reestructurada a 10x15 cm exitosamente!")
    
    st.download_button(
        label="📥 Descargar PDF 10x15",
        data=output_buffer.getvalue(),
        file_name=f"10x15_{archivo_subido.name}",
        mime="application/pdf",
        type="primary"
    )
