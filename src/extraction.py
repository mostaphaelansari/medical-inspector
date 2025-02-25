"""Data extraction functions for the Comparateur_PDF project."""

import re
from typing import Dict, List, Tuple, Optional
from PIL import Image, ImageEnhance, ImageFilter
from pyzbar.pyzbar import decode
import streamlit as st

def extract_rvd_data(text: str) -> Dict[str, str]:
    """Extract relevant data from the RVD text.

    Args:
        text: Text extracted from the RVD PDF.

    Returns:
        Extracted data with keywords as keys.
    """
    keywords = [
        "Commentaire fin d'intervention et recommandations",
        "Numéro de série DEFIBRILLATEUR",
        "Date-Heure rapport vérification défibrillateur",
        "Changement batterie",
        "Changement électrodes adultes",
        "Code site",
        "Numéro de série Batterie",
        "Date mise en service BATTERIE",
        "Niveau de charge de la batterie en %",
        "N° série nouvelle batterie",
        "Date mise en service",
        "Niveau de charge nouvelle batterie",
        "Numéro de série ELECTRODES ADULTES",
        "Numéro de série ELECTRODES ADULTES relevé",
        "Numéro de série relevé 2",
        "Date fabrication DEFIBRILLATEUR",
        "Date fabrication BATTERIE",
        "Date fabrication relevée",
        "Date fabrication nouvelle batterie",
        "Date de péremption ELECTRODES ADULTES",
        "Date de péremption ELECTRODES ADULTES relevée",
        "N° série nouvelles électrodes",
        "Date péremption des nouvelles éléctrodes",
    ]
    results = {}
    lines = text.splitlines()

    for keyword in keywords:
        value = "Non trouvé"
        if any(x in keyword.lower() for x in ["n° série", "numéro de série"]):
            pattern = re.compile(re.escape(keyword) + r"[\s:]*([A-Za-z0-9\-]+)(?=\s|$)", re.IGNORECASE)
        elif keyword == "Code site":
            pattern = re.compile(r"Code site\s+([A-Z0-9]+)", re.IGNORECASE)
        else:
            pattern = re.compile(re.escape(keyword) + r"[\s:]*([^\n]*)")

        for i, line in enumerate(lines):
            stripped_line = line.strip()
            if stripped_line.lower().startswith(keyword.lower()):
                match = pattern.search(stripped_line)
                if match:
                    value = match.group(1).strip()
                    if any(x in keyword.lower() for x in ["n° série", "numéro de série"]):
                        value = value.split()[0]
                else:
                    value = _get_next_valid_line(lines, i, keyword)
                break
            if keyword == "Code site":
                match = pattern.search(stripped_line)
                if match:
                    value = match.group(1)
                    break

        if value != "Non trouvé":
            value = re.sub(r'\s*(?:Vérification|Validation).*$', '', value)
            if "date" in keyword.lower() and re.search(r'\d{2}[/-]\d{2}[/-]\d{4}', value):
                value = re.search(r'\d{2}[/-]\d{2}[/-]\d{4}(?:\s+\d{2}:\d{2})?', value).group(0)
            elif "%" in keyword:
                value = re.sub(r'[^\d.]', '', value)

        results[keyword] = value
    return results

def _get_next_valid_line(lines: List[str], start_idx: int, keyword: str) -> str:
    """Helper function to get the next valid line after a keyword match."""
    j = start_idx + 1
    while j < len(lines):
        next_line = lines[j].strip()
        if (
            next_line and
            not any(x in next_line for x in ["Vérification", "Validation"])
        ):
            if "date" in keyword.lower() and not re.search(r'\d{2}[/-]\d{2}[/-]\d{4}', next_line):
                j += 1
                continue
            return next_line
        j += 1
    return "Non trouvé"

def extract_aed_g5_data(text: str) -> Dict[str, str]:
    """Extract relevant data from AED G5 text.

    Args:
        text: Text extracted from the AED G5 PDF.

    Returns:
        Extracted data with keywords as keys.
    """
    keywords = [
        "N° série DAE",
        "Capacité restante de la batterie",
        "Date d'installation :",
        "Rapport DAE - Erreurs en cours",
        "Date / Heure:",
    ]
    results = {}
    for keyword in keywords:
        pattern = re.compile(re.escape(keyword) + r"[\s:]*([^\n]*)")
        match = pattern.search(text)
        if match:
            results[keyword] = match.group(1).strip()
    return results

def extract_aed_g3_data(text: str) -> Dict[str, str]:
    """Extract relevant data from AED G3 text.

    Args:
        text: Text extracted from the AED G3 PDF.

    Returns:
        Extracted data with keywords as keys.
    """
    keywords = [
        "Série DSA",
        "Dernier échec de DSA",
        "Numéro de lot",
        "Date de mise en service",
        "Capacité initiale de la batterie 12V",
        "Capacité restante de la batterie 12V",
        "Autotest",
    ]
    results = {}
    lines = text.split('\n')
    for i, line in enumerate(lines):
        for keyword in keywords:
            if keyword in line:
                value = lines[i + 1].strip() if i + 1 < len(lines) else ""
                results[keyword] = value
    return results

def extract_important_info_g3(results: List[Tuple]) -> Tuple[Optional[str], Optional[str]]:
    """Extract important information from OCR results for G3 devices.

    Args:
        results: List of OCR results.

    Returns:
        Serial number and date of fabrication.
    """
    serial_number = None
    date_of_fabrication = None
    serial_pattern = r'\b(\d{5,10})\b'
    date_pattern = r'\b(\d{4}-\d{2}-\d{2}|\d{6})\b'
    for _, text, _ in results:
        if not serial_number:
            serial_search = re.search(serial_pattern, text)
            if serial_search:
                serial_number = serial_search.group(1)
        if not date_of_fabrication:
            date_search = re.search(date_pattern, text)
            if date_search:
                date_of_fabrication = date_search.group(1)
    return serial_number, date_of_fabrication

def extract_important_info_g5(results: List[Tuple]) -> Tuple[Optional[str], Optional[str]]:
    """Extract important information from OCR results for G5 devices.

    Args:
        results: List of OCR results.

    Returns:
        Serial number and date of fabrication.
    """
    serial_number = None
    date_of_fabrication = None
    date_pattern = r"(\d{4}-\d{2}-\d{2})"
    serial_pattern = r"([A-Za-z]*\s*[\dOo]+)"
    sn_found = False
    for _, text, _ in results:
        if "SN" in text or "Serial Number" in text:
            sn_found = True
            continue
        if sn_found:
            serial_match = re.search(serial_pattern, text)
            if serial_match:
                processed_serial = serial_match.group().replace('O', '0').replace('o', '0')
                serial_number = processed_serial
                sn_found = False
        date_search = re.search(date_pattern, text)
        if date_search:
            date_of_fabrication = date_search.group(1)
    return serial_number, date_of_fabrication

def extract_important_info_batterie(results: List[Tuple]) -> Tuple[Optional[str], Optional[str]]:
    """Extract important information from OCR results for batteries.

    Args:
        results: List of OCR results.

    Returns:
        Serial number and date of fabrication.
    """
    serial_number = None
    date_of_fabrication = None
    date_pattern = r"(\d{4}-\d{2}-\d{2})"
    sn_pattern = r"\b(?:SN|LOT|Lon|Loz|Lo|LO|Lot|Lool|LOTI|Lotl|LOI|Lod)\b"
    serial_number_pattern = (
        r"\b(?:SN|LOT|Lon|Loz|Lot|Lotl|LoI|Lool|Lo|Lod|LO|LOTI|LOI)?\s*([0-9A-Za-z\-]{5,})\b"
    )
    sn_found = False
    for _, text, _ in results:
        if re.search(sn_pattern, text, re.IGNORECASE):
            sn_found = True
            continue
        if sn_found:
            serial_match = re.search(serial_number_pattern, text)
            if serial_match:
                serial_number = serial_match.group(1)
                sn_found = False
        if re.search(date_pattern, text):
            date_of_fabrication = re.search(date_pattern, text).group(0)
    return serial_number, date_of_fabrication

def extract_important_info_electrodes(image: Image.Image) -> Tuple[Optional[str], Optional[str]]:
    """Extract important information from electrode images.

    Args:
        image: The image of the electrodes.

    Returns:
        Serial number and expiration date.
    """
    try:
        width, height = image.size
        crop_box = (width * 0.2, height * 0.10, width * 1, height * 1)
        cropped_image = image.crop(crop_box)

        enhancer = ImageEnhance.Contrast(cropped_image)
        enhanced_image = enhancer.enhance(2.5)
        enhanced_image = enhanced_image.filter(ImageFilter.SHARPEN)

        barcodes = decode(enhanced_image)
        if barcodes:
            if len(barcodes) >= 2:
                return (
                    barcodes[0].data.decode('utf-8'),
                    barcodes[1].data.decode('utf-8')
                )
            st.warning(
                f"Nombre inattendu de codes-barres trouvés : {len(barcodes)}. "
                "Attendait au moins 2."
            )
            return None, None
        st.warning("Aucun code-barres détecté dans l'image des électrodes.")
        return None, None
    except ValueError as e:
        st.error(f"Erreur de valeur lors du traitement de l'image : {e}")
        return None, None
