import streamlit as st
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="Convertidor a 10x15", page_icon="🏷️", layout="centered")

st.title("🏷️ Convertidor de Etiquetas a 10x15")
st.write("Subí tu PDF original y descargalo adaptado al formato térmico 10x15 cm.")

archivo_subido = st.file_uploader("Seleccionar archivo PDF", type=["pdf"])

if archivo_subido:
    # Medidas 10x15 cm en puntos tipográficos (1 mm = 2.83465 pt)
    ANCHO_DESTINO = 100 * 2.83465  # 283.465 pt
    ALTO_DESTINO = 150 * 2.83465   # 425.197 pt

    # Leer el PDF subido
    bytes_pdf = archivo_subido.read()
    doc_origen = fitz.open(stream=bytes_pdf, filetype="pdf")
    doc_destino = fitz.open()

    for pagina in doc_origen:
        nueva_pag = doc_destino.new_page(width=ANCHO_DESTINO, height=ALTO_DESTINO)
        rect_orig = pagina.rect
        
        # Proporción de escala y centrado sin deformar
        escala = min(ANCHO_DESTINO / rect_orig.width, ALTO_DESTINO / rect_orig.height)
        ancho_final = rect_orig.width * escala
        alto_final = rect_orig.height * escala
        
        x0 = (ANCHO_DESTINO - ancho_final) / 2
        y0 = (ALTO_DESTINO - alto_final) / 2
        
        rect_dest = fitz.Rect(x0, y0, x0 + ancho_final, y0 + alto_final)
        nueva_pag.show_pdf_page(rect_dest, doc_origen, pagina.number)

    # Generar el archivo resultante en memoria
    output_buffer = io.BytesIO()
    doc_destino.save(output_buffer)
    doc_destino.close()
    doc_origen.close()

    st.success("¡Etiqueta(s) convertida(s) exitosamente!")
    
    st.download_button(
        label="📥 Descargar PDF 10x15",
        data=output_buffer.getvalue(),
        file_name=f"etiquetas_10x15_{archivo_subido.name}",
        mime="application/pdf",
        type="primary"
    )