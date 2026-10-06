import streamlit as st
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="Convertidor a 10x15", page_icon="🏷️", layout="centered")

st.title("🏷️ Convertidor de Etiquetas a 10x15")
st.write("Ajusta y agranda tus etiquetas para que ocupen la totalidad del formato 10x15 cm.")

archivo_subido = st.file_uploader("Seleccionar archivo PDF", type=["pdf"])

if archivo_subido:
    # Dimensiones 10x15 cm en puntos (1 mm = 2.83465 pt)
    ANCHO_DESTINO = 100 * 2.83465  # 283.465 pt
    ALTO_DESTINO = 150 * 2.83465   # 425.197 pt

    bytes_pdf = archivo_subido.read()
    doc_origen = fitz.open(stream=bytes_pdf, filetype="pdf")
    doc_destino = fitz.open()

    for pagina in doc_origen:
        # Calcular el Bounding Box uniendo los rectángulos de texto e imágenes reales
        rect_contenido = None
        
        # Recorrer bloques de texto
        bloques = pagina.get_text("blocks")
        for b in bloques:
            r = fitz.Rect(b[:4])
            if rect_contenido is None:
                rect_contenido = r
            else:
                rect_contenido |= r
                
        # Recorrer imágenes (como el logo o QR)
        for img in pagina.get_images():
            # Obtener el recuadro donde se dibuja la imagen
            try:
                for img_rect in pagina.get_image_rects(img[0]):
                    if rect_contenido is None:
                        rect_contenido = img_rect
                    else:
                        rect_contenido |= img_rect
            except Exception:
                pass

        # Si no detectó nada específico, usamos el área completa
        if rect_contenido is None or rect_contenido.is_empty:
            rect_contenido = pagina.rect

        # Margen de seguridad de 2 mm para evitar que la impresora corte los bordes
        margen = 2 * 2.83465
        
        nueva_pag = doc_destino.new_page(width=ANCHO_DESTINO, height=ALTO_DESTINO)
        
        ancho_util = ANCHO_DESTINO - (2 * margen)
        alto_util = ALTO_DESTINO - (2 * margen)
        
        # Calcular la escala para ampliar la etiqueta
        escala = min(ancho_util / rect_contenido.width, alto_util / rect_contenido.height)
        
        ancho_final = rect_contenido.width * escala
        alto_final = rect_contenido.height * escala
        
        # Centrado en la hoja
        x0 = (ANCHO_DESTINO - ancho_final) / 2
        y0 = (ALTO_DESTINO - alto_final) / 2
        rect_dest = fitz.Rect(x0, y0, x0 + ancho_final, y0 + alto_final)
        
        # Dibujar la porción recortada y ampliada
        nueva_pag.show_pdf_page(rect_dest, doc_origen, pagina.number, clip=rect_contenido)

    output_buffer = io.BytesIO()
    doc_destino.save(output_buffer)
    doc_destino.close()
    doc_origen.close()

    st.success("¡Etiqueta optimizada a 10x15 cm con éxito!")
    
    st.download_button(
        label="📥 Descargar PDF 10x15",
        data=output_buffer.getvalue(),
        file_name=f"10x15_{archivo_subido.name}",
        mime="application/pdf",
        type="primary"
    )
