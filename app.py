"""Entry point for the Comparateur_PDF Streamlit application."""

from src.clients import initialize_clients
from src.test_ui import render_ui

def main():
    """Run the Streamlit application."""
    client, reader = initialize_clients()
    render_ui(client, reader)

if __name__ == "__main__":
    main()
