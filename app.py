import streamlit as st
import os
import re
import google.generativeai as genai
from PyPDF2 import PdfReader
import base64
from typing import List

# Configuración de la página
st.set_page_config(
    page_title="Editor de Documentos con IA",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Funciones de la API de Gemini ---

def configure_gemini(api_key: str):
    """Configura la API de Google Gemini con la clave proporcionada."""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        return model
    except Exception as e:
        st.error(f"Error al configurar la API de Gemini: {str(e)}")
        return None

# --- Funciones de Procesamiento de Texto y Documentos ---

def extract_text_from_pdf(uploaded_file) -> str:
    """Extrae el texto de un archivo PDF subido."""
    try:
        pdf_reader = PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"Error al leer el archivo PDF: {str(e)}")
        return ""

def split_into_chapters(text: str) -> List[str]:
    """
    Divide el texto en capítulos basándose en patrones comunes o encabezados de Markdown.
    """
    chapter_patterns = [
        r'Capítulo\s+\d+', r'CAPÍTULO\s+\d+', r'Chapter\s+\d+', r'CHAPTER\s+\d+',
        r'\d+\.\s*[A-Z]', r'Parte\s+\d+', r'PARTE\s+\d+', r'Sección\s+\d+', r'SECCIÓN\s+\d+',
        r'^#{1,6}\s+.*$'  # Encabezados de Markdown
    ]
    combined_pattern = '|'.join(f'({pattern})' for pattern in chapter_patterns)
    chapters = re.split(combined_pattern, text, flags=re.MULTILINE)
    chapters = [chapter.strip() for chapter in chapters if chapter.strip()]
    
    if len(chapters) <= 1:
        words = text.split()
        chapters = []
        current_chapter = []
        word_count = 0
        for word in words:
            current_chapter.append(word)
            word_count += 1
            if word_count >= 1000:
                chapters.append(' '.join(current_chapter))
                current_chapter = []
                word_count = 0
        if current_chapter:
            chapters.append(' '.join(current_chapter))
    return chapters

def change_tone_and_style(model, text: str, tone: str, style: str, apply_rules: bool) -> str:
    """Utiliza Gemini para cambiar el tono y estilo de un texto."""
    rules_text = """
    Además, aplica estrictamente las siguientes reglas de ortografía del español:
    1. En títulos, subtítulos y encabezados, usa mayúscula inicial solamente en la primera palabra y en los nombres propios.
    2. Los subtítulos que siguen a dos puntos (:) después de un título no deben llevar mayúscula inicial.
    3. Cuando una frase va entre comillas y termina con punto y coma (;), punto (.) o coma (,), estos signos van fuera de las comillas.
    """ if apply_rules else ""

    prompt = f"""
    Por favor, reescribe el siguiente texto cambiando el tono a "{tone}" y el estilo a "{style}".
    Mantén el significado y la información original, pero ajusta la forma en que se expresa.
    Si el texto contiene formato como encabezados de Markdown (ej: # Título), presérvalos.
    {rules_text}
    
    Texto original:
    {text}
    
    Texto reescrito:
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error al cambiar el tono y estilo: {str(e)}")
        return text

def correct_style(model, text: str, apply_rules: bool) -> str:
    """Utiliza Gemini para realizar correcciones de estilo a un texto."""
    rules_text = """
    Presta especial atención a las siguientes reglas de ortografía del español:
    1. En títulos, subtítulos y encabezados, usa mayúscula inicial solamente en la primera palabra y en los nombres propios.
    2. Los subtítulos que siguen a dos puntos (:) después de un título no deben llevar mayúscula inicial.
    3. Cuando una frase va entre comillas y termina con punto y coma (;), punto (.) o coma (,), estos signos van fuera de las comillas.
    """ if apply_rules else ""

    prompt = f"""
    Por favor, realiza correcciones de estilo al siguiente texto. Mejora la claridad, 
    coherencia, gramática y puntuación, sin cambiar el significado ni el tono general.
    Si el texto contiene formato como encabezados de Markdown, presérvalos.
    {rules_text}
    
    Texto original:
    {text}
    
    Texto corregido:
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error al realizar correcciones de estilo: {str(e)}")
        return text

def apply_spanish_orthography_rules(model, text: str) -> str:
    """Aplica reglas ortográficas específicas del español de forma explícita."""
    prompt = f"""
    Revisa y corrige el siguiente texto para que cumpla estrictamente con estas reglas de ortografía del español:
    
    1. **Capitalización de Títulos**: En títulos, subtítulos y encabezados (como los que empiezan con # en Markdown), solo la primera palabra y los nombres propios deben llevar mayúscula inicial.
       - Ejemplo incorrecto: `# Este Es Un Título`
       - Ejemplo correcto: `# Este es un título`
    
    2. **Subtítulos después de Dos Puntos**: Si un subtítulo sigue a un título separado por dos puntos (:), el subtítulo no debe llevar mayúscula inicial.
       - Ejemplo incorrecto: `Título del Libro: Un Subtítulo Importante`
       - Ejemplo correcto: `Título del libro: un subtítulo importante`
    
    3. **Puntuación y Comillas**: Los signos de puntuación como punto (.), coma (,) y punto y coma (;) siempre se colocan fuera de las comillas de cierre.
       - Ejemplo incorrecto: `El autor dijo: "Esto es una prueba".`
       - Ejemplo correcto: `El autor dijo: "Esto es una prueba".`
    
    Aplica estas reglas sobre el siguiente texto y devuelve solo el texto corregido, sin explicaciones adicionales.
    
    Texto a corregir:
    {text}
    
    Texto corregido:
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Error al aplicar las reglas ortográficas: {str(e)}")
        return text

# --- Funciones de Utilidad ---

def create_download_file(text: str, filename: str) -> str:
    """Crea un enlace de descarga para el texto procesado."""
    b64 = base64.b64encode(text.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">Descargar archivo editado</a>'
    return href

# --- Interfaz Principal de la Aplicación ---

def main():
    st.title("📝 Editor de Documentos con IA")
    st.markdown("Esta aplicación utiliza Google Gemini para editar documentos (PDF, TXT, MD), cambiar el tono y estilo, y realizar correcciones de estilo y ortográficas.")
    
    # Sidebar para configuración
    st.sidebar.header("Configuración")
    api_key = st.sidebar.text_input("Introduce tu API Key de Google Gemini:", type="password")
    
    # Opciones de tono y estilo
    tone_options = ["Formal", "Informal", "Profesional", "Amigable", "Académico", "Creativo", "Técnico", "Persuasivo"]
    selected_tone = st.sidebar.selectbox("Selecciona el tono deseado:", tone_options)
    style_options = ["Conciso", "Detallado", "Directo", "Elegante", "Sencillo", "Técnico", "Narrativo", "Expositivo"]
    selected_style = st.sidebar.selectbox("Selecciona el estilo deseado:", style_options)
    
    # Opciones de procesamiento
    process_chapters = st.sidebar.checkbox("Procesar capítulo por capítulo", value=True)
    apply_corrections = st.sidebar.checkbox("Aplicar correcciones de estilo", value=True)
    apply_spanish_rules = st.sidebar.checkbox(
        "Aplicar reglas ortográficas del español", 
        value=True,
        help="Aplica reglas específicas de capitalización y puntuación en español."
    )
    
    # Área principal para subir y procesar documentos
    st.header("Sube tu documento")
    uploaded_file = st.file_uploader(
        "Sube un archivo PDF, TXT o Markdown (MD):", 
        type=["pdf", "txt", "md"],
        help="Sube el documento que deseas editar."
    )
    
    if uploaded_file is not None:
        file_details = {
            "Nombre de archivo": uploaded_file.name,
            "Tipo de archivo": uploaded_file.type,
            "Tamaño": f"{uploaded_file.size / 1024:.2f} KB"
        }
        st.json(file_details)
        
        text = ""
        if uploaded_file.name.endswith('.pdf'):
            text = extract_text_from_pdf(uploaded_file)
        elif uploaded_file.name.endswith(('.txt', '.md')):
            try:
                text = uploaded_file.read().decode("utf-8")
            except UnicodeDecodeError:
                st.error("No se pudo decodificar el archivo. Por favor, asegúrate de que esté en formato UTF-8.")
                text = None

        if text:
            st.success("Documento cargado correctamente.")
            if process_chapters:
                chapters = split_into_chapters(text)
                st.info(f"Se han detectado {len(chapters)} capítulos/secciones en el documento.")
            else:
                chapters = [text]
                st.info("El documento se procesará como un solo bloque.")
            
            if st.button("Procesar documento") and api_key:
                with st.spinner("Procesando documento..."):
                    model = configure_gemini(api_key)
                    if model:
                        processed_chapters = []
                        progress_bar = st.progress(0)
                        
                        for i, chapter in enumerate(chapters):
                            # 1. Cambiar tono y estilo
                            edited_chapter = change_tone_and_style(
                                model, chapter, selected_tone, selected_style, apply_spanish_rules
                            )
                            
                            # 2. Aplicar correcciones de estilo generales
                            if apply_corrections:
                                edited_chapter = correct_style(model, edited_chapter, apply_spanish_rules)
                            
                            # 3. Aplicar reglas ortográficas del español (si no se aplicaron antes)
                            # Este paso es una pasada final para asegurar el cumplimiento estricto de las reglas.
                            if apply_spanish_rules:
                                edited_chapter = apply_spanish_orthography_rules(model, edited_chapter)
                            
                            processed_chapters.append(edited_chapter)
                            progress = (i + 1) / len(chapters)
                            progress_bar.progress(progress)
                        
                        processed_text = "\n\n".join(processed_chapters)
                        st.success("Procesamiento completado.")
                        
                        tab1, tab2 = st.tabs(["Original", "Editado"])
                        with tab1:
                            st.subheader("Documento Original")
                            st.text_area("", text, height=500, key="original_text")
                        
                        with tab2:
                            st.subheader("Documento Editado")
                            st.text_area("", processed_text, height=500, key="edited_text")
                            original_name = os.path.splitext(uploaded_file.name)[0]
                            filename = f"editado_{original_name}.txt"
                            st.markdown(create_download_file(processed_text, filename), unsafe_allow_html=True)
            elif not api_key:
                st.warning("Por favor, introduce tu API Key de Google Gemini para procesar el documento.")

# --- Información Adicional en la Sidebar ---
st.sidebar.markdown("---")
st.sidebar.markdown("### Acerca de esta aplicación")
st.sidebar.info(
    "Esta aplicación utiliza la API de Google Gemini para editar documentos. "
    "Puedes cambiar el tono y estilo de tu texto, así como aplicar correcciones "
    "de estilo y reglas ortográficas específicas del español."
)

st.sidebar.markdown("### Instrucciones de uso")
st.sidebar.markdown(
    """
    1. Introduce tu API Key de Google Gemini.
    2. Selecciona el tono, estilo y las opciones de corrección.
    3. Sube tu documento (PDF, TXT o MD).
    4. Haz clic en "Procesar documento".
    5. Revisa el resultado y descarga el archivo editado.
    """
)

# Ejecutar la aplicación principal
if __name__ == "__main__":
    main()
