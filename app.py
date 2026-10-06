import streamlit as st
import fitz  # PyMuPDF
import io
import re
from reportlab.lib.pagesizes import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="Generador 10x15 Profesional", page_icon="🏷️", layout="centered")

st.title("🏷️ Generador de Etiquetas 10x15")
st.write("Rediseño dinámico de precisión basado en la etiqueta modelo.")

archivo_subido = st.file_uploader("Seleccionar archivo PDF", type=["pdf"])

def procesar_etiqueta(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pagina = doc[0]
    
    # --- 1. EXTRAER IMÁGENES (QR Y LOGO) ---
    imagenes = []
    for img_info in pagina.get_images():
        xref = img_info[0]
        pix = fitz.Pixmap(doc, xref)
        if pix.alpha:
            pix = fitz.Pixmap(fitz.csRGB, pix)
        imagenes.append(pix.tobytes("png"))
    
    qr_png = imagenes[0] if len(imagenes) > 0 else None
    logo_png = imagenes[1] if len(imagenes) > 1 else None

    # --- 2. EXTRAER PALABRAS CON COORDENADAS ---
    palabras = pagina.get_text("words") # (x0, y0, x1, y1, word, block_no, line_no, word_no)
    
    localidad = ""
    destinatario = ""
    telefono = ""
    peso = ""
    direccion = ""
    cp = ""
    observacion = "Sin información"
    fecha = ""
    remitente = ""
    venta = ""
    envio = ""

    texto_completo = pagina.get_text("text")
    lineas = [l.strip() for l in texto_completo.split("\n") if l.strip()]

    # Parseo preciso por regex y contexto
    for i, l in enumerate(lineas):
        l_lower = l.lower()
        if "cp:" in l_lower or "cp " in l_lower:
            m = re.search(r'CP:?\s*(\d+)', l, re.IGNORECASE)
            if m: cp = f"CP: {m.group(1)}"
        if "rte" in l_lower:
            remitente = re.sub(r'(?i)rte\.?:?', '', l).strip()
        elif "venta" in l_lower:
            venta = re.sub(r'(?i)venta:?', '', l).strip()
        elif "envio" in l_lower or "envío" in l_lower:
            envio = re.sub(r'(?i)env[ií]o:?', '', l).strip()
        elif "observaci" in l_lower:
            observacion = l
        elif "kg" in l_lower:
            peso = l
        elif re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', l):
            fecha = l
        elif "+" in l or l.startswith("11") or l.startswith("15"):
            telefono = l

    # Extraer Localidad (Top-Left)
    words_top_left = [w[4] for w in palabras if w[0] < pagina.rect.width * 0.3 and w[1] < pagina.rect.height * 0.25]
    if words_top_left:
        localidad = " ".join(words_top_left).upper()

    # Extraer Destinatario y Dirección buscando la columna central
    words_center = [w for w in palabras if pagina.rect.width * 0.25 <= w[0] <= pagina.rect.width * 0.65]
    
    # Agrupar por líneas según coordenada Y
    lineas_center = {}
    for w in words_center:
        y_approx = round(w[1] / 8) * 8
        lineas_center.setdefault(y_approx, []).append(w)

    lineas_ordenadas = [
        " ".join([w[4] for w in sorted(lineas_center[k], key=lambda x: x[0])])
        for k in sorted(lineas_center.keys())
    ]

    # Filtrar líneas descartando teléfono, peso, localidad
    filtradas = []
    for l in lineas_ordenadas:
        if any(x in l.lower() for x in ["kg", "+54", "observaci", "cp:"]) or l.upper() == localidad:
            continue
        filtradas.append(l)

    if len(filtradas) > 0:
        destinatario = filtradas[0].upper()
    if len(filtradas) > 1:
        direccion = " ".join(filtradas[1:])

    # --- 3. CONSTRUIR PDF EN 10x15 CM CON REPORTLAB ---
    buffer = io.BytesIO()
    
    # Ancho: 100mm, Alto: 150mm
    doc_rl = SimpleDocTemplate(
        buffer,
        pagesize=(100 * mm, 150 * mm),
        rightMargin=4 * mm,
        leftMargin=4 * mm,
        topMargin=4 * mm,
        bottomMargin=4 * mm
    )

    styles = getSampleStyleSheet()
    
    style_localidad = ParagraphStyle('Loc', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=14, leading=16, alignment=1)
    style_dest_title = ParagraphStyle('DestT', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor("#444444"))
    style_dest_name = ParagraphStyle('DestN', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=14)
    style_info = ParagraphStyle('Info', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=11)
    style_dir = ParagraphStyle('Dir', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=12)
    style_obs = ParagraphStyle('Obs', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10)

    story = []

    # --- HEADER: QR a la Izquierda | Logo y Localidad a la Derecha ---
    from reportlab.platypus import Image as RLImage
    
    img_qr = RLImage(io.BytesIO(qr_png), width=42*mm, height=42*mm) if qr_png else Paragraph("", style_info)
    
    header_right = []
    if logo_png:
        header_right.append(RLImage(io.BytesIO(logo_png), width=40*mm, height=16*mm))
        header_right.append(Spacer(1, 2*mm))
    if localidad:
        header_right.append(Paragraph(f"<b>{localidad}</b>", style_localidad))

    t_header = Table([[img_qr, header_right]], colWidths=[44*mm, 48*mm])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 3*mm))

    # --- BLOQUE DESTINATARIO ---
    story.append(Paragraph("Destinatario", style_dest_title))
    story.append(Spacer(1, 1*mm))
    if destinatario:
        story.append(Paragraph(destinatario, style_dest_name))
        story.append(Spacer(1, 1*mm))

    # Tabla Teléfono | Fecha + Peso
    txt_tel = telefono if telefono else ""
    txt_der = f"{fecha} &nbsp;&nbsp;&nbsp;&nbsp; <b>{peso}</b>" if fecha or peso else ""
    
    t_mid = Table([[Paragraph(txt_tel, style_info), Paragraph(txt_der, style_info)]], colWidths=[46*mm, 46*mm])
    t_mid.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t_mid)
    story.append(Spacer(1, 3*mm))

    # --- SECCIÓN DIRECCIÓN Y SEGUIMIENTO ---
    datos_envio = []
    if remitente: datos_envio.append(f"Rte.: {remitente}")
    if venta: datos_envio.append(f"Venta: {venta}")
    if envio: datos_envio.append(f"Envio: {envio}")
    
    str_envio = "<br/>".join(datos_envio)
    
    t_envio = Table([[Paragraph(str_envio, style_info)]], colWidths=[92*mm])
    t_envio.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t_envio)
    story.append(Spacer(1, 3*mm))

    if direccion:
        txt_completo_dir = f"{direccion} {cp}".strip()
        story.append(Paragraph(txt_completo_dir, style_dir))
        story.append(Spacer(1, 3*mm))

    if observacion:
        story.append(Paragraph(f"<b>Observación:</b> {observacion}", style_obs))

    # Borde exterior
    def draw_background(canvas, doc):
        canvas.saveState()
        canvas.setLineWidth(1)
        canvas.setStrokeColor(colors.black)
        canvas.rect(3*mm, 3*mm, 94*mm, 144*mm)
        canvas.restoreState()

    doc_rl.build(story, onFirstPage=draw_background)
    return buffer.getvalue()

if archivo_subido:
    try:
        pdf_res = procesar_etiqueta(archivo_subido.read())
        st.success("¡Etiqueta adaptada con precisión al formato 10x15 cm!")
        st.download_button(
            label="📥 Descargar PDF 10x15",
            data=pdf_res,
            file_name=f"10x15_{archivo_subido.name}",
            mime="application/pdf",
            type="primary"
        )
    except Exception as e:
        st.error(f"Error procesando la etiqueta: {e}")
