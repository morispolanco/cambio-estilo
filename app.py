import streamlit as st
import os
import re
from google import genai
from google.genai import types
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
    """Configura el cliente de la API de Google Gemini."""
    if not api_key:
        st.error("La API Key no puede estar vacía.")
        return None
    try:
        os.environ["GEMINI_API_KEY"] = api_key
        client = genai.Client()
        return client
    except Exception as e:
        st.error(f"Error al configurar el cliente de Gemini: {str(e)}")
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
    """Divide el texto en capítulos basándose en patrones comunes o encabezados de Markdown."""
    chapter_patterns = [
        r'Capítulo\s+\d+', r'CAPÍTULO\s+\d+', r'Chapter\s+\d+', r'CHAPTER\s+\d+',
        r'\d+\.\s*[A-Z]', r'Parte\s+\d+', r'PARTE\s+\d+', r'Sección\s+\d+', r'SECCIÓN\s+\d+',
        r'^#{1,6}\s+.*$'
    ]
    combined_pattern = '|'.join(f'({pattern})' for pattern in chapter_patterns)
    chapters = re.split(combined_pattern, text, flags=re.MULTILINE)
    chapters = [chapter.strip() for chapter in chapters if chapter]
    
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

# --- Funciones de Edición con IA (CORREGIDAS) ---

def change_style_based_on_description(client: genai.Client, text: str, style_description: str, apply_rules: bool, enable_search: bool) -> str:
    """Utiliza Gemini con capacidades avanzadas para cambiar el estilo."""
    rules_text = """
    Además, aplica estrictamente las siguientes reglas de ortografía del español:
    1. En títulos, subtítulos y encabezados, usa mayúscula inicial solamente en la primera palabra y en los nombres propios.
    2. Los subtítulos que siguen a dos puntos (:) después de un título no deben llevar mayúscula inicial.
    3. Cuando una frase va entre comillas y termina con punto y coma (;), punto (.) o coma (,), estos signos van fuera de las comillas.
    """ if apply_rules else ""

    prompt = f"""
    Por favor, reescribe el siguiente texto para que se ajuste al estilo y tono descritos por el usuario.
    Mantén el significado y la información original, pero ajusta la forma en que se expresa.
    Si el texto contiene formato como encabezados de Markdown (ej: # Título), presérvalos.
    {rules_text}
    
    Descripción del estilo y tono deseados por el usuario:
    "{style_description}"
    
    Texto original:
    {text}
    
    Texto reescrito:
    """
    
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])] # <-- LÍNEA CORREGIDA
    
    tools = [types.Tool(googleSearch=types.GoogleSearch())] if enable_search else None
    
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=-1),
        tools=tools,
    )
    
    try:
        response_text = ""
        for chunk in client.models.generate_content_stream(
            model="gemini-flash-latest",
            contents=contents,
            config=config,
        ):
            response_text += chunk.text
        return response_text
    except Exception as e:
        st.error(f"Error al cambiar el estilo: {str(e)}")
        return text

def correct_style(client: genai.Client, text: str, apply_rules: bool, enable_search: bool) -> str:
    """Utiliza Gemini para realizar correcciones de estilo."""
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
    
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])] # <-- LÍNEA CORREGIDA
    
    tools = [types.Tool(googleSearch=types.GoogleSearch())] if enable_search else None
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=-1),
        tools=tools,
    )
    
    try:
        response_text = ""
        for chunk in client.models.generate_content_stream(
            model="gemini-flash-latest",
            contents=contents,
            config=config,
        ):
            response_text += chunk.text
        return response_text
    except Exception as e:
        st.error(f"Error al realizar correcciones de estilo: {str(e)}")
        return text

def apply_spanish_orthography_rules(client: genai.Client, text: str) -> str:
    """Aplica reglas ortográficas específicas del español."""
    prompt = f"""
    Revisa y corrige el siguiente texto para que cumpla estrictamente con estas reglas de ortografía del español:
    
    1. **Capitalización de Títulos**: En títulos, subtítulos y encabezados (como los que empiezan con # en Markdown), solo la primera palabra y los nombres propios deben llevar mayúscula inicial.
    2. **Subtítulos después de Dos Puntos**: Si un subtítulo sigue a un título separado por dos puntos (:), el subtítulo no debe llevar mayúscula inicial.
    3. **Puntuación y Comillas**: Los signos de puntuación como punto (.), coma (,) y punto y coma (;) siempre se colocan fuera de las comillas de cierre.
    
    Aplica estas reglas sobre el siguiente texto y devuelve solo el texto corregido, sin explicaciones adicionales.
    
    Texto a corregir:
    {text}
    
    Texto corregido:
    """
    
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])] # <-- LÍNEA CORREGIDA
    
    config = types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=-1),
    )
    
    try:
        response_text = ""
        for chunk in client.models.generate_content_stream(
            model="gemini-flash-latest",
            contents=contents,
            config=config,
        ):
            response_text += chunk.text
        return response_text
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
    st.markdown("Esta aplicación utiliza la API de Google Gemini con capacidades avanzadas para editar y enriquecer tus documentos.")
    
    st.sidebar.header("Configuración")
    api_key = st.sidebar.text_input("Introduce tu API Key de Google Gemini:", type="password")
    
    st.sidebar.subheader("Descripción del Estilo y Tono")
    style_description = st.sidebar.text_area(
        "Describe cómo quieres que sea el nuevo documento:",
        placeholder="Ej: Quiero un tono profesional pero cercano, como si un experto le estuviera explicando el tema a un colega. Usa frases cortas y directas, y evita la jerga excesiva.",
        height=150
    )

    with st.sidebar.expander("💡 Ver ejemplos de descripciones"):
        st.markdown("""
        **Académico formal:**
        > "Escribe en un registro formal y académico. Utiliza un vocabulario preciso y una estructura argumentativa clara. Mantén un tono objetivo y analítico."
        
        **Marketing persuasivo:**
        > "Adopta un tono enérgico y persuasivo. Usa un lenguaje directo y orientado a la acción, destacando los beneficios."
        
        **Blog amigable:**
        > "El estilo debe ser conversacional y amigable. Usa un lenguaje sencillo, preguntas retóricas y un toque de humor."
        """)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Opciones de Procesamiento")
    process_chapters = st.sidebar.checkbox("Procesar capítulo por capítulo", value=True)
    apply_corrections = st.sidebar.checkbox("Aplicar correcciones de estilo", value=True)
    apply_spanish_rules = st.sidebar.checkbox(
        "Aplicar reglas ortográficas del español", 
        value=True,
        help="Aplica reglas específicas de capitalización y puntuación en español."
    )
    enable_google_search = st.sidebar.checkbox(
        "Habilitar Búsqueda de Google", 
        value=False,
        help="Permite que la IA busque información en tiempo real para mejorar o contextualizar el texto. Puede ralentizar el proceso."
    )
    
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
                if not style_description:
                    st.warning("Por favor, describe el estilo y tono que deseas aplicar.")
                else:
                    with st.spinner("Procesando documento..."):
                        client = configure_gemini(api_key)
                        if client:
                            processed_chapters = []
                            progress_bar = st.progress(0)
                            
                            for i, chapter in enumerate(chapters):
                                edited_chapter = change_style_based_on_description(
                                    client, chapter, style_description, apply_spanish_rules, enable_google_search
                                )
                                
                                if apply_corrections:
                                    edited_chapter = correct_style(client, edited_chapter, apply_spanish_rules, enable_google_search)
                                
                                if apply_spanish_rules:
                                    edited_chapter = apply_spanish_orthography_rules(client, edited_chapter)
                                
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
    "Esta aplicación utiliza la API de Google Gemini con capacidades avanzadas como Búsqueda de Google y Modo de Pensamiento "
    "para editar y enriquecer tus documentos."
)

st.sidebar.markdown("### Instrucciones de uso")
st.sidebar.markdown(
    """
    1. Introduce tu API Key de Google Gemini.
    2. Describe con detalle el estilo y tono que quieres.
    3. Selecciona las opciones de corrección y mejoras.
    4. Sube tu documento (PDF, TXT o MD).
    5. Haz clic en "Procesar documento".
    6. Revisa el resultado y descarga el archivo editado.
    """
)

# Ejecutar la aplicación principal
if __name__ == "__main__":
    main()
