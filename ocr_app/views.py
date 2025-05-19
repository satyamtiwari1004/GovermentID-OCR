from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import Passport
from passporteye import read_mrz
import pytesseract
from PIL import Image
import cv2
import numpy as np
import re
import os
import easyocr

import torch

pin = False  # True only if not using MPS

def home(request):
    passports = Passport.objects.all().order_by('-created_at')
    return render(request, 'ocr_app/home.html', {'passports': passports})

def upload_passport(request):
    if request.method == 'POST' and request.FILES.get('passport_image'):
        try:
            passport = Passport.objects.create(image=request.FILES['passport_image'])
            
            # Process the image with OpenCV
            image_path = passport.image.path
            image = cv2.imread(image_path)
            
            if image is None:
                raise Exception("Failed to read image")
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Denoise
            gray = cv2.fastNlMeansDenoising(gray, h=30)

            # Resize (scale up for better OCR)
            gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

            # Apply adaptive thresholding (more robust than Otsu for uneven lighting)
            gray = cv2.adaptiveThreshold(gray, 255,
                                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                        cv2.THRESH_BINARY, 31, 2)

            # Optional: sharpen image
            kernel = np.array([[0, -1, 0], 
                            [-1, 5,-1], 
                            [0, -1, 0]])
            gray = cv2.filter2D(gray, -1, kernel)

            # OCR
            text = pytesseract.image_to_string(gray)

            print("🔍 OCR Output:\n", text)

            
            # Define regex patterns
            patterns = {
                "Passport Number": r'P\d{7}',
                "Surname": r'Surname\s*[:\-]?\s*(\w+)',
                "Given Names": r'Given Names\s*[:\-]?\s*([\w\s]+)',
                "Nationality": r'Nationality\s*[:\-]?\s*(\w+)',
                "Date of Birth": r'(\d{2}/\d{2}/\d{4})',
                "Place of Birth": r'Place of Birth\s*[:\-]?\s*(\w+)',
                "Date of Issue": r'(\d{2}/\d{2}/\d{4})',
                "Date of Expiry": r'(\d{2}/\d{2}/\d{4})'
            }
            
            # Extract fields
            extracted_data = {}
            dob_found = doi_found = doe_found = False
            
            for key, pattern in patterns.items():
                matches = re.findall(pattern, text)
                if matches:
                    if key == "Date of Birth" and not dob_found:
                        extracted_data[key] = matches[0]
                        dob_found = True
                    elif key == "Date of Issue" and not doi_found and len(matches) > 1:
                        extracted_data[key] = matches[1]
                        doi_found = True
                    elif key == "Date of Expiry" and not doe_found and len(matches) > 2:
                        extracted_data[key] = matches[2]
                        doe_found = True
                    elif key not in extracted_data:
                        extracted_data[key] = matches[0]
            
            # Update passport object with extracted data
            passport.passport_number = extracted_data.get("Passport Number", "")
            passport.surname = extracted_data.get("Surname", "")
            passport.given_names = extracted_data.get("Given Names", "")
            passport.nationality = extracted_data.get("Nationality", "")
            passport.date_of_birth = extracted_data.get("Date of Birth", "")
            passport.place_of_birth = extracted_data.get("Place of Birth", "")
            passport.date_of_issue = extracted_data.get("Date of Issue", "")
            passport.date_of_expiry = extracted_data.get("Date of Expiry", "")
            
            passport.save()

            reader = easyocr.Reader(['en'])
            result = reader.readtext(image_path, detail=0)
            print(result)
            parsed_data = extract_passport_info(result)
            
            print(parsed_data)
            for key, value in parsed_data.items():
                    print(f"{key}: {value}")
            
            return JsonResponse({
                'status': 'success',
                'passport': {
                    'id': passport.id,
                    'passport_number': passport.passport_number,
                    'surname': passport.surname,
                    'given_names': passport.given_names,
                    'nationality': passport.nationality,
                    'date_of_birth': passport.date_of_birth,
                    'place_of_birth': passport.place_of_birth,
                    'date_of_issue': passport.date_of_issue,
                    'date_of_expiry': passport.date_of_expiry,
                }
            })
            
        except Exception as e:
            # If there's an error, delete the passport object if it was created
            if 'passport' in locals():
                passport.delete()
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

def correct_mrz_character(c, position, line_number):
    # Allowed character sets by field
    if line_number == 1:
        if position in range(0, 2):  # P<
            return 'P' if c not in ['P', '<'] else c
        elif position in range(2, 5):  # A-Z (Issuing country)
            return c if c.isalpha() else '<'
        else:  # Names section
            return c if c.isalpha() or c == '<' else '<'
    elif line_number == 2:
        if position in list(range(0, 9)) + list(range(10, 13)) + list(range(28, 43)):
            # Passport no., Nationality, Optional data
            return c if c.isalnum() or c == '<' else '<'
        elif position in [9, 19, 27, 42]:  # Check digits
            return c if c.isdigit() or c == '<' else '<'
        elif position in range(13, 19):  # DOB YYMMDD
            return c if c.isdigit() else '<'
        elif position == 20:  # Sex
            return c if c in ['M', 'F', '<'] else '<'
        elif position in range(21, 27):  # Expiry date
            return c if c.isdigit() else '<'
        else:
            return c if c.isalnum() or c == '<' else '<'
    else:
        return c

def clean_mrz_line_by_standard(line, line_number):
    line = line.strip().upper().replace(' ', '<').replace('?', '<').replace('_', '<')

    # Replace common misread characters
    ocr_fixes = {
        'O': '0', 'Q': '0', 'D': '0',  # Digits
        'I': '1', 'L': '1', '|': '1',
        'Z': '2', 'S': '5', 'B': '8',
    }

    line = ''.join(ocr_fixes.get(c, c) for c in line)

    # Ensure correct length (MRZ line is 44 chars for passports)
    line = line.ljust(44, '<')[:44]

    # Apply field-based correction
    corrected = ''.join(correct_mrz_character(c, i, line_number) for i, c in enumerate(line))
    return corrected

def parse_mrz(line1, line2):
    if len(line1) < 44 or len(line2) < 44:
        return {"error": "Incomplete MRZ lines"}

    passport_type = line1[0]
    issuing_country = line1[2:5]
    names_raw = line1[5:].split('<<')
    surname = names_raw[0].replace('<', ' ').strip()
    given_names = names_raw[1].replace('<', ' ').strip() if len(names_raw) > 1 else ""

    passport_number = line2[0:9].replace('<', '').strip()
    nationality = line2[10:13].strip()
    dob = line2[13:19]
    sex = line2[20]
    expiry = line2[21:27]

    def format_date(ymd):
        year = "19" + ymd[:2] if int(ymd[:2]) > 25 else "20" + ymd[:2]
        return f"{year}-{ymd[2:4]}-{ymd[4:6]}"

    return {
        "Passport Type": passport_type,
        "Issuing Country": issuing_country,
        "Surname": surname,
        "Given Names": given_names,
        "Passport Number": passport_number,
        "Nationality": nationality,
        "Date of Birth": format_date(dob),
        "Date of Expiry": format_date(expiry),
        "Sex": {"M": "Male", "F": "Female"}.get(sex, "Unspecified")
    }

import re
from datetime import datetime

def extract_passport_info(ocr_lines):
    cleaned_lines = [line.strip().replace('’', "'") for line in ocr_lines if line and isinstance(line, str)]

    # Fields to extract
    passport_data = {
        "Passport Number": None,
        "Surname": None,
        "Given Names": None,
        "Nationality": None,
        "Date of Birth": None,
        "Place of Birth": None,
        "Date of Issue": None,
        "Date of Expiry": None,
        "MRZ": []
    }

    # Collect MRZ (2 or 3 lines with '<' and length ~44)
    mrz_candidates = [line for line in cleaned_lines if '<' in line and len(line) >= 30]
    passport_data["MRZ"] = mrz_candidates[:3]

    # Extract dates
    date_candidates = [line for line in cleaned_lines if re.search(r'\d{2}/\d{2}/\d{4}', line)]
    for date_str in date_candidates:
        try:
            dt = datetime.strptime(date_str, "%d/%m/%Y")
            year = dt.year
            if year < 1970:
                passport_data["Date of Birth"] = date_str
            elif year < datetime.now().year:
                passport_data["Date of Issue"] = date_str
            else:
                passport_data["Date of Expiry"] = date_str
        except:
            continue

    # Find passport number: 7-9 alphanumeric characters, possibly prefixed with '?'
    for line in cleaned_lines:
        match = re.search(r'[A-Z0-9]{7,9}', line.replace('?', '').upper())
        if match and not passport_data["Passport Number"]:
            passport_data["Passport Number"] = match.group()

    # Name extraction: Look for line with both upper-case and likely 'Given' and 'Surname'
    name_lines = [line for line in cleaned_lines if re.search(r'[A-Z][a-z]+ [A-Z][a-z]+', line)]
    if name_lines:
        full_name = name_lines[-1]
        parts = full_name.strip().split()
        if len(parts) >= 2:
            passport_data["Surname"] = parts[-1]
            passport_data["Given Names"] = ' '.join(parts[:-1])

    # Try nationality: look for short uppercase country name
    for line in cleaned_lines:
        if line.isupper() and len(line) == 3:
            passport_data["Nationality"] = line
            break

    # Fallback place of birth: first readable city-like word
    for line in cleaned_lines:
        if re.match(r'[A-Z][a-z]+', line) and line.lower() not in ['name', 'verified']:
            passport_data["Place of Birth"] = line
            break

    return passport_data