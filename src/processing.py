"""Image and PDF processing functions for the Comparateur_PDF project."""

import logging
import os
import tempfile
from typing import Dict, List, Optional, Tuple
import io
import numpy as np
import pdfplumber
import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter, ExifTags
from .config import MODEL_ID
from .extraction import extract_rvd_data

# Set up logging
logger = logging.getLogger(__name__)


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
                logger.debug("Rotated image by %s degrees", degrees)
    except (AttributeError, KeyError, OSError) as e:
        logger.warning("Could not process EXIF orientation: %s", e)
    
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
    # Import here to avoid circular imports
    
    return client.infer(image_path, model_id=MODEL_ID)


def extract_text_from_pdf(uploaded_file) -> str:
    """Extract text from a PDF file.

    Args:
        uploaded_file: The uploaded PDF file (Streamlit UploadedFile).

    Returns:
        Extracted text from the PDF.
    """
    text = ""
    try:
        # Read bytes from the uploaded file
        file_bytes = uploaded_file.read()
        file_like_object = io.BytesIO(file_bytes)
        
        with pdfplumber.open(file_like_object) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
    except Exception as e:
        logger.error("PDF text extraction failed: %s", e)
    
    return text



def process_pdf_file(
    uploaded_file, 
    error_container
) -> None:
    """Process a PDF file based on its type.
    
    Args:
        uploaded_file: The PDF file to process
        error_container: Streamlit container for errors
    """
    text = extract_text_from_pdf(uploaded_file)
    filename_lower = uploaded_file.name.lower()
    
    # Process RVD documents
    if is_rvd_document(uploaded_file.name, text):
        try:
            # Import here to avoid circular imports
            
            st.session_state.processed_data['RVD'] = extract_rvd_data(text)
            st.success(f"RVD traité : {uploaded_file.name}")
        except Exception as e:
            error_container.error(f"Erreur lors du traitement RVD : {uploaded_file.name} - {e}")
            logger.error("RVD processing error: %s", e)
            
    # Process AED documents
    elif 'aed' in filename_lower:
        try:
            # Import here to avoid circular imports
            from .extraction import extract_aed_g5_data, extract_aed_g3_data
            aed_type = st.session_state.dae_type
            
            if aed_type == "G5":
                st.session_state.processed_data['AEDG5'] = extract_aed_g5_data(text)
            else:
                st.session_state.processed_data['AEDG3'] = extract_aed_g3_data(text)
                
            st.success(f"Rapport AED {aed_type} traité : {uploaded_file.name}")
        except Exception as e:
            error_container.error(f"Erreur lors du traitement AED : {uploaded_file.name} - {e}")
            logger.error("AED processing error: %s", e)
            
    # Unrecognized PDF type
    else:
        st.warning(f"Type de PDF non reconnu : {uploaded_file.name}")


def process_image_file(
    uploaded_file, 
    error_container, 
    client, 
    reader
) -> None:
    """Process an image file.
    
    Args:
        uploaded_file: The image file to process
        error_container: Streamlit container for errors
        client: ML client for classification
        reader: OCR reader
    """
    temp_file_path = None
    image = None
    
    try:
        # Open and preprocess image
        image = Image.open(uploaded_file)
        image = fix_orientation(image)
        image = image.convert('RGB')
        
        # Save to temporary file for classification
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            image.save(temp_file, format='JPEG')
            temp_file_path = temp_file.name
        
        # Import extraction functions (here to avoid circular imports)
        from .extraction import (
            extract_important_info_g3, extract_important_info_g5,
            extract_important_info_batterie, extract_important_info_electrodes
        )
        
        # Classify image
        result = classify_image(client, temp_file_path)
        detected_classes = [
            pred['class'] for pred in result.get('predictions', [])
            if pred['confidence'] > 0.5
        ]
        
        # Process based on classification
        process_classified_image(image, detected_classes, reader, uploaded_file, 
                                 extract_important_info_g3, extract_important_info_g5,
                                 extract_important_info_batterie, extract_important_info_electrodes)
                
    except ValueError as e:
        logger.warning("Value error processing %s: %s", uploaded_file.name, e)
        error_container.error(
            f"Erreur de valeur lors de la classification de {uploaded_file.name} : {e}"
        )
        # Append image even on error, with an error type
        add_error_image(image, 'Erreur de classification')
    
    except Exception as e:
        logger.error("Unexpected error processing %s: %s", uploaded_file.name, e, exc_info=True)
        error_container.error(
            f"Erreur inattendue lors du traitement de {uploaded_file.name} : {e}"
        )
        # Append image even on unexpected errors
        add_error_image(image, 'Erreur de traitement')
    
    finally:
        # Clean up temp file
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


def process_classified_image(
    image, detected_classes, reader, uploaded_file,
    extract_important_info_g3, extract_important_info_g5,
    extract_important_info_batterie, extract_important_info_electrodes
):
    """Process an image based on its classification.
    
    Args:
        image: The image to process
        detected_classes: List of detected classes
        reader: OCR reader
        uploaded_file: The original uploaded file
        extract_*: Various extraction functions
    """
    # Create img_data with default values
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
    
    # Add the image data to session state
    st.session_state.processed_data['images'].append(img_data)


def add_error_image(image, error_type):
    """Add an image with error information to the session state.
    
    Args:
        image: The image that caused the error
        error_type: Type of error that occurred
    """
    img_data = {
        'type': error_type,
        'serial': None,
        'date': None,
        'image': image if image is not None else None
    }
    st.session_state.processed_data['images'].append(img_data)


def initialize_session_data():
    """Initialize session state data structures if they don't exist."""
    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = {'images': []}
    elif 'images' not in st.session_state.processed_data:
        st.session_state.processed_data['images'] = []


def process_uploaded_file(
    uploaded_file, 
    progress_bar, 
    status_text, 
    error_container, 
    i: int, 
    total_files: int, 
    client, 
    reader
) -> None:
    """Process a single uploaded file.
    
    Args:
        uploaded_file: The file to process
        progress_bar: Streamlit progress bar
        status_text: Streamlit text element for status updates
        error_container: Streamlit container for errors
        i: Current file index
        total_files: Total number of files
        client: ML client for classification
        reader: OCR reader
    """
    # Initialize data structures
    initialize_session_data()
    
    # Update progress
    progress = (i + 1) / total_files
    progress_bar.progress(progress)
    
    # Update status
    status_text.markdown(
        f"""
        <div style="padding: 1rem; background: rgba(0,102,153,0.05); border-radius: 8px;">
            🔍 Analyse du fichier {i+1}/{total_files} : <strong>{uploaded_file.name}</strong>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Process file based on type
    if uploaded_file.type == "application/pdf":
        process_pdf_file(uploaded_file, error_container)
    else:
        process_image_file(uploaded_file, error_container, client, reader)


# Additional utility functions

def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """Preprocess image to improve OCR results.
    
    Args:
        image: The image to preprocess.
        
    Returns:
        The preprocessed image.
    """
    # Convert to grayscale
    gray_image = image.convert('L')
    
    # Increase contrast
    enhancer = ImageEnhance.Contrast(gray_image)
    contrast_image = enhancer.enhance(2.0)
    
    # Apply slight sharpening
    sharpened = contrast_image.filter(ImageFilter.SHARPEN)
    
    # Apply slight blur to reduce noise
    processed_image = sharpened.filter(ImageFilter.GaussianBlur(radius=0.5))
    
    return processed_image


def is_rvd_document(filename: str, text: str) -> bool:
    """Check if the document is an RVD report.
    
    Args:
        filename: Name of the file
        text: Extracted text from the document
        
    Returns:
        True if RVD document, False otherwise
    """
    if 'rapport de vérification' in filename.lower():
        return True
    
    # Keywords that indicate an RVD document
    rvd_keywords = [
        "rapport de vérification défibrillateur",
        "commentaire fin d'intervention",
        "numéro de série defibrillateur"
    ]
    
    return any(keyword in text.lower() for keyword in rvd_keywords)


def get_aed_type(filename: str, text: str) -> Optional[str]:
    """Determine the AED type from filename and content.
    
    Args:
        filename: Name of the file
        text: Extracted text from the document
        
    Returns:
        "G3", "G5", or None if not determined
    """
    filename_lower = filename.lower()
    text_lower = text.lower()
    
    if 'g5' in filename_lower or 'g5' in text_lower:
        return "G5"
    
    if 'g3' in filename_lower or 'g3' in text_lower:
        return "G3"
    
    return None
