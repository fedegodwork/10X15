import streamlit as st
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="Convertidor Universal 10x15", page_icon="🏷️", layout="centered")

st.title("🏷️ Convertidor de Etiquetas a 10x15 (Universal)")
st.write("Sube cualquier PDF de etiqueta apaisada para transformarlo automáticamente al formato vertical 10x15 cm.")

archivo_subido = st.file_uploader("Seleccionar archivo PDF", type=["pdf"])

if archivo_subido:
    # Dimensiones exactas de hoja 10x15 cm (100x150 mm en puntos)
    ANCHO_DESTINO = 100 * 2.83465  # 283.465 pt
    ALTO_DESTINO = 150 * 2.83465   # 425.197 pt

    bytes_pdf = archivo_subido.read()
    doc_origen = fitz.open(stream=bytes_pdf, filetype="pdf")
    doc_destino = fitz.open()

    for pagina in doc_origen:
        rect_pag = pagina.rect
        
        # Detectar el recuadro que contiene elementos visibles (para ignorar bordes blancos vacíos)
        bloques = pagina.get_text("blocks")
        rect_contenido = None
        for b in bloques:
            r = fitz.Rect(b[:4])
            rect_contenido = r if rect_contenido is None else (rect_contenido | r)
            
        for img in pagina.get_images():
            try:
                for img_rect in pagina.get_image_rects(img[0]):
                    rect_contenido = img_rect if rect_contenido is None else (rect_contenido | img_rect)
            except Exception:
                pass

        if rect_contenido is None or rect_contenido.is_empty:
            rect_contenido = rect_pag

        # Margen de seguridad externo (3 mm)
        m = 3 * 2.83465
        
        # Crear nueva página 10x15 cm
        nueva_pag = doc_destino.new_page(width=ANCHO_DESTINO, height=ALTO_DESTINO)

        # -------------------------------------------------------------
        # 1. BLOQUE QR (Toma el tercio izquierdo de la etiqueta original)
        # -------------------------------------------------------------
        corte_x = rect_contenido.x0 + (rect_contenido.width * 0.32)
        
        rect_qr_orig = fitz.Rect(
            rect_contenido.x0, 
            rect_contenido.y0, 
            corte_x, 
            rect_contenido.y1
        )
        
        # Destino: Mitad superior de la hoja 10x15
        alto_qr_dest = ALTO_DESTINO * 0.44
        rect_qr_dest = fitz.Rect(m, m, ANCHO_DESTINO - m, m + alto_qr_dest)
        
        # Insertar sección del QR escalada al máximo arriba
        nueva_pag.show_pdf_page(rect_qr_dest, doc_origen, pagina.number, clip=rect_qr_orig)

        # -------------------------------------------------------------
        # 2. BLOQUE DATOS Y LOGO (Toma los dos tercios derechos)
        # -------------------------------------------------------------
        rect_datos_orig = fitz.Rect(
            corte_x, 
            rect_contenido.y0, 
            rect_contenido.x1, 
            rect_contenido.y1
        )
        
        # Destino: Mitad inferior de la hoja 10x15
        rect_datos_dest = fitz.Rect(m, m + alto_qr_dest + 8, ANCHO_DESTINO - m, ALTO_DESTINO - m)
        
        # Insertar sección de Datos y Logo escalada en la parte inferior
        nueva_pag.show_pdf_page(rect_datos_dest, doc_origen, pagina.number, clip=rect_datos_orig)

    # Guardar archivo en memoria
    output_buffer = io.BytesIO()
    doc_destino.save(output_buffer)
    doc_destino.close()
    doc_origen.close()

    st.success("¡Etiqueta convertida exitosamente a 10x15 cm!")

    st.download_button(
        label="📥 Descargar PDF 10x15",
        data=output_buffer.getvalue(),
        file_name=f"10x15_{archivo_subido.name}",
        mime="application/pdf",
        type="primary"
    )
