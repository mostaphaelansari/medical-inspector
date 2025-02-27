"""Streamlit UI components for the Comparateur_PDF project."""

import json
import os
from datetime import datetime
import zipfile
from typing import Dict, Any, List, Tuple
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from .config import ALLOWED_EXTENSIONS, CSS_STYLE
from .processing import process_uploaded_file
from .comparison import compare_data

def display_section_comparison(title: str, section_data: Dict[str, Dict]) -> None:
    """Display comparison results for a specific equipment section with enhanced UI.

    Args:
        title: Title of the section.
        section_data: Comparison data for the section.
    """
    if not section_data:
        return
    
    st.markdown(f"""
        <div class="section-header">
            <h2>{title}</h2>
        </div>
    """, unsafe_allow_html=True)
    
    # Count total checks and successful checks
    total_checks, success_checks = count_section_checks(section_data)
    success_rate = int((success_checks / total_checks * 100) if total_checks > 0 else 0)
    
    # Enhanced summary section with card layout
    st.markdown("""
    <div class="summary-container">
        <h3>Résumé de la section</h3>
        <div class="metrics-grid">
            <div class="metric-card">
                <h4>Points vérifiés</h4>
                <p>{}</p>
            </div>
            <div class="metric-card">
                <h4>Points conformes</h4>
                <p>{}</p>
            </div>
            <div class="metric-card">
                <h4>Taux de conformité</h4>
                <p>{}%</p>
            </div>
        </div>
    </div>
    """.format(total_checks, success_checks, success_rate), unsafe_allow_html=True)
    
    # Prepare comparison rows
    data_rows = []
    for field, data in section_data.items():
        if isinstance(data, dict) and 'match_rvd_aed' in data:
            row = create_comparison_row(field, data, 'rvd', 'aed', 'match_rvd_aed')
            data_rows.append(row)
            if 'image' in data:
                image_row = create_comparison_row(f"{field} (Image)", data, 'rvd', 'image', 'match_rvd_image')
                data_rows.append(image_row)
        elif isinstance(data, dict) and ('match' in data):
            compare_type = 'aed' if 'aed' in data else 'image'
            row = create_comparison_row(field, data, 'rvd', compare_type, 'match')
            data_rows.append(row)
        elif field == 'adultes' or field == 'pediatriques':
            for subfield, subdata in data.items():
                compare_type = 'aed' if 'aed' in subdata else 'image'
                row = create_comparison_row(f"{field.title()} - {subfield}", subdata, 'rvd', compare_type, 'match')
                data_rows.append(row)
    
    # Add filter for mismatches
    show_only_mismatches = st.checkbox(f"Afficher uniquement les non-conformités pour {title}", value=False, key=f"mismatch_{title}")
    filtered_rows = [row for row in data_rows if not show_only_mismatches or not row['match']]
    
    # Display the enhanced comparison table
    display_comparison_table(filtered_rows)

def count_section_checks(section_data: Dict) -> Tuple[int, int]:
    """Count total checks and successful checks in a section."""
    total_checks = 0
    success_checks = 0
    for field, data in section_data.items():
        if isinstance(data, dict):
            if 'match_rvd_aed' in data:
                total_checks += 1
                if data.get('match_rvd_aed', False):
                    success_checks += 1
            if 'match_rvd_image' in data:
                total_checks += 1
                if data.get('match_rvd_image', False):
                    success_checks += 1
            if 'match' in data:
                total_checks += 1
                if data.get('match', False):
                    success_checks += 1
            if field in ['adultes', 'pediatriques']:
                for subfield, subdata in data.items():
                    if 'match' in subdata:
                        total_checks += 1
                        if subdata.get('match', False):
                            success_checks += 1
    return total_checks, success_checks

def create_comparison_row(field: str, data: Dict, source1: str, source2: str, match_key: str) -> Dict:
    """Create a comparison row for the data table."""
    return {
        "field": field.replace('_', ' ').title(),
        "value1": str(data.get(source1, 'N/A')),
        "value2": str(data.get(source2, 'N/A')),
        "source1": source1.upper(),
        "source2": source2.upper(),
        "match": data.get(match_key, False),
        "errors": data.get('errors', []) if 'errors' in data else [data.get('error')] if 'error' in data else []
    }

import pandas as pd
import streamlit as st
from typing import List, Dict

def display_comparison_table(data_rows: List[Dict]) -> None:
    """
    Display a comparison table in Streamlit using a styled pandas DataFrame.
    
    Args:
        data_rows: List of dictionaries with keys like 'field', 'value1', 'value2', 
                  'source2', 'match', and optionally 'errors'.
    """
    # Convert the list of dictionaries to a DataFrame
    df = pd.DataFrame(data_rows)

    # Rename columns to match your desired headers
    df = df.rename(columns={
        'field': 'Paramètre',
        'value1': 'RVD',
        'value2': 'Valeur comparée',
        'source2': 'Source',
        'match': 'Résultat'
    })

    # Handle errors if they exist in the data
    if 'errors' in df.columns:
        df['Erreurs'] = df['errors'].apply(lambda x: ', '.join(x) if x else '')
    else:
        df['Erreurs'] = ''

    # Format the 'Résultat' column with icons and text
    df['Résultat'] = df['Résultat'].apply(lambda x: '✅ Conforme' if x else '❌ Non conforme')

    # Define a styling function for the 'Résultat' column
    def style_result(val):
        if 'Conforme' in val:
            return 'background-color: #d4edda; color: #155724;'  # Light green background, dark green text
        else:
            return 'background-color: #f8d7da; color: #721c24;'  # Light red background, dark red text

    # Apply the styling to the DataFrame
    styled_df = df.style.applymap(style_result, subset=['Résultat'])

    # Display the styled DataFrame in Streamlit
    st.dataframe(styled_df, use_container_width=True)

def display_overall_compliance_summary(comparison_results: Dict) -> None:
    """Display an overall compliance summary with enhanced visualization."""
    total_all = 0
    success_all = 0
    section_stats = {}
    
    for section_name, section_data in comparison_results.items():
        total, success = count_section_checks(section_data)
        section_stats[section_name.title()] = {
            "total": total,
            "success": success,
            "rate": (success / total * 100) if total > 0 else 0
        }
        total_all += total
        success_all += success
    
    overall_rate = (success_all / total_all * 100) if total_all > 0 else 0
    
    st.markdown("""
    <div style="background-color: #f8f9fa; border-radius: 10px; padding: 15px; margin-bottom: 20px;">
        <h2 style="margin-top: 0;">Récapitulatif de conformité</h2>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Points vérifiés", total_all)
    with col2:
        st.metric("Points conformes", success_all, delta=f"{success_all-total_all}" if success_all < total_all else None)
    with col3:
        st.metric("Conformité globale", f"{overall_rate:.1f}%")
    
    # Pie chart for overall compliance
    fig = go.Figure(data=[go.Pie(
        labels=['Conforme', 'Non conforme'],
        values=[success_all, total_all - success_all],
        hole=0.4,
        marker_colors=['#28a745', '#dc3545']
    )])
    fig.update_layout(
        title='Répartition de la conformité',
        height=300,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Section compliance bars
    st.markdown("### Conformité par section")
    bars_html = ""
    for section, stats in section_stats.items():
        rate = stats["rate"]
        color = get_color_for_rate(rate)
        bars_html += f"""
        <div style="margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span style="font-weight: 600;">{section}</span>
                <span>{stats['success']}/{stats['total']} ({rate:.1f}%)</span>
            </div>
            <div style="background-color: #e9ecef; border-radius: 5px; height: 20px; width: 100%;">
                <div style="background-color: {color}; width: {rate}%; height: 100%; border-radius: 5px;"></div>
            </div>
        </div>
        """
    st.markdown(bars_html, unsafe_allow_html=True)
    
    # Overall result and failed checks
    if success_all == total_all:
        st.success("✅ Tous les contrôles sont réussis ! Le dispositif est conforme.")
    else:
        failed = collect_failed_checks(comparison_results)
        st.warning(f"⚠️ {len(failed)} point(s) de non-conformité détecté(s)")
        if failed:
            st.markdown("### Points de non-conformité")
            for i, item in enumerate(failed):
                st.markdown(f"{i+1}. **{item}**")
    
    # Download CSV button
    if st.button("Télécharger les résultats en CSV"):
        df = generate_comparison_csv(comparison_results)
        csv = df.to_csv(index=False)
        st.download_button(
            label="Télécharger CSV",
            data=csv,
            file_name=f"comparison_results_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

def get_color_for_rate(rate: float) -> str:
    """Get color for compliance rate."""
    if rate >= 90:
        return "#28a745"  # Green
    elif rate >= 75:
        return "#17a2b8"  # Blue
    elif rate >= 50:
        return "#ffc107"  # Yellow
    else:
        return "#dc3545"  # Red

def collect_failed_checks(comparison_results: Dict) -> List[str]:
    """Collect all failed checks."""
    failed = []
    for section_name, section_data in comparison_results.items():
        for field, data in section_data.items():
            if isinstance(data, dict):
                if 'match' in data and not data.get('match', False):
                    compare_type = 'AED' if 'aed' in data else 'Image'
                    failed.append(f"{section_name.title()} - {field.replace('_', ' ').title()} (RVD vs {compare_type})")
                if 'match_rvd_aed' in data and not data.get('match_rvd_aed', False):
                    failed.append(f"{section_name.title()} - {field.replace('_', ' ').title()} (RVD vs AED)")
                if 'match_rvd_image' in data and not data.get('match_rvd_image', False):
                    failed.append(f"{section_name.title()} - {field.replace('_', ' ').title()} (RVD vs Image)")
                if field in ['adultes', 'pediatriques']:
                    for subfield, subdata in data.items():
                        if 'match' in subdata and not subdata.get('match', False):
                            compare_type = 'AED' if 'aed' in subdata else 'Image'
                            failed.append(f"{section_name.title()} - {field.title()} - {subfield.replace('_', ' ').title()} (RVD vs {compare_type})")
    return failed

def generate_comparison_csv(comparison_results: Dict) -> pd.DataFrame:
    """Generate a DataFrame for CSV export from comparison results."""
    data = []
    for section, section_data in comparison_results.items():
        for field, field_data in section_data.items():
            if isinstance(field_data, dict):
                if 'match_rvd_aed' in field_data:
                    data.append({
                        'Section': section,
                        'Field': field,
                        'Source1': 'RVD',
                        'Value1': field_data.get('rvd', 'N/A'),
                        'Source2': 'AED',
                        'Value2': field_data.get('aed', 'N/A'),
                        'Match': 'Conforme' if field_data.get('match_rvd_aed', False) else 'Non conforme',
                        'Errors': ', '.join(field_data.get('errors', []))
                    })
                if 'match_rvd_image' in field_data:
                    data.append({
                        'Section': section,
                        'Field': field,
                        'Source1': 'RVD',
                        'Value1': field_data.get('rvd', 'N/A'),
                        'Source2': 'Image',
                        'Value2': field_data.get('image', 'N/A'),
                        'Match': 'Conforme' if field_data.get('match_rvd_image', False) else 'Non conforme',
                        'Errors': ', '.join(field_data.get('errors', []))
                    })
                if 'match' in field_data and 'aed' in field_data:
                    data.append({
                        'Section': section,
                        'Field': field,
                        'Source1': 'RVD',
                        'Value1': field_data.get('rvd', 'N/A'),
                        'Source2': 'AED',
                        'Value2': field_data.get('aed', 'N/A'),
                        'Match': 'Conforme' if field_data.get('match', False) else 'Non conforme',
                        'Errors': ', '.join(field_data.get('errors', []))
                    })
                elif 'match' in field_data and 'image' in field_data:
                    data.append({
                        'Section': section,
                        'Field': field,
                        'Source1': 'RVD',
                        'Value1': field_data.get('rvd', 'N/A'),
                        'Source2': 'Image',
                        'Value2': field_data.get('image', 'N/A'),
                        'Match': 'Conforme' if field_data.get('match', False) else 'Non conforme',
                        'Errors': ', '.join(field_data.get('errors', []))
                    })
    return pd.DataFrame(data)

def setup_session_state():
    """Initialize session state variables."""
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
    """Display the Streamlit user interface."""
    st.set_page_config(page_title="Inspecteur de dispositifs médicaux", layout="wide")
    
    # Enhanced global CSS
    additional_css = """
    <style>
    .header {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .section-header {
        background: linear-gradient(to right, #f1f3f5, #ffffff);
        padding: 0.8rem;
        border-radius: 5px;
        margin: 1.5rem 0 1rem;
        border-left: 5px solid #0068c9;
    }
    .section-header h2 {
        margin: 0;
        font-size: 1.5rem;
        color: #0a1e42;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 16px;
        border-radius: 4px 4px 0 0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0068c9 !important;
        color: white !important;
    }
    .stMetric {
        background-color: white;
        padding: 0.5rem;
        border-radius: 5px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .image-card {
        background: white;
        border-radius: 8px;
        padding: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 15px;
    }
    .stExpander {
        border: none !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border-radius: 8px !important;
    }
    </style>
    """
    st.markdown(CSS_STYLE + additional_css, unsafe_allow_html=True)
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
        st.markdown("""
        <div style="padding: 10px 0; margin-bottom: 20px;">
            <h1 style="margin: 0; font-size: 2rem;">📋 Téléversement des documents</h1>
            <p style="opacity: 0.8;">Téléversez les fichiers PDF et images pour l'analyse</p>
        </div>
        """, unsafe_allow_html=True)
        
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
        st.markdown("""
        <div style="padding: 10px 0; margin-bottom: 20px;">
            <h1 style="margin: 0; font-size: 2rem;">📋vs📑 Comparaison des documents</h1>
            <p style="opacity: 0.8;">Analyse automatisée des correspondances entre les sources de données</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container():
            comparison_results = compare_data()
            display_overall_compliance_summary(comparison_results)
            st.markdown("---")
            display_section_comparison("Défibrillateur", comparison_results.get('defibrillateur', {}))
            st.markdown("---")
            display_section_comparison("Batterie", comparison_results.get('batterie', {}))
            st.markdown("---")
            display_section_comparison("Électrodes", comparison_results.get('electrodes', {}))

    with tab4:
        st.title("📤 Export automatisé")
        with st.container():
            col_config, col_preview = st.columns([1, 2])
            with col_config:
                with st.form("export_config"):
                    st.markdown("#### ⚙️ Paramètres d'export")
                    export_format = st.selectbox(
                        "Format de sortie",
                        ["ZIP", "PDF", "CSV", "XLSX"],
                        index=0
                    )
                    include_images = st.checkbox("Inclure les images", True)
                    st.markdown("---")
                    with st.expander("Exportation des fichiers", expanded=True):
                        if st.form_submit_button("Générer un package d'export"):
                            if not st.session_state.processed_data.get('RVD'):
                                st.warning("Aucune donnée RVD disponible pour le nommage")
                            else:
                                code_site = st.session_state.processed_data['RVD'].get('Code site', 'INCONNU')
                                date_str = datetime.now().strftime("%Y%m%d")
                                with zipfile.ZipFile('export.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
                                    zipf.writestr(
                                        'donnees_traitees.json',
                                        json.dumps(st.session_state.processed_data, indent=2)
                                    )
                                    
                                    summary = (
                                        "Résumé de l'inspection\n\n"
                                        "Données RVD:\n" +
                                        json.dumps(st.session_state.processed_data['RVD'], indent=2) +
                                        "\n\n" +
                                        f"Données AED {st.session_state.dae_type}:\n" +
                                        json.dumps(st.session_state.processed_data[f'AEDG{st.session_state.dae_type[-1]}'], indent=2) +
                                        "\n\nComparaisons par section:\n"
                                    )
                                    
                                    for section_name, section_data in st.session_state.processed_data['comparisons'].items():
                                        summary += f"\n{section_name.upper()}:\n"
                                        for field, data in section_data.items():
                                            if isinstance(data, dict):
                                                if 'match' in data:
                                                    summary += (
                                                        f"  {field.replace('_', ' ').title()}: "
                                                        f"{'✅' if data.get('match', False) else '❌'}\n"
                                                    )
                                                elif 'match_rvd_aed' in data:
                                                    summary += (
                                                        f"  {field.replace('_', ' ').title()} (RVD vs AED): "
                                                        f"{'✅' if data.get('match_rvd_aed', False) else '❌'}\n"
                                                    )
                                                    if 'match_rvd_image' in data:
                                                        summary += (
                                                            f"  {field.replace('_', ' ').title()} (RVD vs Image): "
                                                            f"{'✅' if data.get('match_rvd_image', False) else '❌'}\n"
                                                        )
                                                elif field in ['adultes', 'pediatriques']:
                                                    summary += f"  {field.title()}:\n"
                                                    for subfield, subdata in data.items():
                                                        if 'match' in subdata:
                                                            summary += (
                                                                f"    {subfield.replace('_', ' ').title()}: "
                                                                f"{'✅' if subdata.get('match', False) else '❌'}\n"
                                                            )
                                    
                                    zipf.writestr("resume.txt", summary)
                                    
                                    if 'uploaded_files' in st.session_state:
                                        for uploaded_file in st.session_state.uploaded_files:
                                            if (
                                                uploaded_file.type == "application/pdf" or
                                                (include_images and uploaded_file.type.startswith("image/"))
                                            ):
                                                original_bytes = uploaded_file.getvalue()
                                                if uploaded_file.type == "application/pdf":
                                                    if 'rapport de vérification' in uploaded_file.name.lower():
                                                        new_name = f"RVD_{code_site}_{date_str}.pdf"
                                                    else:
                                                        new_name = f"AED_{st.session_state.dae_type}_{code_site}_{date_str}.pdf"
                                                else:
                                                    new_name = f"IMAGE_{code_site}_{date_str}_{uploaded_file.name}"
                                                zipf.writestr(new_name, original_bytes)
                                
                                st.session_state.export_ready = True
                                if os.path.exists('export.zip'):
                                    with open("export.zip", "rb") as f:
                                        st.download_button(
                                            label="Télécharger le package d'export",
                                            data=f,
                                            file_name=f"Inspection_{code_site}_{date_str}.zip",
                                            mime="application/zip"
                                        )
            
            with col_preview:
                st.markdown("#### 👁️ Aperçu de l'export")
                if st.session_state.get('export_ready'):
                    st.success("✅ Package prêt pour téléchargement !")
                    preview_data = {
                        "format": export_format,
                        "fichiers_inclus": [
                            "donnees_traitees.json",
                            "resume.txt",
                            *(
                                ["images.zip"]
                                if include_images and any(
                                    f.type.startswith("image/")
                                    for f in st.session_state.get('uploaded_files', [])
                                )
                                else []
                            )
                        ],
                        "taille_estimee": f"{(len(st.session_state.get('uploaded_files', []))*0.5):.1f} Mo"
                    }
                    st.json(preview_data)
                    if os.path.exists('export.zip'):
                        with open("export.zip", "rb") as f:
                            if st.download_button(
                                label="📥 Télécharger l'export complet",
                                data=f,
                                file_name=f"Inspection_{datetime.now().strftime('%Y%m%d')}.zip",
                                mime="application/zip",
                                help="Cliquez pour télécharger le package complet",
                                use_container_width=True,
                                type="primary"
                            ):
                                st.balloons()
                else:
                    st.markdown(
                        """
                        <div style="padding: 2rem; text-align: center; opacity: 0.5;">
                            ⚠️ Aucun export généré
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
