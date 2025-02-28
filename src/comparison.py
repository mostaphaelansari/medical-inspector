from typing import Dict, List, Tuple, Optional, Callable, Any
import re
import streamlit as st
from datetime import datetime
from .utils import normalize_serial

# Precompiled regex patterns for better performance
DATE_PATTERN = re.compile(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{2,4}[-/]\d{1,2}[-/]?\d{0,2}|\d{1,2}[-/]\d{4})')
BATTERY_LEVEL_PATTERN = re.compile(r'\d+')

# Constants to avoid string duplication
NA = 'N/A'
G5_TYPE = 'G5'

# Common date formats consolidated in one place
DATE_FORMATS = [
    '%d/%m/%Y',           # 31/12/2023
    '%d-%m-%Y',           # 31-12-2023
    '%Y-%m-%d',           # 2023-12-31
    '%d/%m/%Y %H:%M:%S',  # 31/12/2023 14:30:00
    '%d/%m/%Y %H:%M',     # 31/12/2023 14:30
    '%d-%m-%Y %H:%M:%S',  # 31-12-2023 14:30:00
    '%d-%m-%Y %H:%M',     # 31-12-2023 14:30
    '%d %B %Y',           # 31 December 2023
    '%B %Y',              # December 2023
    '%m/%Y',              # 12/2023
    '%m-%Y'               # 12-2023
]

def parse_date(date_str: str) -> Tuple[Optional[datetime.date], Optional[str]]:
    """Parse a date string into a date object.

    Args:
        date_str: The date string to parse.

    Returns:
        Parsed date and error message if any.
    """
    formats = [
        '%d/%m/%Y %H:%M', '%d/%m/%Y %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S',
        '%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d', '%Y%m%d',
        '%d %b %Y', '%d %B %Y'
    ]
    clean_date = re.sub(r'[^\d:/ -]', '', str(date_str)).strip()
    clean_date = re.sub(r'/', '-', clean_date)
    date_part = clean_date.split(' ')[0] if ' ' in clean_date else clean_date
    for fmt in formats:
        try:
            return datetime.strptime(date_part, fmt).date(), None
        except ValueError:
            continue
    return None, f"Unrecognized format: {clean_date}"

def normalize_value(value: Any) -> Optional[str]:
    """Normalize a value to string or None if it's missing"""
    return value if value and value != NA else None

def compare_values(vals: Dict[str, Any], normalizer: Callable = lambda x: x) -> Dict:
    """Compare multiple values with normalization"""
    comparison = {k: v or NA for k, v in vals.items()}
    
    # Normalize all values
    normalized = {k: normalizer(v) for k, v in vals.items() if v and v != NA}
    
    # Generate all pairwise comparisons
    keys = list(normalized.keys())
    for i, key1 in enumerate(keys):
        for key2 in keys[i+1:]:
            comparison[f"match_{key1}_{key2}"] = normalized[key1] == normalized[key2]
    
    return comparison

def compare_rvd_releve(rvd_original: str, rvd_releve: str, aed_val: str, 
                      image_val: str, normalizer: Callable) -> Dict:
    """Compare original and relevé RVD values with AED and image data."""
    return compare_values({
        'rvd_original': rvd_original,
        'rvd_releve': rvd_releve,
        'aed': aed_val,
        'image': image_val
    }, normalizer)

def compare_dates_with_releve(rvd_orig_date: str, rvd_releve_date: str, 
                             aed_date: str, img_date: str) -> Dict:
    """Compare dates including original and relevé dates from RVD."""
    result = {
        'rvd_original': rvd_orig_date or NA,
        'rvd_releve': rvd_releve_date or NA,
        'aed': aed_date or NA,
        'image': img_date or NA,
        'errors': []
    }

    dates = {}
    for name, date_str in [
        ('rvd_original', rvd_orig_date),
        ('rvd_releve', rvd_releve_date),
        ('aed', aed_date),
        ('image', img_date)
    ]:
        if date_str and date_str != NA:
            parsed, error = parse_date(date_str)
            dates[name] = parsed
            if error:
                result['errors'].append(f"{name}: {error}")

    # For comparison, consider year and month only if any date is just month/year format
    month_year_only = any(d and (d.day == 1) for d in dates.values() if d is not None)
    
    valid_dates = [(k, v) for k, v in dates.items() if v is not None]
    
    for i, (name1, date1) in enumerate(valid_dates):
        for name2, date2 in valid_dates[i+1:]:
            if month_year_only:
                # Compare only year and month if any date might be month/year format
                result[f"match_{name1}_{name2}"] = (
                    date1.year == date2.year and date1.month == date2.month
                )
            else:
                result[f"match_{name1}_{name2}"] = date1 == date2
            
    return result

def get_image_by_type(images: List[Dict], image_type: str) -> Optional[Dict]:
    """Find an image by type from the image list"""
    return next((img for img in images if img.get('type') == image_type), None)

def get_dae_field(aed: Dict, field_g5: str, field_other: str) -> Optional[str]:
    """Get the appropriate field based on DAE type"""
    is_g5 = st.session_state.get('dae_type') == G5_TYPE
    return aed.get(field_g5 if is_g5 else field_other)

def compare_battery_level(rvd: Dict, aed: Dict) -> Dict:
    """Compare battery levels from RVD and AED"""
    result = {'match': False}
    
    try:
        rvd_batt_str = rvd.get('Niveau de charge de la batterie en %')
        if not rvd_batt_str or rvd_batt_str == NA:
            result['error'] = "Missing RVD battery data"
            return result
            
        rvd_batt = float(rvd_batt_str)
        result['rvd'] = f"{rvd_batt}%"
        
        is_g5 = st.session_state.get('dae_type') == G5_TYPE
        aed_batt_text = aed.get(
            'Capacité restante de la batterie' if is_g5 else 'Capacité restante de la batterie 12V'
        )
        
        if not aed_batt_text or aed_batt_text == NA:
            result['error'] = "Missing AED battery data"
            return result
            
        match = BATTERY_LEVEL_PATTERN.search(aed_batt_text)
        if not match:
            result['error'] = "Cannot extract battery level from AED data"
            return result
            
        aed_batt = float(match.group())
        result['aed'] = f"{aed_batt}%"
        result['match'] = abs(rvd_batt - aed_batt) <= 2
        
    except Exception as e:
        result['error'] = str(e)
    
    return result

def compare_electrodes_section(rvd: Dict, images: List[Dict], section_type: str) -> Dict:
    """Compare electrodes data (either adult or pediatric)"""
    image = get_image_by_type(images, 'Electrodes')
    
    prefix = "ADULTES" if section_type == "adultes" else "PEDIATRIQUES"
    
    serial_fields = (
        f'Numéro de série ELECTRODES {prefix}',
        f'Numéro de série ELECTRODES {prefix} relevé'
    )
    date_fields = (
        f'Date de péremption ELECTRODES {prefix}',
        f'Date de péremption ELECTRODES {prefix} relevée'
    )
    
    results = {}
    results['Numéro_de_série'] = compare_rvd_releve(
        rvd.get(serial_fields[0]),
        rvd.get(serial_fields[1]),
        None,
        image.get('serial') if image else None,
        normalize_serial
    )

    results['date_de_péremption'] = compare_dates_with_releve(
        rvd.get(date_fields[0]),
        rvd.get(date_fields[1]),
        None,
        image.get('date') if image else None
    )
    
    return results

def compare_section(section: str, rvd: Dict, aed: Dict, images: List[Dict]) -> Dict:
    """Unified comparison function with relevé data support."""
    if section == "defibrillateur":
        image = get_image_by_type(images, 'Defibrillateur G5')
        
        return {
            'Numéro de série': compare_rvd_releve(
                rvd.get('Numéro de série DEFIBRILLATEUR'),
                rvd.get('Numéro de série relevé'),
                get_dae_field(aed, 'N° série DAE', 'Série DSA'),
                image.get('serial') if image else None,
                normalize_serial
            ),
            'date de fabrication': compare_dates_with_releve(
                rvd.get('Date fabrication DEFIBRILLATEUR'),
                rvd.get('Date fabrication relevée'),
                None,
                image.get('date') if image else None
            ),
            'Date de rapport': compare_dates_with_releve(
                rvd.get('Date-Heure rapport vérification défibrillateur'),
                None,
                get_dae_field(aed, 'Date / Heure:', 'Date de mise en service'),
                None
            )
        }

    elif section == "batterie":
        image = get_image_by_type(images, 'Batterie')
        battery_serial_field = ("Numéro de série Batterie" if rvd.get("Changement batterie") == "Non"
                               else "N° série nouvelle batterie")

        return {
            'Numéro de série': compare_rvd_releve(
                rvd.get(battery_serial_field),
                rvd.get('Numéro de série relevé 2'),
                None,
                image.get('serial') if image else None,
                normalize_serial
            ),
            'Date de fabrication': compare_dates_with_releve(
                rvd.get('Date fabrication BATTERIE'),
                rvd.get('Date fabrication BATTERIE relevée'),
                None,
                image.get('date') if image else None
            ),
            'installation_date': compare_dates_with_releve(
                rvd.get('Date mise en service BATTERIE'),
                rvd.get('Date mise en service BATTERIE relevée'),
                get_dae_field(aed, "Date d'installation :", 'Date de mise en service batterie'),
                None
            ),
            'battery_level': compare_battery_level(rvd, aed)
        }

    elif section == "electrodes":
        results = {
            'adultes': compare_electrodes_section(rvd, images, "adultes")
        }
        
        # Only include pediatric electrodes if they were changed
        if rvd.get("Changement électrodes pédiatriques") == "Oui":
            results['pediatriques'] = compare_electrodes_section(rvd, images, "pediatriques")
        else:
            results['pediatriques'] = {}
            
        return results

    return {}

def compare_data() -> Dict[str, Dict[str, Dict]]:
    """Main comparison function with complete implementation."""
    results = {
        "defibrillateur": {},
        "batterie": {},
        "electrodes": {}
    }
    
    if not hasattr(st.session_state, 'dae_type'):
        st.error("Type de DAE non défini dans session_state")
        return results
    
    aed_type = f'AEDG{st.session_state.dae_type[-1]}'
    
    if not st.session_state.processed_data.get('RVD'):
        st.error("Données RVD manquantes pour la comparaison")
        return results
    
    rvd = st.session_state.processed_data.get('RVD', {})
    aed = st.session_state.processed_data.get(aed_type, {})
    images = st.session_state.processed_data.get('images', [])
    
    for section in results.keys():
        results[section] = compare_section(section, rvd, aed, images)
    
    st.session_state.processed_data['comparisons'] = results
    return results
