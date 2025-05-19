# Passport OCR Scanner

A Django web application that uses OCR to extract information from passport images. The application features a modern UI with drag-and-drop functionality for uploading passport images.

## Features

- Drag and drop interface for uploading passport images
- OCR processing of passport images using Tesseract
- Extraction of key passport information:
  - Passport Number
  - Surname
  - Given Names
  - Nationality
  - Date of Birth
  - Place of Birth
  - Date of Issue
  - Date of Expiry
- Modern, responsive UI using Tailwind CSS

## Prerequisites

- Python 3.8 or higher
- Tesseract OCR installed on your system
- Virtual environment (recommended)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd passport-ocr
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Install Tesseract OCR:
- On macOS:
```bash
brew install tesseract
```
- On Ubuntu:
```bash
sudo apt-get install tesseract-ocr
```
- On Windows:
Download and install from: https://github.com/UB-Mannheim/tesseract/wiki

5. Set up environment variables:
```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your settings
nano .env  # or use your preferred text editor
```

Required environment variables:
- `DEBUG`: Set to 'True' for development, 'False' for production
- `SECRET_KEY`: Your Django secret key
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts

6. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

7. Start the development server:
```bash
python manage.py runserver
```

8. Visit http://localhost:8000 in your web browser

## Usage

1. Open the web application in your browser
2. Drag and drop a passport image onto the upload area or click to select a file
3. Wait for the OCR processing to complete
4. View the extracted information below the upload area

## Notes

- The application works best with clear, high-quality passport images
- Black and white or grayscale images are recommended for better OCR results
- The OCR accuracy may vary depending on the image quality and format
- Never commit your .env file to version control
- Always keep your SECRET_KEY secure and different between environments

## License

This project is licensed under the MIT License - see the LICENSE file for details. 