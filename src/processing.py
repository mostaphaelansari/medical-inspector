"""Image and PDF processing functions for the Comparateur_PDF project."""

import os
import tempfile
import numpy as np
from typing import Dict, List, Tuple
from PIL import Image, ImageEnhance, ImageFilter, ExifTags

import pdfplumber
import streamlit as st

def fix_orientation(img: Image.Image) -> Image.Image:
    """Adjust image orientation based on EXIF data.

    Args:
        img: The image to correct.

    Returns:
        The corrected image.
    """
    try:
        orientation = None
        for key in ExifTags.TAGS:
            if ExifTags.TAGS[key] == 'Orientation':
                orientation = key
                break
        if orientation is not None:
            exif = dict(img.getexif().items())
            rotation_map = {3: 180, 6: 270, 8: 90}
            degrees = rotation_map.get(exif.get(orientation))
            if degrees:
                img = img.rotate(degrees, expand=True)
    except (AttributeError, KeyError):
        pass  # Consider logging this in production
    return img

@st.cache_data
def process_ocr(_reader, image: Image.Image) -> List[Tuple]:
    """Perform OCR on the given image.

    Args:
        _reader: Initialized EasyOCR reader (excluded from cache key).
        image: The image to process.

    Returns:
        A list of tuples containing the recognized text and its position.
    """
    return _reader.readtext(np.array(image))

def classify_image(client, image_path: str) -> Dict:
    """Classify an image using the machine learning model.

    Args:
        client: Initialized InferenceHTTPClient.
        image_path: Path to the image file.

    Returns:
        Classification results.
    """
    from .config import MODEL_ID
    return client.infer(image_path, model_id=MODEL_ID)

def extract_text_from_pdf(uploaded_file) -> str:
    """Extract text from a PDF file.

    Args:
        uploaded_file: The uploaded PDF file.

    Returns:
        Extracted text from the PDF.
    """
    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def process_uploaded_file(uploaded_file, progress_bar, status_text, error_container, i, total_files, client, reader):
    """Process a single uploaded file."""
    progress = (i + 1) / total_files
    progress_bar.progress(progress)
    status_text.markdown(
        f"""
        <div style="padding: 1rem; background: rgba(0,102,153,0.05); border-radius: 8px;">
            🔍 Analyse du fichier {i+1}/{total_files} : <strong>{uploaded_file.name}</strong>
        </div>
        """,
        unsafe_allow_html=True
    )

    if uploaded_file.type == "application/pdf":
        text = extract_text_from_pdf(uploaded_file)
        if 'rapport de vérification' in uploaded_file.name.lower():
            from .extraction import extract_rvd_data
            st.session_state.processed_data['RVD'] = extract_rvd_data(text)
            st.success(f"RVD traité : {uploaded_file.name}")
        elif 'aed' in uploaded_file.name.lower():
            from .extraction import extract_aed_g5_data, extract_aed_g3_data
            if st.session_state.dae_type == "G5":
                st.session_state.processed_data['AEDG5'] = extract_aed_g5_data(text)
            else:
                st.session_state.processed_data['AEDG3'] = extract_aed_g3_data(text)
            st.success(f"Rapport AED {st.session_state.dae_type} traité : {uploaded_file.name}")
        else:
            st.warning(f"Type de PDF non reconnu : {uploaded_file.name}")
    else:
        image = Image.open(uploaded_file)
        image = fix_orientation(image)
        image = image.convert('RGB')
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            image.save(temp_file, format='JPEG')
            temp_file_path = temp_file.name
        try:
            from .extraction import (
                extract_important_info_g3, extract_important_info_g5,
                extract_important_info_batterie, extract_important_info_electrodes
            )
            result = classify_image(client, temp_file_path)
            detected_classes = [
                pred['class'] for pred in result.get('predictions', [])
                if pred['confidence'] > 0.5
            ]
            
            # Always create img_data, even if no classification
            img_data = {
                'type': detected_classes[0] if detected_classes else 'Non classifié',
                'serial': None,
                'date': None,
                'image': image
            }
            
            # Process further if classified
            if detected_classes:
                if "Defibrillateur" in detected_classes[0]:
                    results = process_ocr(reader, image)
                    if "G3" in detected_classes[0]:
                        img_data['serial'], img_data['date'] = extract_important_info_g3(results)
                    else:
                        img_data['serial'], img_data['date'] = extract_important_info_g5(results)
                elif "Batterie" in detected_classes[0]:
                    results = process_ocr(reader, image)
                    img_data['serial'], img_data['date'] = extract_important_info_batterie(results)
                elif "Electrodes" in detected_classes[0]:
                    img_data['serial'], img_data['date'] = extract_important_info_electrodes(image)
                st.success(f"Image {detected_classes[0]} traitée : {uploaded_file.name}")
            else:
                st.warning(f"Aucune classification trouvée pour : {uploaded_file.name}")
            
            # Always append the image data, classified or not
            st.session_state.processed_data['images'].append(img_data)
        
        except ValueError as e:
            error_container.error(
                f"Erreur de valeur lors de la classification de {uploaded_file.name} : {e}"
            )
            # Append image even on error, with an error type
            img_data = {
                'type': 'Erreur de classification',
                'serial': None,
                'date': None,
                'image': image
            }
            st.session_state.processed_data['images'].append(img_data)
        
        except Exception as e:
            error_container.error(
                f"Erreur inattendue lors du traitement de {uploaded_file.name} : {e}"
            )
            # Append image even on unexpected errors
            img_data = {
                'type': 'Erreur de traitement',
                'serial': None,
                'date': None,
                'image': image
            }
            st.session_state.processed_data['images'].append(img_data)
        
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
