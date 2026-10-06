import streamlit as st
import fitz  # PyMuPDF
import io
import re
import base64

st.set_page_config(page_title="Generador 10x15 Universal", page_icon="🏷️", layout="centered")

st.title("🏷️ Generador de Etiquetas 10x15")
st.write("Adaptador dinámico universal para impresoras térmicas.")

archivo_subido = st.file_uploader("Seleccionar archivo PDF", type=["pdf"])

if archivo_subido:
    ANCHO = 100 * 2.83465  # 100 mm (283.465 pt)
    ALTO = 150 * 2.83465   # 150 mm (425.197 pt)

    bytes_pdf = archivo_subido.read()
    doc_origen = fitz.open(stream=bytes_pdf, filetype="pdf")
    doc_destino = fitz.open()

    for pagina in doc_origen:
        r_pag = pagina.rect

        # 1. IDENTIFICACIÓN DE QR Y LOGO
        qr_pix = None
        logo_pix = None

        try:
            for img_info in pagina.get_images():
                xref = img_info[0]
                pix = fitz.Pixmap(doc_origen, xref)
                if pix.alpha:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                
                aspecto_img = pix.width / float(pix.height)
                if 0.85 <= aspecto_img <= 1.15 and not qr_pix:
                    qr_pix = pix
                elif not logo_pix:
                    logo_pix = pix
        except Exception:
            pass

        # 2. EXTRACCIÓN Y PARSEO DE TEXTO LÍNEA POR LÍNEA
        texto_completo = pagina.get_text("text")
        lineas_raw = [l.strip() for l in texto_completo.split("\n") if l.strip()]

        localidad = ""
        destinatario = ""
        telefono = ""
        peso_bulto = ""
        direccion = ""
        cp = ""
        observacion = ""
        fecha = ""
        remitente = ""
        venta = ""
        envio = ""

        lineas_usadas = set()

        # A. Captura de metadatos exactos (Regex)
        for l in lineas_raw:
            l_lower = l.lower()
            
            if ("cp:" in l_lower or "cp " in l_lower) and not cp:
                m = re.search(r'CP:?\s*(\d+)', l, re.IGNORECASE)
                if m: cp = f"CP: {m.group(1)}"
            
            if "rte" in l_lower and not remitente:
                remitente = re.sub(r'(?i)rte\.?:?', '', l).strip()
                lineas_usadas.add(l)
            elif "venta" in l_lower and not venta:
                venta = re.sub(r'(?i)venta:?', '', l).strip()
                lineas_usadas.add(l)
            elif ("envio" in l_lower or "envío" in l_lower) and not envio:
                envio = re.sub(r'(?i)env[ií]o:?', '', l).strip()
                lineas_usadas.add(l)
            elif "observaci" in l_lower and not observacion:
                obs_clean = re.sub(r'(?i)observaci[oó]n:?', '', l).strip()
                if obs_clean and obs_clean.lower() != "sin información":
                    observacion = obs_clean
                lineas_usadas.add(l)
            elif ("kg" in l_lower or "bulto" in l_lower) and not peso_bulto:
                peso_bulto = l.upper()
                lineas_usadas.add(l)
            elif re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', l) and not fecha:
                fecha = re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', l).group(0)
                lineas_usadas.add(l)
            elif ("+" in l or l.startswith("11") or l.startswith("15")) and len(re.sub(r'\D', '', l)) >= 8 and not telefono:
                telefono = l
                lineas_usadas.add(l)

        # B. Captura de Localidad (Evita basuras corporativas y letras sueltas)
        palabras_ignorar = [
            "goxp", "logística", "logistica", "jyj", "j&j", 
            "destinatario", "remitente", "campos extra", "total a cobrar"
        ]

        for l in lineas_raw:
            if l in lineas_usadas or any(ign in l.lower() for ign in palabras_ignorar):
                continue
            l_clean = l.strip().upper()
            if len(l_clean) <= 2:  # Ignorar letras sueltas como la 'S'
                continue
            if any(z in l_clean for z in ["ESTEBAN ECHEVERRIA", "ECHEVERRIA", "MORON", "MORÓN", "SOLANO", "QUILMES", "LANUS", "AVELLANEDA", "SAN ISIDRO", "CABA", "PALERMO", "MORENO", "MERLO", "SAN MARTIN", "TIGRE"]):
                localidad = l_clean
                lineas_usadas.add(l)
                break

        if not localidad:
            for l in lineas_raw:
                l_clean = l.strip().upper()
                if l not in lineas_usadas and not re.search(r'\d', l) and len(l_clean) > 2:
                    if not any(ign in l.lower() for ign in palabras_ignorar):
                        localidad = l_clean
                        lineas_usadas.add(l)
                        break

        # C. Captura de Destinatario
        for l in lineas_raw:
            if l in lineas_usadas or any(ign in l.lower() for ign in palabras_ignorar):
                continue
            l_clean = l.strip()
            # Un nombre no suele tener números ni barra de fecha
            if not re.search(r'\d', l_clean) and "/" not in l_clean and len(l_clean) > 2:
                destinatario = l_clean.upper()
                lineas_usadas.add(l)
                break

        # D. Captura de Dirección (Todo lo que tenga números/calle que haya quedado libre)
        partes_direccion = []
        for l in lineas_raw:
            if l in lineas_usadas or any(ign in l.lower() for ign in palabras_ignorar):
                continue
            l_lower = l.lower()
