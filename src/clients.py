"""Client initializations for the Comparateur_PDF project."""

import streamlit as st
import torch
import easyocr
from inference_sdk import InferenceHTTPClient
from .config import API_URL  

def initialize_clients():
    """
    Initialize InferenceHTTPClient and EasyOCR reader.
    
    Returns:
        tuple: (InferenceHTTPClient, EasyOCR Reader) instances
    """
    try:
        client = InferenceHTTPClient(
            api_url=API_URL,
            api_key=st.secrets["API_KEY"]
        )
        # Check for GPU availability once and use it
        use_gpu = torch.cuda.is_available()
        reader = easyocr.Reader(['en'], gpu=use_gpu)
        return client, reader
    except KeyError as e:
        raise KeyError("API_KEY not found in Streamlit secrets") from e
    except Exception as e:
        raise RuntimeError("Failed to initialize clients") from e
