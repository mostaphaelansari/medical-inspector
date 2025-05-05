"""Streamlit UI components for the Comparateur_PDF project."""

import base64
import json
import os
import shutil
import tempfile
from datetime import datetime
from io import BytesIO
from typing import Any, Dict
import zipfile
import altair as alt
import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import Image
from tkinter import Tk, filedialog

from .config import ALLOWED_EXTENSIONS, CSS_STYLE
from .processing import process_uploaded_file
from .comparison import compare_data



def display_comparison_dashboard(data: Dict[str, Dict]) -> None:
    """
    Display a comprehensive, visually-appealing comparison dashboard.
    
    Args:
        data: The complete comparison data structure
    """
    # Apply custom CSS for better styling
    st.markdown("""
    <style>
    .comparison-card {
        border-radius: 5px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .field-label {
        font-weight: 600;
        color: #555;
    }
    .match-indicator {
        font-size: 1.2rem;
        font-weight: bold;
    }
    .data-value {
        font-family: monospace;
        background-color: #f5f5f5;
        padding: 0.2rem 0.4rem;
        border-radius: 3px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 100%;
        display: inline-block;
    }
    .st-emotion-cache-z5fcl4 {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create summary metrics at the top
    if data:
        create_summary_metrics(data)
    
    # Display each section with improved visuals
    for section_name, section_data in data.items():
        if section_data:
            display_section_card(section_name, section_data)

def create_summary_metrics(data: Dict[str, Dict]) -> None:
    """
    Create summary metrics and visualizations for the overall comparison.
    
    Args:
        data: The complete comparison data
    """
    # Calculate overall statistics
    total_fields = 0
    total_comparisons = 0
    successful_matches = 0
    sections_data = []
    
    for section_name, section_data in data.items():
        section_fields = 0
        section_comparisons = 0
        section_matches = 0
        
        for field, field_data in section_data.items():
            if isinstance(field_data, dict):
                if field in ['adultes', 'pediatriques']:
                    # Handle nested structure
                    for subfield, subdata in field_data.items():
                        section_fields += 1
                        match_keys = [k for k in subdata.keys() if k.startswith('match_')] if isinstance(subdata, dict) else []
                        section_comparisons += len(match_keys)
                        section_matches += sum(1 for k in match_keys if subdata.get(k, False))
                else:
                    section_fields += 1
                    match_keys = [k for k in field_data.keys() if k.startswith('match_')]
                    section_comparisons += len(match_keys)
                    section_matches += sum(1 for k in match_keys if field_data.get(k, False))
        
        total_fields += section_fields
        total_comparisons += section_comparisons
        successful_matches += section_matches
        
        if section_comparisons > 0:
            match_percentage = (section_matches / section_comparisons) * 100
            sections_data.append({
                "section": section_name.replace('_', ' ').title(),
                "percentage": round(match_percentage, 1)
            })
    
    # Display metrics in a card
    with st.container():
        st.markdown("""
        <div style="background-color: #66CDAA; padding: 1.5rem; border-radius: 10px; 
                   margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <h2 style="margin-top: 0;">Rapport de Comparaison</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Summary metrics in columns
        if total_comparisons > 0:
            overall_percentage = (successful_matches / total_comparisons) * 100
            
            cols = st.columns(4)
            cols[0].metric(
                label="Champs Analysés",
                value=total_fields
            )
            cols[1].metric(
                label="Vérifications",
                value=total_comparisons
            )
            cols[2].metric(
                label="Correspondances",
                value=successful_matches
            )
            cols[3].metric(
                label="Taux de Correspondance",
                value=f"{overall_percentage:.1f}%",
                delta="objectif: 100%" if overall_percentage < 100 else None,
                delta_color="inverse"
            )
            
            # Create a chart for section-by-section comparison
            if sections_data:
                st.markdown("### Comparaison par Section")
                df = pd.DataFrame(sections_data)
                
                chart = alt.Chart(df).mark_bar().encode(
                    x=alt.X('percentage:Q', title='Pourcentage de Correspondance'),
                    y=alt.Y('section:N', title='', sort='-x'),
                    color=alt.Color('percentage:Q', scale=alt.Scale(
                        domain=[0, 50, 100],
                        range=['#ff4b4b', '#ffa500', '#00cc96']
                    )),
                    tooltip=['section', 'percentage']
                ).properties(
                    height=len(sections_data) * 40
                )
                
                st.altair_chart(chart, use_container_width=True)

def display_section_card(section_name: str, section_data: Dict[str, Dict]) -> None:
    """
    Display a section's data in a visually appealing card format, 
    ensuring display even if no matches are found.
    
    Args:
        section_name: Name of the section
        section_data: Comparison data for the section
    """
    display_name = section_name.replace('_', ' ').title()
    
    with st.expander(f"📊 {display_name}", expanded=True):
        # Initialize metrics
        total_comparisons = 0
        successful_matches = 0
        
        # Flag to track if any data was processed
        data_processed = False
        
        for field, data in section_data.items():
            if isinstance(data, dict):
                # Handle nested structures
                if field in ['adultes', 'pediatriques']:
                    st.markdown(f"### {field.title()}")
                    for subfield, subdata in data.items():
                        display_field_card(subfield, subdata)
                        
                        # Count matches
                        match_keys = [k for k in subdata.keys() if k.startswith('match_')]
                        total_comparisons += len(match_keys)
                        successful_matches += sum(1 for k in match_keys if subdata.get(k, False))
                        
                        # Mark that data was processed
                        if match_keys:
                            data_processed = True
                else:
                    display_field_card(field, data)
                    
                    # Count matches
                    match_keys = [k for k in data.keys() if k.startswith('match_')]
                    total_comparisons += len(match_keys)
                    successful_matches += sum(1 for k in match_keys if data.get(k, False))
                    
                    # Mark that data was processed
                    if match_keys:
                        data_processed = True
        
        # Section summary - always displayed
        st.markdown(f"### Résumé de la Section: {display_name}")
        
        # Handle case with no matches or no data processed
        if total_comparisons == 0 or not data_processed:
            # Use columns for layout
            cols = st.columns([3, 1])
            with cols[0]:
                # Show empty progress bar
                st.progress(0)
            with cols[1]:
                # Display "No Data" message
                st.markdown(f'<p style="color:#6c757d; font-weight:bold; text-align:center; font-size:1.2rem;">N/A 📭</p>', unsafe_allow_html=True)
            
            # Optional: Add an informative message
            st.markdown("""
            <div style="background-color: #f8f9fa; border-left: 4px solid #6c757d; padding: 0.75rem; margin: 1rem 0;">
                <p style="margin: 0; color: #6c757d;">
                    ℹ️ Aucune donnée n'a été détectée pour cette section. 
                    Veuillez vérifier les entrées ou les sources de données.
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Calculate match percentage
            match_percentage = (successful_matches / total_comparisons) * 100
            
            # Use columns for better layout
            cols = st.columns([3, 1])
            with cols[0]:
                st.progress(match_percentage / 100)
            with cols[1]:
                if match_percentage == 100:
                    st.markdown(f'<p style="color:#00cc96; font-weight:bold; text-align:center; font-size:1.2rem;">100% ✅</p>', unsafe_allow_html=True)
                elif match_percentage >= 75:
                    st.markdown(f'<p style="color:#ffa500; font-weight:bold; text-align:center; font-size:1.2rem;">{match_percentage:.1f}% ⚠️</p>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<p style="color:#ff4b4b; font-weight:bold; text-align:center; font-size:1.2rem;">{match_percentage:.1f}% ❌</p>', unsafe_allow_html=True)

def display_field_card(field_name: str, data: Dict[str, Any]) -> None:
    """
    Display data for a specific field in an attractive card layout.
    
    Args:
        field_name: Name of the field
        data: Comparison data for the field
    """
    display_name = field_name.replace('_', ' ').title()
    
    # Custom data sources for battery level
    if field_name == 'battery_level':
        data_sources = {
            "RVD": {'key': 'rvd', 'icon': '🔋', 'color': '#6c757d'},
            "AED": {'key': 'aed', 'icon': '🔌', 'color': '#28a745'}
        }
    else:
        # Default data sources for other fields
        data_sources = {
            "RVD Original": {'key': 'rvd_original', 'icon': '📄', 'color': '#6c757d'},
            "RVD Relevé": {'key': 'rvd_releve', 'icon': '📋', 'color': '#007bff'},
            "AED": {'key': 'aed', 'icon': '🔌', 'color': '#28a745'},
            "Image": {'key': 'image', 'icon': '📷', 'color': '#6610f2'}
        }

    # Card container
    st.markdown(f"""
    <div class="comparison-card" style="background-color: #ffffff;">
        <h4 style="margin-top: 0; color: #333;">{display_name}</h4>
        <p style="color: #666; font-size: 0.8rem; margin-bottom: 1rem;">Nom technique: {field_name}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Extract values with special handling for battery level
    values = {}
    for label, source_info in data_sources.items():
        value = data.get(source_info['key'], None)
        
        # Format battery percentage specifically
        if field_name == 'battery_level' and value not in [None, 'N/A', '-']:
            if isinstance(value, str) and '%' not in value:
                value = f"{value}%"
        
        values[label] = {
            'value': value if value is not None else '-',
            'icon': source_info['icon'],
            'color': source_info['color']
        }

    # Data source comparison
    source_cols = st.columns(len(data_sources))
    for i, (label, info) in enumerate(values.items()):
        with source_cols[i]:
            value_display = info['value'] if info['value'] not in [None, 'N/A', '-'] else '-'
            
            # Special styling for battery level
            battery_style = ""
            if field_name == 'battery_level' and '%' in str(value_display):
                battery_style = "font-weight: 700; color: #2e7d32;" if data.get('match', False) \
                    else "font-weight: 700; color: #d32f2f;"
            
            st.markdown(f"""
            <div style="padding: 0.5rem; border-left: 3px solid {info['color']}; 
                background-color: #f8f9fa; height: 100%;">
                <p style="margin: 0; font-weight: 600; color: {info['color']};">
                    {info['icon']} {label}
                </p>
                <div class="data-value" style="margin-top: 0.5rem; width: 100%; {battery_style}">
                    {value_display}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Match status (different presentation for battery level)
    if field_name == 'battery_level':
        if 'match' in data:
            cols = st.columns([7, 3])
            with cols[0]:
                color = '#00cc96' if data['match'] else '#ff4b4b'
                st.markdown(f"""
                <div style="background-color: #e9ecef; border-radius: 5px; height: 10px; width: 100%; margin-top: 0.5rem;">
                    <div style="background-color: {color}; width: {'100' if data['match'] else '0'}%; 
                        height: 100%; border-radius: 5px;"></div>
                </div>
                """, unsafe_allow_html=True)
            
            with cols[1]:
                status = "✅ Match" if data['match'] else "❌ Mismatch"
                color = '#00cc96' if data['match'] else '#ff4b4b'
                st.markdown(f'<p class="match-indicator" style="color:{color}; text-align:center;">{status}</p>', 
                          unsafe_allow_html=True)
    else:
        # Existing match status handling for other fields
        match_keys = [k for k in data.keys() if k.startswith('match_')]
        if match_keys:
            matches = sum(1 for k in match_keys if data.get(k, False))
            match_percentage = (matches / len(match_keys)) * 100
            
            cols = st.columns([7, 3])
            with cols[0]:
                color = get_match_color(match_percentage)
                st.markdown(f"""
                <div style="background-color: #e9ecef; border-radius: 5px; height: 10px; width: 100%; margin-top: 0.5rem;">
                    <div style="background-color: {color}; width: {match_percentage}%; height: 100%; border-radius: 5px;"></div>
                </div>
                """, unsafe_allow_html=True)
            
            with cols[1]:
                if matches == len(match_keys):
                    st.markdown(f'<p class="match-indicator" style="color:#00cc96; text-align:center;">100% ✅</p>', 
                              unsafe_allow_html=True)
                elif match_percentage >= 50:
                    st.markdown(f'<p class="match-indicator" style="color:#ffa500; text-align:center;">{match_percentage:.0f}% ⚠️</p>', 
                              unsafe_allow_html=True)
                else:
                    st.markdown(f'<p class="match-indicator" style="color:#ff4b4b; text-align:center;">{match_percentage:.0f}% ❌</p>', 
                              unsafe_allow_html=True)

    # Error handling - FIXED to avoid nested expanders
    if 'errors' in data and data['errors']:
        st.markdown("<p style='font-weight: bold; color: #856404; margin-top: 0.75rem;'>⚠️ Problèmes Détectés:</p>", 
                   unsafe_allow_html=True)
        for err in data['errors']:
            st.markdown(f"""
            <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 0.75rem; margin-bottom: 0.5rem;">
                <p style="margin: 0; color: #856404;">• {err}</p>
            </div>
            """, unsafe_allow_html=True)
    
    if 'error' in data and data['error']:
        st.markdown(f"""
        <div style="background-color: #f8d7da; border-left: 4px solid #dc3545; padding: 0.75rem; margin: 1rem 0;">
            <p style="margin: 0; color: #721c24;"><strong>🚫 Erreur critique:</strong> {data['error']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<hr style='margin: 1.5rem 0; opacity: 0.2;'>", unsafe_allow_html=True)

def get_match_color(percentage):
    """
    Determine color based on match percentage.
    
    Args:
        percentage: Match percentage
    
    Returns:
        Color code for the progress bar
    """
    if percentage == 100:
        return '#00cc96'  # Green for perfect match
    elif percentage >= 75:
        return '#ffa500'  # Orange for good match
    elif percentage >= 50:
        return '#ff7f50'  # Coral for partial match
    else:
        return '#ff4b4b'  # Red for poor match

# Sample usage
if __name__ == "__main__":
    st.set_page_config(
        page_title="Rapport de Comparaison",
        page_icon="📊",
        layout="wide"
    )
    
    # Demo data structure
    sample_data = {
        "informations_generales": {
            "model": {
                "rvd_original": "Zoll AED Plus",
                "rvd_releve": "Zoll AED Plus",
                "aed": "Zoll AED Plus",
                "image": "Zoll AED Plus",
                "match_rvd_aed": True,
                "match_rvd_image": True
            },
            "serial_number": {
                "rvd_original": "X12345678",
                "rvd_releve": "X12345678",
                "aed": "X12345678",
                "image": None,
                "match_rvd_aed": True,
                "errors": ["Numéro de série non visible sur l'image"]
            }
        },
        "electrodes": {
            "adultes": {
                "model": {
                    "rvd_original": "CPR-D-padz",
                    "rvd_releve": "CPR-D-padz",
                    "aed": "CPR-D",
                    "image": "CPR-D-padz",
                    "match_rvd_aed": False,
                    "match_rvd_image": True,
                    "errors": ["Discordance entre le modèle RVD et AED"]
                },
                "expiry_date": {
                    "rvd_original": "2025-06-30",
                    "rvd_releve": "2025-06-30",
                    "aed": "2025-06-30",
                    "image": "2025-06-30",
                    "match_rvd_aed": True,
                    "match_rvd_image": True
                }
            }
        }
    }
# Sample usage
if __name__ == "__main__":
    st.set_page_config(
        page_title="Rapport de Comparaison",
        page_icon="📊",
        layout="wide"
    )
    
    # Demo data structure
    sample_data = {
        "informations_generales": {
            "model": {
                "rvd_original": "Zoll AED Plus",
                "rvd_releve": "Zoll AED Plus",
                "aed": "Zoll AED Plus",
                "image": "Zoll AED Plus",
                "match_rvd_aed": True,
                "match_rvd_image": True
            },
            "serial_number": {
                "rvd_original": "X12345678",
                "rvd_releve": "X12345678",
                "aed": "X12345678",
                "image": None,
                "match_rvd_aed": True,
                "errors": ["Numéro de série non visible sur l'image"]
            }
        },
        "electrodes": {
            "adultes": {
                "model": {
                    "rvd_original": "CPR-D-padz",
                    "rvd_releve": "CPR-D-padz",
                    "aed": "CPR-D",
                    "image": "CPR-D-padz",
                    "match_rvd_aed": False,
                    "match_rvd_image": True,
                    "errors": ["Discordance entre le modèle RVD et AED"]
                },
                "expiry_date": {
                    "rvd_original": "2025-06-30",
                    "rvd_releve": "2025-06-30",
                    "aed": "2025-06-30",
                    "image": "2025-06-30",
                    "match_rvd_aed": True,
                    "match_rvd_image": True
                }
            }
        }
    }

# Helper function to open file dialog
def save_file_dialog(default_name):
    root = Tk()
    root.withdraw()  # Hide the root window
    root.wm_attributes('-topmost', 1)  # Keep the dialog on top
    file_path = filedialog.asksaveasfilename(
                    defaultextension=".pdf",
                    initialfile=default_name,
                    filetypes=[("PDF Files", "*.pdf"), ("Image Files", "*.png *.jpg *.jpeg")]
                )
    return file_path
def display_all_comparisons() -> None:
    """Display all comparison results with an overview summary."""
    if 'comparisons' not in st.session_state.processed_data:
        st.warning("Aucune comparaison disponible. Veuillez d'abord exécuter la comparaison des données.")
        return
    
    comparisons = st.session_state.processed_data['comparisons']
    
    # Overview section
    st.header("Résumé des Comparaisons")
    
    # Create metrics for overall statistics
    total_all = 0
    matches_all = 0
    section_stats = {}
    
    for section, data in comparisons.items():
        section_matches = 0
        section_total = 0
        
        # Function to process each data dict and count matches
        def count_matches(data_dict):
            matches = 0
            total = 0
            for k, v in data_dict.items():
                if k.startswith('match_') and isinstance(v, bool):
                    total += 1
                    if v:
                        matches += 1
            return matches, total
        
        # Process regular fields
        for field, field_data in data.items():
            if isinstance(field_data, dict):
                if field in ['adultes', 'pediatriques']:
                    # Process nested electrodes data
                    for _, subdata in field_data.items():
                        m, t = count_matches(subdata)
                        section_matches += m
                        section_total += t
                else:
                    # Process regular field data
                    m, t = count_matches(field_data)
                    section_matches += m
                    section_total += t
        
        # Store statistics for this section
        if section_total > 0:
            section_stats[section] = {
                'matches': section_matches,
                'total': section_total,
                'percentage': (section_matches / section_total * 100) if section_total > 0 else 0
            }
            total_all += section_total
            matches_all += section_matches
    
    # Display overall metrics
    cols = st.columns(len(section_stats) + 1)
    
    # Overall percentage
    overall_percentage = (matches_all / total_all * 100) if total_all > 0 else 0
    cols[0].metric(
        label="Correspondance Globale",
        value=f"{overall_percentage:.1f}%",
        delta=None
    )
    
    # Section percentages
    for i, (section, stats) in enumerate(section_stats.items(), 1):
        if i < len(cols):
            cols[i].metric(
                label=f"{section.title()}",
                value=f"{stats['percentage']:.1f}%",
                delta=f"{stats['matches']}/{stats['total']} correspondances"
            )
    
    # Detailed sections
    st.markdown("## Détails des comparaisons")
    

def setup_session_state():
    """Initialiser les variables d'état de session."""
    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = {
            'RVD': {},
            'AEDG5': {},
            'AEDG3': {},
            'images': [],
            'files': [],
            'comparisons': {
                'defibrillateur': {},
                'batterie': {},
                'electrodes': {}
            }
        }
    if 'dae_type' not in st.session_state:
        st.session_state.dae_type = 'G5'
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = []

def render_ui(client, reader):
    """Afficher l'interface utilisateur Streamlit."""
    st.set_page_config(page_title="Inspecteur de dispositifs médicaux", layout="wide")
    st.markdown(CSS_STYLE, unsafe_allow_html=True)
    setup_session_state()

    with st.container():
        st.markdown(
        """
        <div class="header" style="background: linear-gradient(to right, #006A4E, #307D7E); padding: 1.5rem; border-radius: 10px; color: white; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); margin-bottom: 2rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h1 style="margin: 0; font-size: 2.5rem; font-weight: 700; letter-spacing: -0.5px;">
                        Système d'inspection des dispositifs médicaux
                    </h1>
                    <p style="opacity: 0.9; margin: 0.5rem 0 0; font-size: 1.1rem;">
                        v2.1.0 | Plateforme d'analyse intelligente
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.sidebar:
        # Add custom CSS for #000bf7 blue theme
        st.markdown("""
            <style>
                /* Custom blue theme for sidebar */
                [data-testid="stSidebar"] {
                    background-color: #006A4E;
                    color: white;
                }
                
                /* Sidebar title and text */
                [data-testid="stSidebar"] .st-emotion-cache-1avcm0n {
                    color: white;
                }
                
                /* Headings in sidebar */
                [data-testid="stSidebar"] h1, 
                [data-testid="stSidebar"] h2, 
                [data-testid="stSidebar"] h3, 
                [data-testid="stSidebar"] h4 {
                    color: white;
                }
                
                /* Expander backgrounds */
                [data-testid="stSidebar"] .st-emotion-cache-1bx5d6i {
                    background-color: rgba(255, 255, 255, 0.1);
                    border-radius: 8px;
                    margin-bottom: 10px;
                }
                
                /* Toggle button colors */
                [data-testid="stSidebar"] .st-emotion-cache-19rxjzo {
                    background-color: #0009c8;
                }
                
                /* Secondary buttons */
                [data-testid="stSidebar"] [data-testid="baseButton-secondary"] {
                    background-color: rgba(255, 255, 255, 0.2);
                    color: white;
                    border: none;
                }
                
                /* Primary buttons */
                [data-testid="stSidebar"] [data-testid="baseButton-primary"] {
                    background-color: #ffffff;
                    color: #000bf7;
                }
                
                /* Footer styling */
                [data-testid="stSidebar"] div[style*="text-align:center"] {
                    background-color: rgba(255, 255, 255, 0.1) !important;
                    color: white !important;
                }
                
                /* Footer text */
                [data-testid="stSidebar"] div[style*="text-align:center"] p {
                    color: white !important;
                }
                
                /* Footer link */
                [data-testid="stSidebar"] div[style*="text-align:center"] a {
                    color: #cdd6ff !important;
                }
            </style>
        """, unsafe_allow_html=True)
        
        # Logo and App Title
        st.image("templates/img/Locacoeur-Logo-Transp.png", use_container_width=True)
        st.title("Système d'inspection des dispositifs médicaux 📟")
        st.markdown("---")
        
        # Main Configuration Section
        with st.expander("⚙️ Configuration du dispositif", expanded=True):
            # Device selection with visual icons
            st.markdown("#### 📱 Type d'appareil")
            device_col1, device_col2 = st.columns(2)
            
            with device_col1:
                g5_selected = st.session_state.get("dae_type", "G5") == "G5"
                if st.button("G5", use_container_width=True, 
                            type="primary" if g5_selected else "secondary"):
                    st.session_state.dae_type = "G5"
                    
            with device_col2:
                g3_selected = st.session_state.get("dae_type", "G5") == "G3"
                if st.button("G3", use_container_width=True, 
                            type="primary" if g3_selected else "secondary"):
                    st.session_state.dae_type = "G3"
            
            st.markdown(f"**Appareil sélectionné:** {st.session_state.get('dae_type', 'G5')}")
        
            # Processing Options Section
        with st.expander("🔧 Options de traitement", expanded=True):
                # Processing options with toggle switches
                st.markdown('<h4 style="color: white;">Configuration d\'analyse</h4>', unsafe_allow_html=True)
                
                # Using custom CSS to make the toggle labels white
                st.markdown("""
                <style>
                div[data-testid="stExpander"] label {
                    color: white !important;
                }
                </style>
                """, unsafe_allow_html=True)
                
                ocr_enabled = st.toggle(
                    "OCR (Reconnaissance de texte)",
                    value=st.session_state.get("enable_ocr", True),
                    help="Active la reconnaissance de texte sur les images"
                )
                st.session_state.enable_ocr = ocr_enabled
                
                auto_classify = st.toggle(
                    "Classification automatique",
                    value=st.session_state.get("auto_classify", True),
                    help="Active la classification automatique des documents"
                )
                st.session_state.auto_classify = auto_classify
        # User Guide
        with st.expander("🔍 Guide d'utilisation", expanded=False):
            st.markdown("""
                ### Comment utiliser l'application
                
                <div style="background-color:rgba(255, 255, 255, 0.15); padding:10px; border-radius:5px; margin-bottom:10px;">
                    <b>1. Préparation</b> 📋<br>
                    Vérifiez que vos documents sont au format requis et que les images sont nettes
                </div>
                
                <div style="background-color:rgba(255, 255, 255, 0.15); padding:10px; border-radius:5px; margin-bottom:10px;">
                    <b>2. Téléversement</b> 📤<br>
                    Glissez-déposez vos fichiers et attendez le traitement complet
                </div>
                
                <div style="background-color:rgba(255, 255, 255, 0.15); padding:10px; border-radius:5px; margin-bottom:10px;">
                    <b>3. Vérification</b> ✅<br>
                    Examinez les données extraites et validez les résultats
                </div>
                
                <div style="background-color:rgba(255, 255, 255, 0.15); padding:10px; border-radius:5px;">
                    <b>4. Export</b> 📥<br>
                    Choisissez le format d'export et téléchargez vos résultats
                </div>
            """, unsafe_allow_html=True)
        
        # Enhanced footer with version info
        st.markdown("---")
        st.markdown("""
        <div style="text-align:center; padding:1rem 0; background:rgba(255, 255, 255, 0.15); border-radius:8px;">
            <p style="margin:0; font-size:0.8rem; color:#ffffff;">Version 1.2.0</p>
            <p style="margin:0; font-size:0.8rem;">💻 Développé par <b>Locacoeur</b></p>
            <a href="mailto:support@locacoeur.com" style="font-size:0.75rem; color:#cdd6ff;">Contact support technique</a>
        </div>
        """, unsafe_allow_html=True)


    # Ensure session state initialization
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = []

    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = {'RVD': {}}

    # Custom CSS to make tabs much bigger
    st.markdown(
        """
        <style>
            /* Make tabs bigger */
            .stTabs [data-baseweb="tab"] {
                font-size: 24px !important; /* Super large text */
                font-weight: bold !important;
                padding: 15px 100px !important; /* Increase tab size */
                background-color: 14c394 !important; /* Highlight tabs */
                color: black !important;
                border-radius: 10px !important;
            }

            /* Make active tab even bigger */
            .stTabs [aria-selected="true"] {
                font-size: 28px !important;
                font-weight: 900 !important; /* Extra bold */
                background-color: #006A4E !important; /* Different color for active tab */
                color: white !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Téléversement",
        "📊 Analyse",
        "📋vs📋 Comparaison",
        "📤 Export"
    ])


    with tab1:
    # Header with styled title
        st.title("📋 Téléversement des documents")
        
        # Add custom CSS for better styling
        st.markdown("""
        <style>
        .upload-container {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
            margin-bottom: 1rem;
        }
        .success-message {
            padding: 10px;
            border-radius: 5px;
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .file-status {
            font-size: 0.9rem;
            color: #6c757d;
            margin-bottom: 0.5rem;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Divider
        st.markdown("---")
        
        # File upload section in expander
        with st.expander("Téléverser des documents", expanded=True):
            # Styled container for upload
            st.markdown('<div class="upload-container">', unsafe_allow_html=True)
            
            uploaded_files = st.file_uploader(
                "Glissez et déposez des fichiers ici",
                type=ALLOWED_EXTENSIONS,
                accept_multiple_files=True,
                help="Téléverser des rapports PDF et des images de dispositifs"
            )
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Process files if uploaded
            if uploaded_files:
                with st.container() as processing_container:
                    # Create columns for better layout
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                    
                    with col2:
                        file_counter = st.empty()
                        file_counter.markdown(f'<div class="file-status">0/{len(uploaded_files)} fichiers</div>', unsafe_allow_html=True)
                    
                    error_container = st.empty()
                    total_files = len(uploaded_files)
                    
                    # Process each file
                    for i, uploaded_file in enumerate(uploaded_files):
                        try:
                            # Update visual indicators
                            progress_value = i / total_files
                            progress_bar.progress(progress_value)
                            status_text.info(f"Traitement de: {uploaded_file.name}")
                            file_counter.markdown(f'<div class="file-status">{i}/{total_files} fichiers</div>', unsafe_allow_html=True)
                            
                            # Process the file
                            process_uploaded_file(
                                uploaded_file, progress_bar, status_text,
                                error_container, i, total_files, client, reader
                            )
                        except ValueError as e:
                            error_container.error(
                                f"Erreur de valeur lors du traitement de {uploaded_file.name} : {e}"
                            )
                    
                    # Complete the progress
                    progress_bar.progress(1.0)
                    file_counter.markdown(f'<div class="file-status">{total_files}/{total_files} fichiers</div>', unsafe_allow_html=True)
                    
                    # Store uploaded files in session state
                    st.session_state.uploaded_files = uploaded_files
                    
                    # Final success message
                    st.markdown(f"""
                    <div class="success-message">
                        <b>✅ Traitement terminé pour tous les {total_files} fichiers.</b>
                    </div>
                    """, unsafe_allow_html=True)

    with tab2:
        # ---- CSS for modern dashboard design ----
        st.markdown("""
        <style>
        :root {
            --primary-color: #3f51b5;
            --success-color: #2e7d32;
            --warning-color: #ed6c02;
            --error-color: #d32f2f;
        }

        /* Main container styling */
        .main-container {
            padding: 0;
            margin: 0;
            font-family: 'Inter', sans-serif;
        }
        
        /* Dashboard header */
        .dashboard-title {
            background-color: #f8f9fa;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.04);
            margin-bottom: 1.5rem;
            border-left: 5px solid var(--primary-color);
        }
        
        /* Card styles */
        .data-card {
            background-color: white;
            border-radius: 12px;
            padding: 1.2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            height: 100%;
            transition: all 0.3s ease;
        }
        
        .data-card:hover {
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }
        
        /* Section headers */
        .section-header {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: var(--primary-color);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        /* Document card */
        .document-card {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 3px 10px rgba(0,0,0,0.08);
            height: 100%;
            display: flex;
            flex-direction: column;
            border: 1px solid #f0f0f0;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .document-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.12);
        }
        
        .document-image {
            width: 100%;
            height: 180px;
            object-fit: cover;
            border-bottom: 1px solid #f0f0f0;
            background: #f8f9fa;
        }
        
        .document-content {
            padding: 1rem;
            flex-grow: 1;
        }
        
        .document-title {
            font-size: 0.95rem;
            font-weight: 600;
            margin-bottom: 0.75rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .document-info {
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 0.5rem 1rem;
            font-size: 0.85rem;
            margin-bottom: 1rem;
        }
        
        .info-label {
            color: #666;
        }
        
        .document-actions {
            display: flex;
            gap: 0.5rem;
        }
        
        .action-button {
            background-color: #f5f5f5;
            padding: 0.4rem 0.75rem;
            border-radius: 6px;
            border: none;
            color: #333;
            font-size: 0.8rem;
            font-weight: 500;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.25rem;
            transition: background-color 0.2s;
            width: 100%;
            justify-content: center;
        }
        
        .action-button:hover {
            background-color: #e0e0e0;
        }
        
        .success-tag {
            color: var(--success-color);
            background-color: rgba(46, 125, 50, 0.1);
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        
        .warning-tag {
            color: var(--warning-color);
            background-color: rgba(237, 108, 2, 0.1);
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        
        /* Empty state */
        .empty-state {
            background-color: #f8f9fa;
            border-radius: 12px;
            padding: 2rem;
            text-align: center;
            color: #666;
        }
        
        /* Tabs styling */
        .custom-tabs {
            border-bottom: 1px solid #e0e0e0;
            margin-bottom: 1.5rem;
            display: flex;
            gap: 1.5rem;
        }
        
        .custom-tab {
            padding: 0.75rem 0;
            font-weight: 500;
            color: #666;
            cursor: pointer;
            position: relative;
        }
        
        .custom-tab.active {
            color: var(--primary-color);
        }
        
        .custom-tab.active:after {
            content: '';
            position: absolute;
            bottom: -1px;
            left: 0;
            width: 100%;
            height: 2px;
            background-color: var(--primary-color);
        }
        
        /* Filter chip */
        .filter-chip {
            display: inline-flex;
            align-items: center;
            background-color: #f5f5f5;
            padding: 0.3rem 0.75rem;
            border-radius: 16px;
            margin-right: 0.5rem;
            font-size: 0.85rem;
            border: 1px solid #e0e0e0;
            cursor: pointer;
        }
        
        .filter-chip.active {
            background-color: #e8eaf6;
            border-color: #c5cae9;
            color: var(--primary-color);
        }
        
        /* Progress indicator */
        .progress-container {
            margin-bottom: 0.5rem;
        }
        
        .progress-bar {
            height: 8px;
            background-color: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background-color: var(--primary-color);
            border-radius: 4px;
        }
        
        /* Stats counter */
        .stats-counter {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        
        .counter-item {
            text-align: center;
            padding: 1rem;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        .counter-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary-color);
            margin-bottom: 0.25rem;
        }
        
        .counter-label {
            font-size: 0.8rem;
            color: #666;
        }

        /* Error styling */
        .error-time {
            font-size: 0.9em;
            color: #666;
            padding: 8px;
            background-color: #f8f9fa;
            border-radius: 5px;
            margin: 4px 0;
        }

        .error-code {
            font-weight: bold;
            color: #dc3545;
            padding: 8px;
            background-color: #ffeef0;
            border-radius: 5px;
            margin: 4px 0;
            text-align: center;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Dashboard header
        st.markdown("""
        <div class="dashboard-title">
            <h2 style="margin:0; font-size:1.5rem; font-weight:600;">📊 Analyse des données traitées</h2>
            <p style="margin:0.5rem 0 0 0; color:#666;">Visualisation et exploration des données extraites des documents</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Stats counters - key metrics at a glance
        processed_data = st.session_state.get('processed_data', {})
        images = processed_data.get('images', [])
        
        total_documents = len(images)
        classified_docs = sum(1 for img in images if img.get('type') not in 
                        ['Non classifié', 'Erreur de classification', 'Erreur de traitement'])
        error_docs = total_documents - classified_docs
        success_rate = int(classified_docs / total_documents * 100) if total_documents > 0 else 0
        
        st.markdown(f"""
        <div class="stats-counter">
            <div class="counter-item">
                <div class="counter-value">{total_documents}</div>
                <div class="counter-label">Documents</div>
            </div>
            <div class="counter-item">
                <div class="counter-value" style="color: var(--success-color);">{classified_docs}</div>
                <div class="counter-label">Traités</div>
            </div>
            <div class="counter-item">
                <div class="counter-value" style="color: var(--warning-color);">{error_docs}</div>
                <div class="counter-label">Erreurs</div>
            </div>
            <div class="counter-item">
                <div class="counter-value">{success_rate}%</div>
                <div class="counter-label">Réussite</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Main content tabs using Streamlit's native tabs
        tab_data, tab_images = st.tabs(["Données extraites", "Images analysées"])
        
        with tab_data:
            # Create two column layout for data cards
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("""
                    <div class="section-header">
                        <span>📄 Données RVD</span>
                    </div>
                    """, unsafe_allow_html=True)

                rvd_data = processed_data.get('RVD', {})  # Make sure this line's indentation matches the context
                if rvd_data:
                    with st.container():
                        st.markdown('<div class="data-card">', unsafe_allow_html=True)
                        
                        # JSON viewer (keep this for full data access)
                        with st.expander("Voir JSON complet", expanded=False):
                            st.json(rvd_data)
                        
                        # Convert flat part of JSON to DataFrame for better display
                        if isinstance(rvd_data, dict):
                            # Extract simple key-value pairs (non-nested)
                            flat_data = {k: v for k, v in rvd_data.items() if not isinstance(v, (dict, list))}
                            
                            # Create DataFrame and display it
                            if flat_data:
                                df = pd.DataFrame([flat_data])
                                st.dataframe(
                                    df.T.reset_index().rename(columns={"index": "Attribut", 0: "Valeur"}),
                                    hide_index=True,
                                    use_container_width=True
                                )
                            
                            # Check for changements and display alerts
                            changement = ["Changement batterie", "Changement électrodes adultes", "Changement électrodes pédiatriques"]
                            for i in changement:
                                if rvd_data.get(i) == "Oui":
                                    st.warning(f"{i} a été effectuée ⚠️")
                            # If there's any numerical data that could be visualized, add a chart
                            numerical_data = {k: v for k, v in flat_data.items() if isinstance(v, (int, float))}
                            if numerical_data:
                                st.subheader("Visualisation")
                                chart_data = pd.DataFrame([numerical_data])
                                fig = px.bar(chart_data.T.reset_index(), x="index", y=0, 
                                            labels={"index": "Mesure", "0": "Valeur"},
                                            title="Données numériques")
                                st.plotly_chart(fig, use_container_width=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="empty-state">
                        <p>Aucune donnée RVD n'a été traitée</p>
                        <p style="font-size:0.85rem; margin-top:0.5rem;">Veuillez traiter des documents pour voir les résultats</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            with col2:
                aed_type = f'AEDG{st.session_state.get("dae_type", "1")[-1]}'
                st.markdown(f"""
                <div class="section-header">
                    <span>📊 Données AED {st.session_state.get("dae_type", "")}</span>
                </div>
                """, unsafe_allow_html=True)
                
                aed_data = processed_data.get(aed_type, {})
                if aed_data:
                    with st.container():
                        st.markdown('<div class="data-card">', unsafe_allow_html=True)
                        
                        # Existing JSON viewer
                        with st.expander("Voir JSON complet", expanded=False):
                            st.json(aed_data)
                        
                        # Key metrics display
                        if isinstance(aed_data, dict):
                            cols = st.columns(2)
                            metric_keys = ['date', 'serial', 'id', 'status']
                            for i, key in enumerate(metric_keys):
                                with cols[i % 2]:
                                    if key in aed_data:
                                        st.metric(label=key.capitalize(), value=aed_data[key])
                            
                            # Flat data display
                            flat_data = {k: v for k, v in aed_data.items() 
                                        if not isinstance(v, (dict, list)) and k not in metric_keys}
                            
                            if flat_data:
                                st.subheader("Données détaillées")
                                df = pd.DataFrame([flat_data])
                                st.dataframe(
                                    df.T.reset_index().rename(columns={"index": "Attribut", 0: "Valeur"}),
                                    hide_index=True,
                                    use_container_width=True
                                )
                            
                            # Error display section (new part)
                            if "errors" in aed_data:
                                st.subheader("Journal des Erreurs")
                                
                                # Get error headers from metadata or use defaults
                                error_header = aed_data.get("Rapport DAE - Erreurs en cours", "Date/Heure,Code Erreur")
                                headers = [h.strip() for h in error_header.split(",")]
                                
                                # Create error cards
                                for error in aed_data["errors"]:
                                    cols = st.columns([2, 1])
                                    with cols[0]:
                                        st.markdown(f"""
                                        <div class="error-time">
                                            🕒 {error[0]}
                                        </div>
                                        """, unsafe_allow_html=True)
                                    with cols[1]:
                                        st.markdown(f"""
                                        <div class="error-code">
                                            ⚠️ {error[1]}
                                        </div>
                                        """, unsafe_allow_html=True)
                                    st.markdown("---")  # Separator
                            
                            # Visualization section
                            numerical_data = {k: v for k, v in flat_data.items() 
                                            if isinstance(v, (int, float))}
                            if numerical_data and len(numerical_data) > 1:
                                st.subheader("Visualisation")
                                chart_data = pd.DataFrame([numerical_data])
                                fig = px.bar(chart_data.T.reset_index(), x="index", y=0, 
                                            labels={"index": "Paramètre", "0": "Valeur"},
                                            title="Paramètres numériques")
                                st.plotly_chart(fig, use_container_width=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div class="empty-state">
                        <p>Aucune donnée AED n'a été trouvée</p>
                        <p style="font-size:0.85rem; margin-top:0.5rem;">Veuillez traiter des documents pour voir les résultats</p>
                    </div>
                    """, unsafe_allow_html=True)

            # Data visualization section
            st.markdown("""
            <div class="section-header" style="margin-top:2rem;">
                <span>📈 Visualisation des données</span>
            </div>
            """, unsafe_allow_html=True)
            
            if images:
                col1, col2 = st.columns(2)
                
                with col1:
                    with st.container():
                        st.markdown('<div class="data-card">', unsafe_allow_html=True)
                        st.markdown("<h4 style='margin-top:0;'>Types de documents</h4>", unsafe_allow_html=True)
                        
                        doc_types = {}
                        for img in images:
                            doc_type = img.get('type', 'Inconnu')
                            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                        
                        if doc_types:
                            fig = px.pie(
                                names=list(doc_types.keys()),
                                values=list(doc_types.values()),
                                hole=0.4,
                                color_discrete_sequence=['#3f51b5', '#f44336', '#4caf50', '#ff9800', '#9c27b0']
                            )
                            fig.update_layout(
                                margin=dict(t=0, b=0, l=0, r=0),
                                height=300,
                                showlegend=True,
                                legend=dict(orientation='h', y=-0.2)
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("Pas assez de données pour créer une visualisation")
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                
                with col2:
                    with st.container():
                        st.markdown('<div class="data-card">', unsafe_allow_html=True)
                        st.markdown("<h4 style='margin-top:0;'>Qualité du traitement</h4>", unsafe_allow_html=True)
                        
                        if total_documents > 0:
                            st.markdown(f"""
                            <div class="progress-container">
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width:{success_rate}%;"></div>
                                </div>
                            </div>
                            <div style="display:flex; justify-content:space-between; font-size:0.85rem; color:#666;">
                                <span>0%</span>
                                <span>{success_rate}% Complété</span>
                                <span>100%</span>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            status_data = pd.DataFrame({
                                'Status': ['Traités', 'Erreurs'],
                                'Count': [classified_docs, error_docs]
                            })
                            
                            fig = px.bar(
                                status_data,
                                x='Status',
                                y='Count',
                                color='Status',
                                color_discrete_map={'Traités': '#4caf50', 'Erreurs': '#f44336'}
                            )
                            fig.update_layout(
                                margin=dict(t=20, b=40, l=40, r=20),
                                height=240,
                                showlegend=False
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("Aucun document n'a été traité pour l'analyse")
                        
                        st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="empty-state">
                    <p>Aucune donnée disponible pour la visualisation</p>
                    <p style="font-size:0.85rem; margin-top:0.5rem;">Veuillez traiter des documents pour générer des visualisations</p>
                </div>
                """, unsafe_allow_html=True)
        
        with tab_images:
            st.markdown("""
            <div class="section-header">
                <span>🖼️ Images traitées</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Ensure we have the images from session state
            images = st.session_state.processed_data.get('images', [])
            
            if images:
                # Create responsive grid with 3 columns
                cols = st.columns(3)
                for idx, img_data in enumerate(images):
                    with cols[idx % 3]:
                        # Display image directly
                        st.image(img_data['image'], use_container_width=True)
                        
                        # Customize display based on image type
                        type_display = img_data.get('type', 'Inconnu')
                        if type_display in ['Non classifié', 'Erreur de classification', 'Erreur de traitement']:
                            type_display = f"{type_display} ⚠️"
                        else:
                            type_display = f"{type_display} ✅"
                        
                        # Metadata display
                        st.markdown(
                            f"""
                            **Type:** {type_display}  
                            **Numéro de série:** {img_data.get('serial', 'N/A')}  
                            **Date:** {img_data.get('date', 'N/A')}
                            """,
                            unsafe_allow_html=True
                        )
            else:
                st.info("Aucune image n'a été traitée")

    with tab3:
        # Import datetime at the top level of the tab3 block
        
        # Header section
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h1>📋 vs 📑 Comparaison des Documents</h1>
            <p style="color: #6c757d; font-size: 1.1rem;">Vérification de cohérence entre les différentes sources de données</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Information box
        st.info("""
        Cette section compare les informations entre les documents de référence (RVD), 
        les données de l'appareil (AED) et les images. Le système vérifie automatiquement la cohérence 
        des données critiques pour garantir la conformité du dispositif.
        """)
        st.markdown("---")  # Separator
        
        # Define helper function for validation check
        def check_matches(section_data):
            if not section_data:
                return True, []
                
            all_matched = True
            failed_items = []
            
            for key, value in section_data.items():
                if isinstance(value, dict):
                    # Check direct match flags
                    match_keys = [k for k in value.keys() if k.startswith('match_')]
                    
                    if match_keys:
                        for match_key in match_keys:
                            if not value.get(match_key, False):
                                all_matched = False
                                source_type = match_key.replace('match_', '')
                                failed_items.append((key, source_type))
                    
                    # Check nested structures (like adultes/pediatriques)
                    if key in ['adultes', 'pediatriques']:
                        nested_matched, nested_failed = check_matches(value)
                        if not nested_matched:
                            all_matched = False
                            # Prefix the nested failures with the parent key
                            failed_items.extend([(f"{key} - {item[0]}", item[1]) for item in nested_failed])
            
            return all_matched, failed_items
        
        # Error display section
        if "errors" in aed_data:
            st.subheader("Journal des Erreurs")
                                
            # Get error headers from metadata or use defaults
            error_header = aed_data.get("Rapport DAE - Erreurs en cours", "Date/Heure,Code Erreur")
            headers = [h.strip() for h in error_header.split(",")]
                                
            # Create error cards
            for error in aed_data["errors"]:
                cols = st.columns([2, 1])
                with cols[0]:
                    st.markdown(f"""
                                    <div class="error-time">
                                    🕒 {error[0]}
                                    </div>
                            """, unsafe_allow_html=True)
                with cols[1]:
                    st.markdown(f"""
                                    <div class="error-code">
                                        ⚠️ {error[1]}
                                        </div>
                                    """, unsafe_allow_html=True)
        st.markdown("---")  # Separator
        
        # Consumables changes section
        st.subheader("Changements de Consommables")
        
        # Add an expander for the consumables comparisons
        with st.expander("Comparaison des Changements de Consommables", expanded=True):
            changement = ["Changement batterie", "Changement électrodes adultes", "Changement électrodes pédiatriques"]
            
            # Create a table for consumables comparison
            cols = st.columns([3, 1.5, 1.5, 1])
            cols[0].markdown("**Consommable**")
            cols[1].markdown("**RVD**")
            cols[2].markdown("**AED**")
            cols[3].markdown("**Correspondance**")
            
            for item in changement:
                cols = st.columns([3, 1.5, 1.5, 1])
                cols[0].write(item)
                
                # RVD data
                rvd_value = rvd_data.get(item, "Non")
                cols[1].write(rvd_value)
                
                # AED data (assuming it's in a format like this - adjust as needed)
                aed_value = aed_data.get(f"{item}", "Non")
                cols[2].write(aed_value)
                
                # Check match and display indicator
                if rvd_value == aed_value:
                    cols[3].markdown("✅")
                else:
                    cols[3].markdown("❌")
            
            # Add a button to edit the consumables data if there's a mismatch
            if st.button("Corriger les données de consommables"):
                st.session_state['edit_consumables'] = True
            
            # Show edit form if button was clicked
            if st.session_state.get('edit_consumables', False):
                st.markdown("### Modifier les données de consommables")
                
                # Create an edit form
                with st.form("edit_consumables_form"):
                    edited_values = {}
                    for item in changement:
                        rvd_value = rvd_data.get(item, "Non")
                        aed_value = aed_data.get(f"{item}", "Non")
                        
                        st.markdown(f"**{item}**")
                        cols = st.columns(2)
                        edited_values[f"rvd_{item}"] = cols[0].selectbox(
                            f"RVD: {item}", 
                            options=["Oui", "Non"], 
                            index=0 if rvd_value == "Oui" else 1,
                            key=f"rvd_{item}"
                        )
                        edited_values[f"aed_{item}"] = cols[1].selectbox(
                            f"AED: {item}", 
                            options=["Oui", "Non"], 
                            index=0 if aed_value == "Oui" else 1,
                            key=f"aed_{item}"
                        )
                    
                    submit = st.form_submit_button("Enregistrer les modifications")
                    if submit:
                        # Here you would update your data structures with the edited values
                        # This is a placeholder for where you'd implement the update logic
                        st.success("Modifications enregistrées avec succès!")
                        # Reset the edit flag
                        st.session_state['edit_consumables'] = False
        
        # Simple display of consumables status
        for i in changement:
            if rvd_data.get(i) == "Oui":
                st.warning(f"{i} a été effectuée ⚠️")
            else:
                st.success(f"Aucun {i} n'est effectuée.")
        
        st.markdown("---")  # Separator
        
        # Run comparison and display dashboard
        comparison_results = compare_data()
        
        # Add consumables comparison to the overall comparison results
        consumables_comparison = {}
        changement = ["Changement batterie", "Changement électrodes adultes", "Changement électrodes pédiatriques"]
        for item in changement:
            rvd_value = rvd_data.get(item, "Non")
            aed_value = aed_data.get(f"{item}", "Non")
            consumables_comparison[item] = {
                "rvd": rvd_value,
                "aed": aed_value,
                "match_rvd_aed": rvd_value == aed_value
            }
        
        comparison_results["Consommables"] = consumables_comparison
        
        display_comparison_dashboard(comparison_results)
        
        # Summary section
        st.markdown("## 📊 Résumé de la Validation")
        
        # Process all sections for validation
        all_matches = True
        all_failed_items = []
        
        for section_name, section_data in comparison_results.items():
            section_matches, section_failed = check_matches(section_data)
            if not section_matches:
                all_matches = False
                # Add section name to failed items
                all_failed_items.extend([(f"{section_name} - {item[0]}", item[1]) for item in section_failed])
        
        # Display summary with visual elements
        if all_matches:
            st.markdown("""
            <div style="background-color: #d4edda; border-radius: 10px; padding: 2rem; text-align: center; 
                    margin-top: 2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <h2 style="color: #155724; margin-bottom: 1rem;">✅ Validation Réussie</h2>
                <p style="color: #155724; font-size: 1.1rem;">
                    Tous les contrôles sont réussis ! La maintenance est conforme aux spécifications.
                </p>
                <div style="font-size: 3rem; margin: 1rem 0;">🎉</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Create a more structured failed validation summary
            st.markdown("""
            <div style="background-color: #f8d7da; border-radius: 10px; padding: 2rem; 
                    margin-top: 2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <h2 style="color: #721c24; margin-bottom: 1rem; text-align: center;">❌ Échec de Validation</h2>
                <p style="color: #721c24; font-size: 1.1rem; text-align: center;">
                    Des incohérences ont été détectées entre les différentes sources de données
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Group failed items by section for better organization
            failed_by_section = {}
            for item, source_type in all_failed_items:
                section_parts = item.split(' - ', 1)
                section = section_parts[0]
                field = section_parts[1] if len(section_parts) > 1 else ""
                
                if section not in failed_by_section:
                    failed_by_section[section] = []
                    
                failed_by_section[section].append((field, source_type))
            
            # Display failed items in an organized, expandable format
            for section, failures in failed_by_section.items():
                with st.expander(f"🔍 Problèmes dans la section: {section}", expanded=True):
                    for field, source_type in failures:
                        source_labels = {
                            'rvd_aed': 'RVD vs AED',
                            'rvd_image': 'RVD vs Image',
                            'releve_aed': 'Relevé vs AED',
                            'releve_image': 'Relevé vs Image'
                        }
                        
                        source_label = source_labels.get(source_type, source_type)
                        field_display = field.replace('_', ' ').title()
                        
                        st.markdown(f"""
                        <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; 
                                padding: 0.75rem; margin-bottom: 0.5rem;">
                            <p style="margin: 0; color: #856404;">
                                <strong>{field_display}</strong>: Incohérence détectée entre {source_label}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
            
            # Add action items for the user
            st.markdown("""
            <div style="background-color: #e2e3e5; border-radius: 5px; padding: 1rem; margin-top: 1.5rem;">
                <h3 style="color: #383d41; margin-top: 0;">Actions recommandées:</h3>
                <ul style="color: #383d41;">
                    <li>Vérifiez les données dans le Rapport de vérification (RVD)</li>
                    <li>Assurez-vous que les informations de l'appareil (AED) sont correctement enregistrées</li>
                    <li>Vérifiez la qualité et la lisibilité des images capturées</li>
                    <li>Corrigez les erreurs identifiées et relancez la comparaison</li>
                    <li>Valider le rapport dans Zoho </li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        # Timestamp and signature
        st.markdown(f"""
        <div style="text-align: right; margin-top: 2rem; color: #6c757d; font-size: 0.8rem;">
            Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}
        </div>
        """, unsafe_allow_html=True)
        
    with tab4:
        st.title("📤 Export automatisé")
        
        with st.container():
            col_config, col_preview = st.columns([1, 2])
        
            with col_config:
                with st.form("export_config"):
                    st.markdown("#### ⚙️ Paramètres d'export")
                    include_images = st.checkbox("Inclure les images", True)
                    st.markdown("---")
                    
                    if st.form_submit_button("Générer un package d'export"):
                        if not st.session_state.get('processed_data', {}).get('RVD'):
                            st.warning("Aucune donnée RVD disponible pour le nommage")
                            st.stop()
                        try:
                            code_site = st.session_state.processed_data['RVD'].get('Code du site', 'INCONNU')
                            date_str = datetime.now().strftime("%Y%m%d")
                            
                            with tempfile.TemporaryDirectory() as temp_dir:
                                exported_files = []
                                
                                if 'uploaded_files' in st.session_state:
                                    for file in st.session_state.uploaded_files:
                                        file_extension = os.path.splitext(file.name)[1]
                                        
                                        if file.type == "application/pdf":
                                            file_name = f"LCC_{code_site}_RVD_{date_str}.pdf" if 'rapport de vérification' in file.name.lower() else f"LCC_{st.session_state.dae_type}_{code_site}_AEDR{date_str}.pdf"
                                        
                                        elif include_images and file.type.startswith("image/"):
                                            clean_name = ''.join(c if c.isalnum() or c in ['.', '_', '-'] else '_' for c in file.name)
                                            file_name = f"LCC_{code_site}_{date_str}_{clean_name}"
                                        
                                        else:
                                            continue
                                        
                                        file_path = os.path.join(temp_dir, file_name)
                                        with open(file_path, "wb") as f:
                                            f.write(file.getvalue())
                                        exported_files.append(file_name)
                                
                                if exported_files:
                                    zip_filename = f"LCC_{code_site}_Entretien_{date_str}.zip"
                                    zip_path = os.path.join(temp_dir, zip_filename)
                                    
                                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                                        for file in exported_files:
                                            zipf.write(os.path.join(temp_dir, file), arcname=file)
                                    
                                    with open(zip_path, "rb") as f:
                                        st.session_state.zip_data = f.read()
                                        
                                    st.session_state.zip_filename = zip_filename
                                    st.success(f"Package d'export généré avec succès ({len(exported_files)} fichiers)")
                        except Exception as e:
                            st.error(f"Erreur lors de la génération du package: {str(e)}")
            
            with col_preview:
                st.markdown("#### 👁️ Aperçu des fichiers")
                
                if 'uploaded_files' in st.session_state and st.session_state.uploaded_files:
                    file_list = []
                    pdf_count, image_count = 0, 0
                    
                    for file in st.session_state.uploaded_files:
                        if file.type == "application/pdf":
                            file_type = "📄 PDF"
                            pdf_count += 1
                        elif file.type.startswith("image/"):
                            file_type = "🖼️ Image"
                            image_count += 1
                        else:
                            file_type = "📁 Autre"
                        
                        file_list.append({
                            "Type": file_type,
                            "Nom original": file.name,
                            "Taille": f"{len(file.getvalue()) / 1024:.1f} KB"
                        })
                    
                    st.markdown(f"""
                    **Résumé des fichiers :**
                    - Total: {len(file_list)} fichier(s)
                    - PDF: {pdf_count} fichier(s)
                    - Images: {image_count} fichier(s)
                    """)
                    
                    st.dataframe(file_list, hide_index=True)
                    
                    if 'zip_data' in st.session_state and 'zip_filename' in st.session_state:
                        st.download_button(
                            label="⬇️ Télécharger le package",
                            data=st.session_state.zip_data,
                            file_name=st.session_state.zip_filename,
                            mime="application/zip"
                        )
                else:
                    st.markdown("""
                        <div style="opacity:0.5; text-align:center; padding:2rem; border:1px dashed #ccc; border-radius:5px;">
                            ⚠️ Aucun fichier uploadé
                        </div>
                    """, unsafe_allow_html=True)

