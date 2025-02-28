"""Streamlit UI components for the Comparateur_PDF project."""

import json
import os
from datetime import datetime
from tkinter import Tk, filedialog
import zipfile
from typing import Dict, Any
import streamlit as st
from .config import ALLOWED_EXTENSIONS, CSS_STYLE
from .processing import process_uploaded_file
from .comparison import compare_data

def display_comparison_row(left_label: str, left_value: str, right_label: str, 
                          right_value: str, match_key: str, data: dict) -> None:
    """Display a comparison row with two values and match indicator.
    
    Args:
        left_label: Label for the left column
        left_value: Value for the left column
        right_label: Label for the right column
        right_value: Value for the right column
        match_key: Key to check in data for match status
        data: The comparison data dict
    """
    cols = st.columns([3, 2, 2, 1])
    cols[0].markdown("")
    cols[1].markdown(f"*{left_label}:*  \n`{left_value}`")
    cols[2].markdown(f"*{right_label}:*  \n`{right_value}`")
    
    # Handle different match key formats
    match = data.get(match_key, False)
    if match:
        cols[3].success("✅")
    else:
        cols[3].error("❌")

def display_field_data(field_name: str, data: dict, indent: int = 0) -> None:
    """Display data for a specific field with all data sources in one line.
    
    Args:
        field_name: Name of the field
        data: Comparison data for the field
        indent: Indentation level for nested fields
    """
    with st.container():
        # Header with field name
        indentation = "→ " * indent
        display_name = field_name.replace('_', ' ').title()
        st.markdown(f"**{indentation}{display_name}**")
        
        # Define data sources with labels and access keys
        data_sources = {
            "RVD Original": {'key': 'rvd_original', 'icon': '📄'},
            "RVD Relevé": {'key': 'rvd_releve', 'icon': '📋'},
            "AED": {'key': 'aed', 'icon': '🔌'},
            "Image": {'key': 'image', 'icon': '📷'}
        }
        
        # Extract values and count valid ones
        values = {}
        valid_values = 0
        for label, source_info in data_sources.items():
            value = data.get(source_info['key'], 'N/A')
            values[label] = {'value': value, 'icon': source_info['icon']}
            if value != 'N/A' and value is not None:
                valid_values += 1
        
        if valid_values >= 2:
            # Create a single row with all values
            cols = st.columns([2, 2, 2, 2, 2])
            
            # Display field name with tooltip for technical details
            cols[0].markdown(
                f"<span title='Field technical name: {field_name}'>*Field:*  \n`{display_name}`</span>",
                unsafe_allow_html=True
            )
            
            # Display each value with its label and icon
            for i, (label, info) in enumerate(values.items(), 1):
                if i < len(cols):
                    if info['value'] != 'N/A' and info['value'] is not None:
                        cols[i].markdown(f"*{info['icon']} {label}:*  \n`{info['value']}`")
                    else:
                        cols[i].markdown(f"*{info['icon']} {label}:*  \n`-`")
            
            # Calculate and display match status with improved visuals
            match_keys = [k for k in data.keys() if k.startswith('match_')]
            matches = sum(1 for k in match_keys if data.get(k, False))
            
            # Only display if there are match keys
            if match_keys:
                match_percentage = (matches / len(match_keys)) * 100
                
                # Create color gradient based on match percentage
                color = get_match_color(match_percentage)
                
                status_text = f"Match: {matches}/{len(match_keys)} ({match_percentage:.0f}%)"
                
                # Use a progress bar to show match percentage
                st.progress(match_percentage / 100)
                
                # Add a status indicator with appropriate styling
                if matches == len(match_keys):
                    st.success(f"✅ {status_text}")
                elif match_percentage >= 50:
                    st.warning(f"⚠️ {status_text}")
                else:
                    st.error(f"❌ {status_text}")
        
        # Display errors with more detailed formatting
        if 'errors' in data and data['errors']:
            with st.expander("⚠️ Erreurs détectées", expanded=True):
                for err in data['errors']:
                    st.error(f"• {err}")
        
        if 'error' in data and data['error']:
            st.error(f"🚫 Erreur critique: {data['error']}")

def get_match_color(percentage: float) -> str:
    """Generate a color on a gradient from red to green based on percentage.
    
    Args:
        percentage: Match percentage (0-100)
        
    Returns:
        Hex color code
    """
    if percentage <= 50:
        # Red to yellow gradient for 0-50%
        r = 255
        g = int((percentage / 50) * 255)
        b = 0
    else:
        # Yellow to green gradient for 50-100%
        r = int(255 - ((percentage - 50) / 50) * 255)
        g = 255
        b = 0
    
    return f"#{r:02x}{g:02x}{b:02x}"

def display_section_comparison(title: str, section_data: Dict[str, Dict]) -> None:
    """Display comparison results for a specific equipment section with relevé data.

    Args:
        title: Title of the section.
        section_data: Comparison data for the section.
    """
    if not section_data:
        return
    
    st.subheader(title)
    st.markdown("---")
    
    # Calculate overall match status for the section
    total_comparisons = 0
    successful_matches = 0
    
    for field, data in section_data.items():
        if isinstance(data, dict):
            # Check if it's a nested structure (like electrodes)
            if field in ['adultes', 'pediatriques']:
                if data:  # Only display if there's data
                    st.markdown(f"### {field.title()}")
                    for subfield, subdata in data.items():
                        display_field_data(subfield, subdata, indent=1)
                        
                        # Count matches for statistics
                        match_keys = [k for k in subdata.keys() if k.startswith('match_')]
                        total_comparisons += len(match_keys)
                        successful_matches += sum(1 for k in match_keys if subdata.get(k, False))
                        
                        st.markdown("---")
            else:
                display_field_data(field, data)
                
                # Count matches for statistics
                match_keys = [k for k in data.keys() if k.startswith('match_')]
                total_comparisons += len(match_keys)
                successful_matches += sum(1 for k in match_keys if data.get(k, False))
                
                st.markdown("---")
    
    # Display overall status
    if total_comparisons > 0:
        match_percentage = (successful_matches / total_comparisons) * 100
        st.metric(
            label=f"Correspondance globale pour {title}", 
            value=f"{match_percentage:.1f}%",
            delta=None
        )
        
        # Color-coded status message
        if match_percentage == 100:
            st.success("✅ Toutes les données correspondent parfaitement!")
        elif match_percentage >= 75:
            st.warning(f"⚠️ {successful_matches} correspondances sur {total_comparisons} vérifications")
        else:
            st.error(f"❌ Seulement {successful_matches} correspondances sur {total_comparisons} vérifications")


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
            <div class="header">
                <div style="display: flex; align-items: center; gap: 2rem;">
                    <img src="https://www.locacoeur.com/wp-content/uploads/2020/04/Locacoeur_Logo.png" width="120">
                    <div>
                        <h1 style="margin: 0; font-size: 2.5rem;">
                            Système d'inspection des dispositifs médicaux
                        </h1>
                        <p style="opacity: 0.9; margin: 0.5rem 0 0;">
                            v2.1.0 | Plateforme d'analyse intelligente
                        </p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with st.sidebar:
        st.markdown("### ⚙️ Paramètres de configuration")
        st.markdown("---")
        st.subheader("📱 Configuration du dispositif")
        st.session_state.dae_type = st.radio(
            "Type d'AED",
            ("G5", "G3"),
            index=0,
            help="Sélectionnez le type de dispositif à inspecter"
        )
        st.subheader("🔧 Options de traitement")
        st.session_state.enable_ocr = st.checkbox(
            "Activer l'OCR",
            True,
            help="Active la reconnaissance de texte sur les images"
        )
        st.session_state.auto_classify = st.checkbox(
            "Classification automatique",
            True,
            help="Active la classification automatique des documents"
        )
        st.markdown("---")
        st.markdown("#### 🔍 Guide d'utilisation")
        with st.expander("Comment utiliser l'application ?", expanded=False):
            st.markdown("""
                1. **Préparation** 📋  
                   - Vérifiez que vos documents sont au format requis  
                   - Assurez-vous que les images sont nettes  
                2. **Téléversement** 📤  
                   - Glissez-déposez vos fichiers  
                   - Attendez le traitement complet  
                3. **Vérification** ✅  
                   - Examinez les données extraites  
                   - Validez les résultats  
                4. **Export** 📥  
                   - Choisissez le format d'export  
                   - Téléchargez vos résultats
            """)
        st.markdown("---")
        st.caption("Développé par Locacoeur • [Support technique](mailto:support@locacoeur.com)")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Téléversement des documents",
        "📊 Analyse approfondie",
        "📋vs📋 Comparaison des documents",
        "📤 Export automatisé"
    ])

    with tab1:
        st.title("📋 Téléversement des documents")
        st.markdown("---")
        with st.expander("Téléverser des documents", expanded=True):
            uploaded_files = st.file_uploader(
                "Glissez et déposez des fichiers ici",
                type=ALLOWED_EXTENSIONS,
                accept_multiple_files=True,
                help="Téléverser des rapports PDF et des images de dispositifs"
            )
            if uploaded_files:
                with st.container() as processing_container:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    error_container = st.empty()
                    total_files = len(uploaded_files)

                    for i, uploaded_file in enumerate(uploaded_files):
                        try:
                            process_uploaded_file(
                                uploaded_file, progress_bar, status_text,
                                error_container, i, total_files, client, reader
                            )
                        except ValueError as e:
                            error_container.error(
                                f"Erreur de valeur lors du traitement de {uploaded_file.name} : {e}"
                            )

                    st.session_state.uploaded_files = uploaded_files
                    st.success(f"Traitement terminé pour tous les {total_files} fichiers.")

    with tab2:
        st.markdown("""
        <div style="padding: 10px 0; margin-bottom: 20px;">
            <h1 style="margin: 0; font-size: 2rem;">📊 Analyse des données traitées</h1>
            <p style="opacity: 0.8;">Visualisation des données extraites des documents</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("Données extraites", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Données RVD")
                if st.session_state.processed_data['RVD']:
                    st.json(st.session_state.processed_data['RVD'], expanded=False)
                else:
                    st.info("Aucune donnée RVD n'a été traitée.")
            
            with col2:
                st.subheader(f"Données AED {st.session_state.dae_type}")
                aed_type = f'AEDG{st.session_state.dae_type[-1]}'
                aed_data = st.session_state.processed_data.get(aed_type, {})
                if aed_data:
                    st.json(aed_data, expanded=False)
                else:
                    st.info("Aucune donnée AED n'a été trouvée.")
        
        if st.session_state.processed_data['images']:
            with st.expander("Résultats d'analyse d'images", expanded=True):
                st.markdown("### Images traitées")
                cols = st.columns(3)
                for idx, img_data in enumerate(st.session_state.processed_data['images']):
                    with cols[idx % 3]:
                        st.markdown(f"""
                        <div class="image-card">
                        """, unsafe_allow_html=True)
                        st.image(img_data['image'], use_container_width=True)
                        
                        type_display = img_data['type']
                        status_icon = "✅"
                        if type_display in ['Non classifié', 'Erreur de classification', 'Erreur de traitement']:
                            status_icon = "⚠️"
                        
                        st.markdown(
                            f"""
                            <div style="padding: 10px 5px;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                    <strong style="font-size: 16px;">{type_display}</strong>
                                    <span style="font-size: 18px;">{status_icon}</span>
                                </div>
                                <div style="font-size: 14px; margin-bottom: 5px;">
                                    <strong>Numéro de série:</strong> {img_data.get('serial', 'N/D')}
                                </div>
                                <div style="font-size: 14px;">
                                    <strong>Date:</strong> {img_data.get('date', 'N/D')}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Aucune image traitée à afficher pour le moment.")

    with tab3:
        st.title("📋vs📑 Comparaison des documents")
        with st.expander("Comparaison des documents", expanded=True):
            # Run comparison and get results organized by equipment sections
            comparison_results = compare_data()
            
            # Display results by equipment section
            display_section_comparison("Défibrillateur", comparison_results.get('defibrillateur', {}))
            display_section_comparison("Batterie", comparison_results.get('batterie', {}))
            display_section_comparison("Électrodes", comparison_results.get('electrodes', {}))
            
            # Check if all matches are successful
            def check_matches(section_data):
                for key, value in section_data.items():
                    if isinstance(value, dict):
                        if 'match' in value and not value.get('match', False):
                            return False
                        if 'match_rvd_aed' in value and not value.get('match_rvd_aed', False):
                            return False
                        if 'match_rvd_image' in value and not value.get('match_rvd_image', False):
                            return False
                        if key in ['adultes', 'pediatriques']:
                            if not check_matches(value):
                                return False
                return True
            
            all_matches = all(
                check_matches(section_data)
                for section_name, section_data in comparison_results.items()
            )
            
            if all_matches:
                st.success("Tous les contrôles sont réussis ! Le dispositif est conforme.")
            else:
                # Collect failed checks
                failed = []
                for section_name, section_data in comparison_results.items():
                    for field, data in section_data.items():
                        if isinstance(data, dict):
                            if 'match' in data and not data.get('match', False):
                                failed.append(f"{section_name} - {field}")
                            if 'match_rvd_aed' in data and not data.get('match_rvd_aed', False):
                                failed.append(f"{section_name} - {field} (RVD vs AED)")
                            if 'match_rvd_image' in data and not data.get('match_rvd_image', False):
                                failed.append(f"{section_name} - {field} (RVD vs Image)")
                            if field in ['adultes', 'pediatriques']:
                                for subfield, subdata in data.items():
                                    if 'match' in subdata and not subdata.get('match', False):
                                        failed.append(f"{section_name} - {field} - {subfield}")
                
                st.error(f"Échec de validation pour : {', '.join(failed)}")

            

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
                            code_site = st.session_state.processed_data['RVD'].get('Code site', 'INCONNU')
                            date_str = datetime.now().strftime("%Y%m%d")
                            
                            # Process PDF files
                            if 'uploaded_files' in st.session_state:
                                for file in st.session_state.uploaded_files:
                                    if file.type == "application/pdf":
                                        # Generate default name
                                        if 'rapport de vérification' in file.name.lower():
                                            default_name = f"RVD_{code_site}_{date_str}.pdf"
                                        else:
                                            default_name = f"AED_{st.session_state.dae_type}_{code_site}_{date_str}.pdf"
                                        
                                        # Open save dialog
                                        save_path = save_file_dialog(default_name)
                                        
                                        if save_path:  # If user didn't cancel
                                            with open(save_path, "wb") as f:
                                                f.write(file.getvalue())
                                            st.success(f"Fichier enregistré : {os.path.basename(save_path)}")
                                    
                                    # Process images if included
                                    if include_images and file.type.startswith("image/"):
                                        default_name = f"IMAGE_{code_site}_{date_str}_{file.name}"
                                        save_path = save_file_dialog(default_name)
                                        
                                        if save_path:  # If user didn't cancel
                                            with open(save_path, "wb") as f:
                                                f.write(file.getvalue())
                                            st.success(f"Image enregistrée : {os.path.basename(save_path)}")

                        except Exception as e:
                            st.error(f"Erreur lors de l'enregistrement : {str(e)}")

            with col_preview:
                st.markdown("#### 👁️ Aperçu des fichiers")
                if 'uploaded_files' in st.session_state:
                    file_list = []
                    for file in st.session_state.uploaded_files:
                        file_type = "PDF" if file.type == "application/pdf" else "Image"
                        file_list.append({
                            "Type": file_type,
                            "Nom original": file.name,
                            "Taille": f"{len(file.getvalue()) / 1024:.1f} KB"
                        })
                    
                    if file_list:
                        st.table(file_list)
                    else:
                        st.info("Aucun fichier disponible pour l'export")
                else:
                    st.markdown("""
                        <div style="opacity:0.5; text-align:center; padding:2rem;">
                            ⚠️ Aucun fichier uploadé
                        </div>
                    """, unsafe_allow_html=True)
