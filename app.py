import streamlit as st
import fitz  # PyMuPDF
import io

st.set_page_config(page_title="Generador 10x15 Universal", page_icon="🏷️", layout="centered")

st.title("🏷️ Generador de Etiquetas 10x15")
st.write("Transformación vectorial directa sin pérdida de datos.")

archivo_subido = st.file_uploader("Seleccionar archivo PDF", type=["pdf"])

if archivo_subido:
    # Hoja 10x15 cm (100x150 mm en puntos)
    ANCHO_DEST = 100 * 2.83465  # 283.465 pt
    ALTO_DEST = 150 * 2.83465   # 425.197 pt

    bytes_pdf = archivo_subido.read()
    doc_origen = fitz.open(stream=bytes_pdf, filetype="pdf")
    doc_destino = fitz.open()

    for pagina in doc_origen:
        r_orig = pagina.rect
        w = r_orig.width
        h = r_orig.height

        nueva_pag = doc_destino.new_page(width=ANCHO_DEST, height=ALTO_DEST)
        m = 8  # Margen externo

        # -------------------------------------------------------------
        # 1. BLOQUE QR (Primer 28% del ancho) -> Arriba Izquierda
        # -------------------------------------------------------------
        rect_qr_orig = fitz.Rect(r_orig.x0, r_orig.y0, r_orig.x0 + (w * 0.28), r_orig.y1)
        tam_qr = 135
        rect_qr_dest = fitz.Rect(m, m, m + tam_qr, m + tam_qr)
        nueva_pag.show_pdf_page(rect_qr_dest, doc_origen, pagina.number, clip=rect_qr_orig)

        # -------------------------------------------------------------
        # 2. BLOQUE GESTIÓN Y LOGO (Último 35% del ancho) -> Arriba Derecha
        # -------------------------------------------------------------
        rect_gest_orig = fitz.Rect(r_orig.x0 + (w * 0.65), r_orig.y0, r_orig.x1, r_orig.y1)
        x_der = m + tam_qr + 8
        rect_gest_dest = fitz.Rect(x_der, m, ANCHO_DEST - m, m + tam_qr)
        nueva_pag.show_pdf_page(rect_gest_dest, doc_origen, pagina.number, clip=rect_gest_orig)

        # Línea divisora bajo el QR
        y_div1 = m + tam_qr + 6
        nueva_pag.draw_line(fitz.Point(m, y_div1), fitz.Point(ANCHO_DEST - m, y_div1), color=(0, 0, 0), width=1)

        # -------------------------------------------------------------
        # 3. BLOQUE DESTINATARIO COMPLETO (Columna Central) -> Centro 10x15
        # -------------------------------------------------------------
        # Título "Destinatario"
        y_dest = y_div1 + 12
        nueva_pag.insert_text(fitz.Point(m, y_dest), "Destinatario", fontsize=8, fontname="helv")

        # Tomamos toda la columna central (30% al 65% del ancho original)
        rect_cliente_orig = fitz.Rect(
            r_orig.x0 + (w * 0.28), 
            r_orig.y0, 
            r_orig.x0 + (w * 0.65), 
            r_orig.y1
        )

        # Se estampa en el centro del 10x15 aprovechando todo el ancho
        alto_cliente_dest = 180
        rect_cliente_dest = fitz.Rect(m, y_dest + 5, ANCHO_DEST - m, y_dest + 5 + alto_cliente_dest)
        nueva_pag.show_pdf_page(rect_cliente_dest, doc_origen, pagina.number, clip=rect_cliente_orig)

    output_buffer = io.BytesIO()
    doc_destino.save(output_buffer)
    doc_destino.close()
    doc_origen.close()

    st.success("¡Etiqueta reestructurada a 10x15 cm sin omisiones de datos!")

    st.download_button(
        label="📥 Descargar PDF 10x15",
        data=output_buffer.getvalue(),
        file_name=f"10x15_{archivo_subido.name}",
        mime="application/pdf",
        type="primary"
    )
