"""Streamlit UI components for the Comparateur_PDF project."""

import json
import os
from datetime import datetime
import zipfile
from typing import Dict
import streamlit as st
from .config import ALLOWED_EXTENSIONS, CSS_STYLE
from .processing import process_uploaded_file
from .comparison import compare_rvd_aed, compare_rvd_images

def display_comparison(title: str, comparison: Dict[str, Dict[str, str]]) -> None:
    """Display comparison results in a formatted way.

    Args:
        title: Title of the comparison.
        comparison: Comparison data.
    """
    if not comparison:
        st.warning("Aucune donnée de comparaison disponible")
        return
    st.subheader(title)
    for field, data in comparison.items():
        with st.container():
            cols = st.columns([3, 2, 2, 1])
            cols[0].markdown(f"**{field.replace('_', ' ').title()}**")
            cols[1].markdown(f"*RVD:*  \n`{data.get('rvd', 'N/A')}`")
            compare_type = 'AED' if 'aed' in data else 'Image'
            compare_value = data.get(compare_type.lower(), 'N/A')
            cols[2].markdown(f"*{compare_type}:*  \n`{compare_value}`")
            if data.get('match', False):
                cols[3].success("✅")
            else:
                cols[3].error("❌")
            if 'errors' in data:
                for err in data['errors']:
                    st.error(err)
            if 'error' in data:
                st.error(data['error'])
        st.markdown("---")

def setup_session_state():
    """Initialize session state variables."""
    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = {
            'RVD': {},
            'AEDG5': {},
            'AEDG3': {},
            'images': [],
            'files': [],
            'comparisons': {'rvd_vs_aed': {}, 'rvd_vs_images': {}}
        }
    if 'dae_type' not in st.session_state:
        st.session_state.dae_type = 'G5'
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = []

def render_ui(client, reader):
    """Render the Streamlit UI."""
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
        st.title("📊 Analyse de données traitées")
        
        # Display processed RVD and AED data
        with st.expander("Données traitées", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Données RVD")
                st.json(st.session_state.processed_data['RVD'], expanded=False)
            with col2:
                st.subheader(f"Données AED {st.session_state.dae_type}")
                aed_type = f'AEDG{st.session_state.dae_type[-1]}'
                aed_data = st.session_state.processed_data.get(aed_type, {})
                st.json(aed_data if aed_data else {"status": "Aucune donnée AED trouvée"}, expanded=False)
        
        # Display all images, including unclassified or errored ones
        if st.session_state.processed_data['images']:
            with st.expander("Résultats d'analyse d'images", expanded=True):
                cols = st.columns(3)
                for idx, img_data in enumerate(st.session_state.processed_data['images']):
                    with cols[idx % 3]:
                        st.image(img_data['image'], use_container_width=True)
                        
                        # Customize display based on image type
                        type_display = img_data['type']
                        if type_display in ['Non classifié', 'Erreur de classification', 'Erreur de traitement']:
                            type_display = f"{type_display} ⚠️"
                        
                        st.markdown(
                            f"""
                            **Type:** {type_display}  
                            **Numéro de série:** {img_data.get('serial', 'N/A')}  
                            **Date:** {img_data.get('date', 'N/A')}
                            """,
                            unsafe_allow_html=True
                        )
        else:
            st.info("Aucune image traitée à afficher pour le moment.")

    with tab3:
        st.title("📋v📑 Comparaison des documents")
        with st.expander("Comparaison des documents", expanded=True):
            # Removed the button and its styling
            aed_results = compare_rvd_aed()
            image_results = compare_rvd_images()
            display_comparison("Comparaison RVD vs Rapport AED", aed_results)
            display_comparison("Comparaison RVD vs Données d'images", image_results)
            all_matches = all(
                item.get('match', False)
                for comp in [aed_results, image_results]
                for item in comp.values()
            )
            if all_matches:
                st.success("Tous les contrôles sont réussis ! Le dispositif est conforme.")
            else:
                failed = [
                    k for comp in [aed_results, image_results]
                    for k, v in comp.items() if not v.get('match', True)
                ]
                st.error(f"Échec de validation pour : {', '.join(failed)}")

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
                                        'processed_data.json',
                                        json.dumps(st.session_state.processed_data, indent=2)
                                    )
                                    summary = (
                                        "Résumé de l'inspection\n\n"
                                        "Données RVD:\n" +
                                        json.dumps(st.session_state.processed_data['RVD'], indent=2) +
                                        "\n\n" +
                                        f"Données AED {st.session_state.dae_type}:\n" +
                                        json.dumps(st.session_state.processed_data[f'AEDG{st.session_state.dae_type[-1]}'], indent=2) +
                                        "\n\nComparaisons:\n"
                                    )
                                    for comp_type, comp_data in st.session_state.processed_data['comparisons'].items():
                                        summary += f"{comp_type.replace('_vs_', ' vs ').upper()}:\n"
                                        for field, data in comp_data.items():
                                            summary += (
                                                f"  {field.replace('_', ' ').title()}: "
                                                f"{'✅' if data.get('match', False) else '❌'}\n"
                                            )
                                    zipf.writestr("summary.txt", summary)
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
                            "processed_data.json",
                            "summary.txt",
                            *(
                                ["images.zip"]
                                if include_images and any(
                                    f.type.startswith("image/")
                                    for f in st.session_state.get('uploaded_files', [])
                                )
                                else []
                            )
                        ],
                        "taille_estimee": f"{(len(st.session_state.get('uploaded_files', []))*0.5):.1f} MB"
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
