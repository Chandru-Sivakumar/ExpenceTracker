# Receipt Scanner Web Application

A web application that allows users to upload receipt images, extract information using OCR, and display the processed data in a table format.

## Features

- Upload receipt images
- Preview images before upload
- Automatic text extraction using OCR
- Categorization of receipts
- Display of extracted information in a table
- View original receipt images
- Responsive and modern UI

## Prerequisites

- Python 3.8 or higher
- Tesseract OCR installed on your system
  - For Windows: Download and install from [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
  - For Linux: `sudo apt-get install tesseract-ocr`
  - For macOS: `brew install tesseract`

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Create a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the Flask application:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

3. Use the web interface to:
   - Upload receipt images
   - View processed data
   - View original receipt images

## Project Structure

```
.
├── app.py              # Flask application
├── requirements.txt    # Python dependencies
├── templates/          # HTML templates
│   └── index.html     # Main web interface
├── input_images/      # Directory for uploaded images
└── extracted_data/    # Directory for processed data
```

## Notes

- The application uses Tesseract OCR for text extraction
- Images are stored in the `input_images` directory
- Extracted data is saved in CSV format in the `extracted_data` directory
- The application supports common image formats (JPG, PNG, etc.) 