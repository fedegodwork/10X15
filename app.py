import streamlit as st
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="Convertidor a 10x15", page_icon="🏷️", layout="centered")

st.title("🏷️ Convertidor de Etiquetas a 10x15")
st.write("Redistribuye el QR arriba y los datos abajo para adaptar la etiqueta apaisada al formato 10x15 cm.")

archivo_subido = st.file_uploader("Seleccionar archivo PDF", type=["pdf"])

if archivo_subido:
    # Dimensiones exactas de hoja 10x15 cm (en puntos: 1 mm = 2.83465 pt)
    ANCHO_DESTINO = 100 * 2.83465  # 283.465 pt
    ALTO_DESTINO = 150 * 2.83465   # 425.197 pt

    bytes_pdf = archivo_subido.read()
    doc_origen = fitz.open(stream=bytes_pdf, filetype="pdf")
    doc_destino = fitz.open()

    for pagina in doc_origen:
        rect_pag = pagina.rect
        nueva_pag = doc_destino.new_page(width=ANCHO_DESTINO, height=ALTO_DESTINO)
        
        # Margen de seguridad (3 mm)
        m = 3 * 2.83465
        
        # 1. RECORTE DEL QR (Lado izquierdo de la etiqueta original apaisada)
        # Tomamos aproximadamente el primer 30% del ancho
        rect_qr_orig = fitz.Rect(
            rect_pag.x0, 
            rect_pag.y0, 
            rect_pag.x0 + (rect_pag.width * 0.30), 
            rect_pag.y1
        )
        
        # Destino: Mitad superior de la hoja 10x15
        alto_qr_dest = ALTO_DESTINO * 0.45
        rect_qr_dest = fitz.Rect(m, m, ANCHO_DESTINO - m, m + alto_qr_dest)
        
        nueva_pag.show_pdf_page(rect_qr_dest, doc_origen, pagina.number, clip=rect_qr_orig)

        # 2. RECORTE DE DATOS Y LOGO (Lado derecho de la etiqueta original apaisada)
        # Tomamos desde el 30% del ancho hasta el final
        rect_datos_orig = fitz.Rect(
            rect_pag.x0 + (rect_pag.width * 0.28), 
            rect_pag.y0, 
            rect_pag.x1, 
            rect_pag.y1
        )
        
        # Destino: Mitad inferior de la hoja 10x15
        rect_datos_dest = fitz.Rect(m, m + alto_qr_dest + 5, ANCHO_DESTINO - m, ALTO_DESTINO - m)
        
        nueva_pag.show_pdf_page(rect_datos_dest, doc_origen, pagina.number, clip=rect_datos_orig)

    # Guardar archivo en memoria
    output_buffer = io.BytesIO()
    doc_destino.save(output_buffer)
    doc_destino.close()
    doc_origen.close()

    st.success("¡Etiqueta adaptada al formato 10x15 cm exitosamente!")
    
    st.download_button(
        label="📥 Descargar PDF 10x15",
        data=output_buffer.getvalue(),
        file_name=f"10x15_{archivo_subido.name}",
        mime="application/pdf",
        type="primary"
    )
