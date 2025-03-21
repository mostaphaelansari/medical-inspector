"""Data extraction functions for the Comparateur_PDF project."""

import re
import pdfplumber
from typing import Dict, List, Tuple, Optional ,Any
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
    def get_next_valid_line(lines: List[str], current_index: int, keyword: str) -> str:
        """Get the next non-empty line after the keyword line that might contain the value."""
        if current_index + 1 < len(lines):
            next_line = lines[current_index + 1].strip()
            if next_line and not any(kw.lower() in next_line.lower() for kw in keywords):
                return next_line
        return ""
    
    keywords = [
        "Commentaire fin d'intervention et recommandations",
        "Date-Heure rapport vérification défibrillateur",
        "Code du site",
        #Défibrillateur
        "Numéro de série DEFIBRILLATEUR",
        "Numéro de série relevé",
        "Date fabrication DEFIBRILLATEUR",
        "Date fabrication relevée",
        
       
        #Batterie
        "Numéro de série Batterie",
        "Numéro de série relevé 2",
        "Date fabrication BATTERIE",
        "Date fabrication BATTERIE relevée",
        "Date mise en service BATTERIE",
        "Date mise en service BATTERIE relevée",
        "Niveau de charge de la batterie en %",
        "Changement batterie",
        "N° série nouvelle batterie",
        "Date mise en service",
        "Date de mise en service de la nouvelle batterie",
        "Date fabrication nouvelle batterie",
        "Niveau de charge nouvelle batterie",
        #Electrodes Adultes
        "Numéro de série ELECTRODES ADULTES",
        "Numéro de série ELECTRODES ADULTES relevé",
        "Date de péremption ELECTRODES ADULTES",
        "Date de péremption ELECTRODES ADULTES relevée",
        "Changement électrodes adultes",
        "N° série nouvelles électrodes",
        "Date péremption des nouvelles éléctrodes",
        #Electrodes pédiatriques (à faire)
        "Numéro de série ELECTRODES PEDIATRIQUES",
        "Numéro de série ELECTRODES PEDIATRIQUES relevé",
        "Date de péremption ELECTRODES PEDIATRIQUES",
        "Date de péremption ELECTRODES PEDIATRIQUES relevée",
    ]
    results = {}
    lines = text.splitlines()
    for keyword in keywords:
        value = ""
        if any(x in keyword.lower() for x in ["n° série", "numéro de série"]):
            pattern = re.compile(re.escape(keyword) + r"[\s:]*([A-Za-z0-9\-]+)(?=\s|$)", re.IGNORECASE)
        elif keyword.lower() == "code site":
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
                    value = get_next_valid_line(lines, i, keyword)
                break
            
            if keyword.lower() == "code site":
                match = pattern.search(stripped_line)
                if match:
                    value = match.group(1)
                    break
                    
        if value:
            value = re.sub(r'\s*(?:Vérification|Validation).*$', '', value)
            if "date" in keyword.lower() and re.search(r'\d{2}[/-]\d{2}[/-]\d{4}', value):
                value = re.search(r'\d{2}[/-]\d{2}[/-]\d{4}(?:\s+\d{2}:\d{2})?', value).group(0)
            elif "%" in keyword:
                value = re.sub(r'[^\d.]', '', value)
        
        results[keyword] = value
    
    return results



def extract_aed_g5_data(text: str) -> Dict[str, any]:
    """Extract relevant data and errors from AED G5 text.
    
    Args:
        text: Text extracted from the AED G5 PDF.
    
    Returns:
        Dictionary containing both extracted data with keywords as keys
        and a list of errors under the 'errors' key.
    """
    keywords = [
        "N° série DAE",
        "Capacité restante de la batterie",
        "Date d'installation :",
        "Rapport DAE - Erreurs en cours",
        "Date / Heure:",
    ]
    
    results = {}
    
    # Extract keyword data
    for keyword in keywords:
        pattern = re.compile(re.escape(keyword) + r"[\s:]*([^\n]*)")
        match = pattern.search(text)
        if match:
            results[keyword] = match.group(1).strip()
    
    # Extract errors
    errors = re.findall(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})\s+(0x[0-9A-Fa-f]+)", text)
    results["errors"] = errors
    
    # Print error information
    if errors:
        print("Errors found:")
        for error in errors:
            print(f"Date/Time: {error[0]}, Error ID: {error[1]}")
    else:
        print("No errors found in the section.")
    
    return results

def extract_aed_g3_data(text: str) -> Dict[str, Any]:
    """Extrait des mots-clés spécifiques d'un texte de rapport AED.
    
    Args:
        text (str): Texte extrait du rapport AED.
    
    Returns:
        Dict[str, Any]: Dictionnaire contenant les valeurs extraites pour chaque mot-clé
                        et une liste des erreurs sous la clé 'errors'.
    """
    # Liste des mots-clés à extraire
    keywords = {
        "Série DSA": "Série DSA",
        "Dernier échec de DSA": "Dernier échec de DSA",
        "Numéro de lot": "Numéro de lot",
        "Date de mise en service": "Date de mise en service",
        "Autotest": "Autotest",
    }
    
    # Dictionnaire pour stocker les résultats
    results = {}

    try:
        # Extraction des valeurs pour les mots-clés standards
        for key, pattern_base in keywords.items():
            pattern_escaped = re.escape(pattern_base)
            pattern = f"{pattern_escaped}\\s*:\\s*([^\\n]+)"
            
            match = re.search(pattern, text)
            if match:
                value = match.group(1).strip()
                
                # Traitement spécial pour Série DSA: supprimer le premier 0
                if key == "Série DSA" and value and value[0] == "0":
                    value = value[1:]
                
                # Traitement spécial pour Numéro de lot: insérer un '-' après le 5ème chiffre
                if key == "Numéro de lot" and len(value) > 5:
                    value = value[:5] + "-" + value[5:]
                
                results[key] = value
            else:
                results[key] = ""

        # Extraction et conversion des capacités de batterie
        match_initial = re.search(r"Capacité initiale de la batterie 12V\s*:\s*(\d+)\s*mAh", text)
        match_remaining = re.search(r"Capacité restante de la batterie 12V\s*:\s*(\d+)\s*mAh", text)

        if match_initial and match_remaining:
            initial_mAh = float(match_initial.group(1))
            remaining_mAh = float(match_remaining.group(1))

            # Conversion en volts
            initial_V = initial_mAh / 625  # Approximate conversion
            remaining_V = remaining_mAh / 625

            # Calcul du pourcentage de batterie restante
            battery_percentage = (remaining_mAh / initial_mAh) * 100

            results["Capacité initiale de la batterie"] = f"{initial_V:.2f} V"
            results["Capacité restante de la batterie"] = f"{remaining_V:.2f} V"
            results["Pourcentage de la batterie"] = f"{battery_percentage:.2f} %"
        else:
            results["Capacité initiale de la batterie"] = ""
            results["Capacité restante de la batterie"] = ""
            results["Pourcentage de la batterie"] = ""

        # Extraction des erreurs (codes d'erreur avec date/heure)
        errors = re.findall(r"(Code d'erreur \w+)\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}:\d{2})", text)
        results["errors"] = [(f"{date} {time}", code) for code, date, time in errors]

        # Extraction de la dernière date d'installation depuis "Aucune erreur trouvée"
        # Modifié pour tenir compte du format réel sans espace entre "trouvée" et la date
        date_pattern = r"Aucune erreur trouvée\s*(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}:\d{2})"
        dates_found = re.findall(date_pattern, text)

        if dates_found:
            # dates_found contient maintenant une liste de tuples (date, heure)
            last_date, last_time = dates_found[-1]  # Prendre la dernière occurrence
            results["Date installation"] = f"{last_date} {last_time}"
        else:
            results["Date installation"] = ""

        return results

    except Exception as e:
        print(f"Erreur lors de l'extraction des données: {e}")
        return {"erreur": str(e)}




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



