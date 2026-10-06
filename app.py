import streamlit as st
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="Convertidor a 10x15", page_icon="🏷️", layout="centered")

st.title("🏷️ Convertidor de Etiquetas a 10x15")
st.write("Ajusta y agranda tus etiquetas para que ocupen la totalidad del formato 10x15 cm.")

archivo_subido = st.file_uploader("Seleccionar archivo PDF", type=["pdf"])

if archivo_subido:
    # Ancho y alto de hoja 10x15 cm en puntos (1 mm = 2.83465 pt)
    ANCHO_DESTINO = 100 * 2.83465  # 283.465 pt
    ALTO_DESTINO = 150 * 2.83465   # 425.197 pt

    bytes_pdf = archivo_subido.read()
    doc_origen = fitz.open(stream=bytes_pdf, filetype="pdf")
    doc_destino = fitz.open()

    for pagina in doc_origen:
        # Detectar el área donde realmente hay contenido (ignorando los márgenes en blanco)
        rect_contenido = pagina.get_bounding_box()
        
        if not rect_contenido or rect_contenido.is_empty:
            rect_contenido = pagina.rect

        # Dejar solo un pequeño margen de seguridad de 2 mm para que la impresora no corte bordes
        margen = 2 * 2.83465
        
        # Crear la nueva página de 10x15 cm
        nueva_pag = doc_destino.new_page(width=ANCHO_DESTINO, height=ALTO_DESTINO)
        
        # Área útil dentro de la nueva hoja de 10x15 (restando el margen de seguridad)
        ancho_util = ANCHO_DESTINO - (2 * margen)
        alto_util = ALTO_DESTINO - (2 * margen)
        
        # Calcular el factor de escala para agrandar la etiqueta recortada al máximo
        escala = min(ancho_util / rect_contenido.width, alto_util / rect_contenido.height)
        
        ancho_final = rect_contenido.width * escala
        alto_final = rect_contenido.height * escala
        
        # Centrar la etiqueta agrandada en la hoja 10x15
        x0 = (ANCHO_DESTINO - ancho_final) / 2
        y0 = (ALTO_DESTINO - alto_final) / 2
        rect_dest = fitz.Rect(x0, y0, x0 + ancho_final, y0 + alto_final)
        
        # Insertar SOLO la porción recortada y agrandada
        nueva_pag.show_pdf_page(rect_dest, doc_origen, pagina.number, clip=rect_contenido)

    output_buffer = io.BytesIO()
    doc_destino.save(output_buffer)
    doc_destino.close()
    doc_origen.close()

    st.success("¡Etiqueta optimizada al tamaño 10x15 cm!")
    
    st.download_button(
        label="📥 Descargar PDF 10x15",
        data=output_buffer.getvalue(),
        file_name=f"10x15_{archivo_subido.name}",
        mime="application/pdf",
        type="primary"
    )
