# Comparateur_PDF

## Project Structure

```
Comparateur_PDF/
│
├── src/
│   ├── __init__.py           # Empty file to mark src as a package
│   ├── config.py             # Configuration settings and constants
│   ├── clients.py            # Client initializations (e.g., InferenceHTTPClient, OCR reader)
│   ├── utils.py              # Utility functions (e.g., date parsing, serial normalization)
│   ├── processing.py         # Image and PDF processing functions
│   ├── extraction.py         # Data extraction functions (e.g., RVD, AED)
│   ├── comparison.py         # Comparison logic
│   └── ui.py                 # Streamlit UI components and main app logic
│
├── app.py                    # Entry point for running the Streamlit app
├── requirements.txt          # List of dependencies
└── README.md                 # Project documentation
```

## Description

Comparateur_PDF is a tool designed to process, extract, and compare data from PDF documents. It includes a Streamlit-based UI for ease of use.

## Installation

1. Clone the repository:
    ```sh
    git clone <repository_url>
    ```
2. Navigate to the project directory:
    ```sh
    cd Comparateur_PDF
    ```
3. Install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```

## Usage

To run the Streamlit app, execute the following command:
```sh
streamlit run app.py
```

## Files and Directories

- `src/`: Contains the source code for the project.
  - `__init__.py`: Marks `src` as a package.
  - `config.py`: Configuration settings and constants.
  - `clients.py`: Client initializations (e.g., InferenceHTTPClient, OCR reader).
  - `utils.py`: Utility functions (e.g., date parsing, serial normalization).
  - `processing.py`: Image and PDF processing functions.
  - `extraction.py`: Data extraction functions (e.g., RVD, AED).
  - `comparison.py`: Comparison logic.
  - `ui.py`: Streamlit UI components and main app logic.
- `app.py`: Entry point for running the Streamlit app.
- `requirements.txt`: List of dependencies.
- `README.md`: Project documentation.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License.
