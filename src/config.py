"""Configuration settings for the Comparateur_PDF project."""

API_URL = "https://detect.roboflow.com"
MODEL_ID = "medical-object-classifier/3"
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

CSS_STYLE = """
    <style>
        :root {
            --primary: #006699;
            --secondary: #4CAF50;
            --accent: #f8f9fa;
        }
        .main { background-color: var(--accent); font-family: 'Segoe UI', system-ui; }
        .stButton>button {
            background-color: var(--secondary);
            transition: all 0.3s ease;
            transform: scale(1);
            border: none;
        }
        .stButton>button:hover {
            transform: scale(1.05);
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }
        .header {
            background: linear-gradient(135deg, #006699 0%, #004466 100%);
            color: white;
            padding: 2rem 3rem;
            border-radius: 0 0 20px 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 1rem;
            padding: 0 2rem;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 1rem 2rem;
            border-radius: 8px;
            transition: all 0.3s ease;
        }
        .stTabs [aria-selected="true"] {
            background-color: var(--primary) !important;
            color: white !important;
        }
        .card {
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            margin-bottom: 1.5rem;
            background: white;
            border-left: 4px solid var(--primary);
        }
        .upload-dropzone {
            border: 2px dashed var(--primary) !important;
            border-radius: 12px;
            padding: 3rem 1rem;
            background: rgba(0,102,153,0.05);
        }
        .file-preview {
            border-left: 3px solid var(--secondary);
            padding: 1rem;
            margin: 0.5rem 0;
            background: rgba(76,175,80,0.05);
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.02); }
            100% { transform: scale(1); }
        }
    </style>
"""
