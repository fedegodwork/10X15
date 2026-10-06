import streamlit as st
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="Convertidor a 10x15", page_icon="🏷️", layout="centered")

st.title("🏷️ Convertidor de Etiquetas a 10x15")
st.write("Rota y agranda tu etiqueta apaisada para que llene la hoja térmica de 10x15 cm.")

archivo_subido = st.file_uploader("Seleccionar archivo PDF", type=["pdf"])

if archivo_subido:
    # Hoja vertical 10x15 cm (en puntos: 1 mm = 2.83465 pt)
    ANCHO_DESTINO = 100 * 2.83465  # 283.465 pt
    ALTO_DESTINO = 150 * 2.83465   # 425.197 pt

    bytes_pdf = archivo_subido.read()
    doc_origen = fitz.open(stream=bytes_pdf, filetype="pdf")
    doc_destino = fitz.open()

    for pagina in doc_origen:
        # Detectar el recuadro real de contenido de la etiqueta original
        rect_contenido = None
        
        # Recorrer bloques de texto
        bloques = pagina.get_text("blocks")
        for b in bloques:
            r = fitz.Rect(b[:4])
            if rect_contenido is None:
                rect_contenido = r
            else:
                rect_contenido |= r
                
        # Recorrer imágenes (como QR y logo)
        for img in pagina.get_images():
            try:
                for img_rect in pagina.get_image_rects(img[0]):
                    if rect_contenido is None:
                        rect_contenido = img_rect
                    else:
                        rect_contenido |= img_rect
            except Exception:
                pass

        if rect_contenido is None or rect_contenido.is_empty:
            rect_contenido = pagina.rect

        # Al rotar 90 grados la etiqueta apaisada, el ancho original pasa a ser el alto y viceversa
        ancho_rotado = rect_contenido.height
        alto_rotado = rect_contenido.width

        # Margen de seguridad de 3 mm
        margen = 3 * 2.83465
        ancho_util = ANCHO_DESTINO - (2 * margen)
        alto_util = ALTO_DESTINO - (2 * margen)

        # Calcular factor de escala para llenar el 10x15
        escala = min(ancho_util / ancho_rotado, alto_util / alto_rotado)

        ancho_final = ancho_rotado * escala
        alto_final = alto_rotado * escala

        # Centrar en la nueva página
        x0 = (ANCHO_DESTINO - ancho_final) / 2
        y0 = (ALTO_DESTINO - alto_final) / 2
        rect_dest = fitz.Rect(x0, y0, x0 + ancho_final, y0 + alto_final)

        # Crear página 10x15 vertical
        nueva_pag = doc_destino.new_page(width=ANCHO_DESTINO, height=ALTO_DESTINO)

        # Insertar el contenido ROTADO 90 grados
        # rotate=90 o rotate=270 dependiendo del sentido deseado
        nueva_pag.show_pdf_page(
            rect_dest, 
            doc_origen, 
            pagina.number, 
            clip=rect_contenido,
            rotate=90
        )

    output_buffer = io.BytesIO()
    doc_destino.save(output_buffer)
    doc_destino.close()
    doc_origen.close()

    st.success("¡Etiqueta girada y adaptada a 10x15 cm!")

    st.download_button(
        label="📥 Descargar PDF 10x15",
        data=output_buffer.getvalue(),
        file_name=f"10x15_{archivo_subido.name}",
        mime="application/pdf",
        type="primary"
    )
