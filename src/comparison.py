"""Comparison logic for the Comparateur_PDF project."""

from typing import Dict
import re
import streamlit as st
from .utils import parse_date, normalize_serial

def compare_rvd_aed() -> Dict[str, Dict[str, str]]:
    """Compare data from RVD and AED reports.

    Returns:
        Comparison results.
    """
    results = {}
    aed_type = f'AEDG{st.session_state.dae_type[-1]}'
    if not st.session_state.processed_data.get('RVD'):
        st.error("Données RVD manquantes pour la comparaison")
        return results
    if not st.session_state.processed_data.get(aed_type):
        st.error(f"Données {aed_type} manquantes pour la comparaison")
        return results

    rvd = st.session_state.processed_data['RVD']
    aed = st.session_state.processed_data[aed_type]

    aed_key = 'N° série DAE' if st.session_state.dae_type == 'G5' else 'Série DSA'
    results['serial'] = {
        'rvd': rvd.get('Numéro de série DEFIBRILLATEUR', 'N/A'),
        'aed': aed.get(aed_key, 'N/A'),
        'match': normalize_serial(rvd.get('Numéro de série DEFIBRILLATEUR', '')) ==
                 normalize_serial(aed.get(aed_key, ''))
    }

    rvd_date, rvd_err = parse_date(rvd.get('Date-Heure rapport vérification défibrillateur', ''))
    aed_date_key = 'Date / Heure:' if st.session_state.dae_type == 'G5' else 'Date de mise en service'
    aed_date, aed_err = parse_date(aed.get(aed_date_key, ''))
    results['report_date'] = {
        'rvd': rvd.get('Date-Heure rapport vérification défibrillateur', 'N/A'),
        'aed': aed.get(aed_date_key, 'N/A'),
        'match': rvd_date == aed_date if not (rvd_err or aed_err) else False,
        'errors': [e for e in [rvd_err, aed_err] if e]
    }

    rvd_batt_date, rvd_batt_err = parse_date(rvd.get('Date mise en service BATTERIE', ''))
    aed_batt_key = "Date d'installation :" if st.session_state.dae_type == 'G5' else 'Date de mise en service batterie'
    aed_batt_date, aed_batt_err = parse_date(aed.get(aed_batt_key, ''))
    results['battery_install_date'] = {
        'rvd': rvd.get('Date mise en service BATTERIE', 'N/A'),
        'aed': aed.get(aed_batt_key, 'N/A'),
        'match': rvd_batt_date == aed_batt_date if not (rvd_batt_err or aed_batt_err) else False,
        'errors': [e for e in [rvd_batt_err, aed_batt_err] if e]
    }

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

    st.session_state.processed_data['comparisons']['rvd_vs_aed'] = results
    return results

def compare_rvd_images() -> Dict[str, Dict[str, str]]:
    """Compare data from RVD and image analyses.

    Returns:
        Comparison results.
    """
    results = {}
    if not st.session_state.processed_data.get('RVD'):
        st.error("Données RVD manquantes pour la comparaison")
        return results

    rvd = st.session_state.processed_data['RVD']
    images = st.session_state.processed_data['images']

    field_mapping = {
        "batterie": {
            "serial": (
                "Numéro de série Batterie"
                if rvd.get("Changement batterie") == "Non"
                else "N° série nouvelle batterie"
            ),
            "date": "Date fabrication BATTERIE"
        },
        "electrodes_adultes": {
            "serial": (
                "Numéro de série ELECTRODES ADULTES"
                if rvd.get("Changement électrodes adultes") == "Non"
                else "N° série nouvelles électrodes"
            ),
            "date": (
                "Date de péremption ELECTRODES ADULTES"
                if rvd.get("Changement électrodes adultes") == "Non"
                else "Date péremption des nouvelles éléctrodes"
            )
        },
        "electrodes_pediatriques": {"serial": "N/A", "date": "N/A"},
        "defibrillateur": {
            "serial": "Numéro de série DEFIBRILLATEUR",
            "date": "Date fabrication DEFIBRILLATEUR"
        }
    }
    if rvd.get("Changement électrodes pédiatriques") == "Oui":
        field_mapping["electrodes_pediatriques"] = {
            "serial": "N° série nouvelles électrodes pédiatriques",
            "date": "Date péremption des nouvelles éléctrodes pédiatriques"
        }

    battery_data = next((i for i in images if i['type'] == 'Batterie'), None)
    if battery_data:
        results.update(_compare_battery(rvd, battery_data, field_mapping))

    electrode_data = next((i for i in images if i['type'] == 'Electrodes'), None)
    if electrode_data:
        results.update(_compare_electrodes(rvd, electrode_data, field_mapping))

    defibrillator_data = next((i for i in images if i['type'] == 'Defibrillateur G5'), None)
    if defibrillator_data:
        results.update(_compare_defibrillator(rvd, defibrillator_data, field_mapping))

    st.session_state.processed_data['comparisons']['rvd_vs_images'] = results
    return results

def _compare_battery(rvd: Dict, battery_data: Dict, field_mapping: Dict) -> Dict[str, Dict[str, str]]:
    """Helper function to compare battery data."""
    results = {}
    results['battery_serial'] = {
        'rvd': rvd.get(field_mapping["batterie"]["serial"], 'N/A'),
        'image': battery_data.get('serial', 'N/A'),
        'match': normalize_serial(rvd.get(field_mapping["batterie"]["serial"], '')) ==
                 normalize_serial(battery_data.get('serial', ''))
    }
    rvd_date, rvd_err = parse_date(rvd.get(field_mapping["batterie"]["date"], ''))
    img_date, img_err = parse_date(battery_data.get('date', ''))
    results['battery_date'] = {
        'rvd': rvd.get(field_mapping["batterie"]["date"], 'N/A'),
        'image': battery_data.get('date', 'N/A'),
        'match': rvd_date == img_date if not (rvd_err or img_err) else False,
        'errors': [e for e in [rvd_err, img_err] if e]
    }
    return results

def _compare_electrodes(rvd: Dict, electrode_data: Dict, field_mapping: Dict) -> Dict[str, Dict[str, str]]:
    """Helper function to compare electrode data."""
    results = {}
    results['electrode_serial'] = {
        'rvd': rvd.get(field_mapping["electrodes_adultes"]["serial"], 'N/A'),
        'image': electrode_data.get('serial', 'N/A'),
        'match': normalize_serial(rvd.get(field_mapping["electrodes_adultes"]["serial"], '')) ==
                 normalize_serial(electrode_data.get('serial', ''))
    }
    rvd_date, rvd_err = parse_date(rvd.get(field_mapping["electrodes_adultes"]["date"], ''))
    img_date, img_err = parse_date(electrode_data.get('date', ''))
    results['electrode_date'] = {
        'rvd': rvd.get(field_mapping["electrodes_adultes"]["date"], 'N/A'),
        'image': electrode_data.get('date', 'N/A'),
        'match': rvd_date == img_date if not (rvd_err or img_err) else False,
        'errors': [e for e in [rvd_err, img_err] if e]
    }
    if rvd.get("Changement électrodes pédiatriques") == "Oui":
        results['pediatric_electrode_serial'] = {
            'rvd': rvd.get(field_mapping["electrodes_pediatriques"]["serial"], 'N/A'),
            'image': electrode_data.get('serial', 'N/A'),
            'match': normalize_serial(rvd.get(field_mapping["electrodes_pediatriques"]["serial"], '')) ==
                     normalize_serial(electrode_data.get('serial', ''))
        }
        rvd_ped_date, rvd_ped_err = parse_date(rvd.get(field_mapping["electrodes_pediatriques"]["date"], ''))
        img_ped_date, img_ped_err = parse_date(electrode_data.get('date', ''))
        results['pediatric_electrode_date'] = {
            'rvd': rvd.get(field_mapping["electrodes_pediatriques"]["date"], 'N/A'),
            'image': electrode_data.get('date', 'N/A'),
            'match': rvd_ped_date == img_ped_date if not (rvd_ped_err or img_ped_err) else False,
            'errors': [e for e in [rvd_ped_err, img_ped_err] if e]
        }
    return results

def _compare_defibrillator(rvd: Dict, defibrillator_data: Dict, field_mapping: Dict) -> Dict[str, Dict[str, str]]:
    """Helper function to compare defibrillator data."""
    results = {}
    results['defibrillator_serial'] = {
        'rvd': rvd.get(field_mapping["defibrillateur"]["serial"], 'N/A'),
        'image': defibrillator_data.get('serial', 'N/A'),
        'match': normalize_serial(rvd.get(field_mapping["defibrillateur"]["serial"], '')) ==
                 normalize_serial(defibrillator_data.get('serial', ''))
    }
    rvd_date, rvd_err = parse_date(rvd.get(field_mapping["defibrillateur"]["date"], ''))
    img_date, img_err = parse_date(defibrillator_data.get('date', ''))
    results['defibrillator_date'] = {
        'rvd': rvd.get(field_mapping["defibrillateur"]["date"], 'N/A'),
        'image': defibrillator_data.get('date', 'N/A'),
        'match': rvd_date == img_date if not (rvd_err or img_err) else False,
        'errors': [e for e in [rvd_err, img_err] if e]
    }
    return results 
