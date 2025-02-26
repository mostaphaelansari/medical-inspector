"""Comparison logic for the Comparateur_PDF project organized by equipment sections."""

from typing import Dict, List, Tuple, Optional
import re
import streamlit as st
from .utils import parse_date, normalize_serial

def compare_data() -> Dict[str, Dict[str, Dict]]:
    """Compare data across all sources organized by equipment type.
    
    Returns:
        Comparison results organized by equipment section.
    """
    results = {
        "defibrillateur": {},
        "batterie": {},
        "electrodes": {}
    }
    
    # Check if necessary data is available
    aed_type = f'AEDG{st.session_state.dae_type[-1]}'
    if not st.session_state.processed_data.get('RVD'):
        st.error("Données RVD manquantes pour la comparaison")
        return results
    
    # Get data sources
    rvd = st.session_state.processed_data.get('RVD', {})
    aed = st.session_state.processed_data.get(aed_type, {})
    images = st.session_state.processed_data.get('images', [])
    
    # Process defibrillator section
    results["defibrillateur"] = compare_defibrillateur(rvd, aed, images)
    
    # Process battery section
    results["batterie"] = compare_batterie(rvd, aed, images)
    
    # Process electrodes section
    results["electrodes"] = compare_electrodes(rvd, aed, images)
    
    # Store results in session state
    st.session_state.processed_data['comparisons'] = results
    return results

def compare_defibrillateur(rvd: Dict, aed: Dict, images: List[Dict]) -> Dict[str, Dict]:
    """Compare defibrillator data across all sources.
    
    Args:
        rvd: RVD data dictionary
        aed: AED data dictionary
        images: List of image analysis results
        
    Returns:
        Defibrillator comparison results
    """
    results = {}
    
    # Serial number comparison
    aed_key = 'N° série DAE' if st.session_state.dae_type == 'G5' else 'Série DSA'
    results['Numéro de série'] = {
        'rvd': rvd.get('Numéro de série DEFIBRILLATEUR', 'N/A'),
        'aed': aed.get(aed_key, 'N/A'),
        'match_rvd_aed': normalize_serial(rvd.get('Numéro de série DEFIBRILLATEUR', '')) ==
                         normalize_serial(aed.get(aed_key, ''))
    }
    
    # Add image comparison if available
    defibrillator_image = next((i for i in images if i['type'] == 'Defibrillateur G5'), None)
    if defibrillator_image:
        results['Numéro de série']['image'] = defibrillator_image.get('serial', 'N/A')
        results['Numéro de série']['match_rvd_image'] = normalize_serial(rvd.get('Numéro de série DEFIBRILLATEUR', '')) == \
                                             normalize_serial(defibrillator_image.get('serial', ''))
    
    # Manufacturing date comparison
    if defibrillator_image:
        rvd_date, rvd_err = parse_date(rvd.get('Date fabrication DEFIBRILLATEUR', ''))
        img_date, img_err = parse_date(defibrillator_image.get('date', ''))
        results['date de fabrication'] = {
            'rvd': rvd.get('Date fabrication DEFIBRILLATEUR', 'N/A'),
            'image': defibrillator_image.get('date', 'N/A'),
            'match': rvd_date == img_date if not (rvd_err or img_err) else False,
            'errors': [e for e in [rvd_err, img_err] if e]
        }
    
    # Report date comparison
    rvd_date, rvd_err = parse_date(rvd.get('Date-Heure rapport vérification défibrillateur', ''))
    aed_date_key = 'Date / Heure:' if st.session_state.dae_type == 'G5' else 'Date de mise en service'
    aed_date, aed_err = parse_date(aed.get(aed_date_key, ''))
    results['Date de rapport'] = {
        'rvd': rvd.get('Date-Heure rapport vérification défibrillateur', 'N/A'),
        'aed': aed.get(aed_date_key, 'N/A'),
        'match': rvd_date == aed_date if not (rvd_err or aed_err) else False,
        'errors': [e for e in [rvd_err, aed_err] if e]
    }
    
    return results

def compare_batterie(rvd: Dict, aed: Dict, images: List[Dict]) -> Dict[str, Dict]:
    """Compare battery data across all sources.
    
    Args:
        rvd: RVD data dictionary
        aed: AED data dictionary
        images: List of image analysis results
        
    Returns:
        Battery comparison results
    """
    results = {}
    
    # Determine which field to use based on battery change status
    battery_serial_field = (
        "Numéro de série Batterie"
        if rvd.get("Changement batterie") == "Non"
        else "N° série nouvelle batterie"
    )
    
    # Battery serial comparison
    battery_image = next((i for i in images if i['type'] == 'Batterie'), None)
    if battery_image:
        results['Numéro de série'] = {
            'rvd': rvd.get(battery_serial_field, 'N/A'),
            'image': battery_image.get('serial', 'N/A'),
            'match': normalize_serial(rvd.get(battery_serial_field, '')) ==
                     normalize_serial(battery_image.get('serial', ''))
        }
    
    # Battery date comparison
    if battery_image:
        rvd_date, rvd_err = parse_date(rvd.get('Date fabrication BATTERIE', ''))
        img_date, img_err = parse_date(battery_image.get('date', ''))
        results['Date de fabrication'] = {
            'rvd': rvd.get('Date fabrication BATTERIE', 'N/A'),
            'image': battery_image.get('date', 'N/A'),
            'match': rvd_date == img_date if not (rvd_err or img_err) else False,
            'errors': [e for e in [rvd_err, img_err] if e]
        }
    
    # Battery installation date comparison
    rvd_batt_date, rvd_batt_err = parse_date(rvd.get('Date mise en service BATTERIE', ''))
    aed_batt_key = "Date d'installation :" if st.session_state.dae_type == 'G5' else 'Date de mise en service batterie'
    aed_batt_date, aed_batt_err = parse_date(aed.get(aed_batt_key, ''))
    results['installation_date'] = {
        'rvd': rvd.get('Date mise en service BATTERIE', 'N/A'),
        'aed': aed.get(aed_batt_key, 'N/A'),
        'match': rvd_batt_date == aed_batt_date if not (rvd_batt_err or aed_batt_err) else False,
        'errors': [e for e in [rvd_batt_err, aed_batt_err] if e]
    }
    
    # Battery level comparison
    try:
        rvd_batt = float(rvd.get('Niveau de charge de la batterie en %', 0))
        aed_batt_text = (
            aed.get('Capacité restante de la batterie', '0')
            if st.session_state.dae_type == 'G5'
            else aed.get('Capacité restante de la batterie 12V', '0')
        )
        aed_batt = float(re.search(r'\d+', aed_batt_text).group())
        results['battery_level'] = {
            'rvd': f"{rvd_batt}%",
            'aed': f"{aed_batt}%",
            'match': abs(rvd_batt - aed_batt) <= 2
        }
    except (ValueError, AttributeError) as e:
        results['battery_level'] = {
            'error': f"Données de batterie invalides : {str(e)}",
            'match': False
        }
    
    return results

def compare_electrodes(rvd: Dict, aed: Dict, images: List[Dict]) -> Dict[str, Dict]:
    """Compare electrodes data across all sources.
    
    Args:
        rvd: RVD data dictionary
        aed: AED data dictionary
        images: List of image analysis results
        
    Returns:
        Electrodes comparison results
    """
    results = {
        'adultes': {},
        'pediatriques': {}
    }
    
    # Adult electrodes
    electrode_serial_field = (
        "Numéro de série ELECTRODES ADULTES"
        if rvd.get("Changement électrodes adultes") == "Non"
        else "N° série nouvelles électrodes"
    )
    
    electrode_date_field = (
        "Date de péremption ELECTRODES ADULTES"
        if rvd.get("Changement électrodes adultes") == "Non"
        else "Date péremption des nouvelles éléctrodes"
    )
    
    # Adult electrodes serial comparison
    electrode_image = next((i for i in images if i['type'] == 'Electrodes'), None)
    if electrode_image:
        results['adultes']['Numéro_de_série'] = {
            'rvd': rvd.get(electrode_serial_field, 'N/A'),
            'image': electrode_image.get('serial', 'N/A'),
            'match': normalize_serial(rvd.get(electrode_serial_field, '')) ==
                     normalize_serial(electrode_image.get('serial', ''))
        }
    
    # Adult electrodes date comparison
    if electrode_image:
        rvd_date, rvd_err = parse_date(rvd.get(electrode_date_field, ''))
        img_date, img_err = parse_date(electrode_image.get('date', ''))
        results['adultes']['date_de_péremption'] = {
            'rvd': rvd.get(electrode_date_field, 'N/A'),
            'image': electrode_image.get('date', 'N/A'),
            'match': rvd_date == img_date if not (rvd_err or img_err) else False,
            'errors': [e for e in [rvd_err, img_err] if e]
        }
    
    # Pediatric electrodes (if changed)
    if rvd.get("Changement électrodes pédiatriques") == "Oui":
        pediatric_electrode_serial_field = "N° série nouvelles électrodes pédiatriques"
        pediatric_electrode_date_field = "Date péremption des nouvelles éléctrodes pédiatriques"
        
        # Add comparison data if pediatric electrode image is available
        # Note: Using same electrode image for now, as the original code did
        if electrode_image:
            results['pediatriques']['Numéro_de_série'] = {
                'rvd': rvd.get(pediatric_electrode_serial_field, 'N/A'),
                'image': electrode_image.get('serial', 'N/A'),
                'match': normalize_serial(rvd.get(pediatric_electrode_serial_field, '')) ==
                         normalize_serial(electrode_image.get('serial', ''))
            }
            
            rvd_ped_date, rvd_ped_err = parse_date(rvd.get(pediatric_electrode_date_field, ''))
            img_ped_date, img_ped_err = parse_date(electrode_image.get('date', ''))
            results['pediatriques']['date_de_péremption'] = {
                'rvd': rvd.get(pediatric_electrode_date_field, 'N/A'),
                'image': electrode_image.get('date', 'N/A'),
                'match': rvd_ped_date == img_ped_date if not (rvd_ped_err or img_ped_err) else False,
                'errors': [e for e in [rvd_ped_err, img_ped_err] if e]
            }
    
    return results
