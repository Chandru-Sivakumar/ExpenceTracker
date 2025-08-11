from flask import Flask, render_template, request, jsonify, send_from_directory, send_file, redirect, url_for, session, flash
import os
import cv2
import pytesseract
from PIL import Image
import pandas as pd
import re
from werkzeug.utils import secure_filename
from datetime import datetime
import io
import numpy as np
from users import add_user, verify_user
import hashlib
import csv
import json

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'input_images')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.secret_key = os.urandom(24)  # Required for session management

# Ensure upload and data directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('extracted_data', exist_ok=True)

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Login required decorator
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if verify_user(username, password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not password:
            return render_template('register.html', error='Username and password are required')
        
        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match')
        
        success, message = add_user(username, password)
        if success:
            return render_template('register.html', success=message)
        else:
            return render_template('register.html', error=message)
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('landing'))

@app.route('/')
def landing():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('index.html')

def preprocess_image(image_path):
    image = cv2.imread(image_path, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, threshold = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    return threshold

def extract_text(image_path):
    try:
        print(f"Extracting text from: {image_path}")
        processed = preprocess_image(image_path)
        text = pytesseract.image_to_string(processed)
        return text
    except Exception as e:
        print(f"Error in extract_text: {str(e)}")
        raise

def classify_type(text):
    text = text.lower()
    if "invoice" in text:
        return "Invoice"
    elif "bill to" in text or "bill no" in text:
        return "Bill"
    elif "receipt" in text:
        return "Receipt"
    else:
        return "Unknown"

def extract_fields(text):
    text_lower = text.lower()

    # Date Patterns
    date_patterns = [
        r'\b\d{2}[\/\-\.]\d{2}[\/\-\.]\d{2,4}\b',
        r'\b\d{4}[\/\-\.]\d{2}[\/\-\.]\d{2}\b',
        r'\b\d{2} [A-Za-z]{3,9} \d{2,4}\b',
        r'\b[A-Za-z]{3,9} \d{1,2},? \d{4}\b',
    ]
    date = None
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            date = match.group()
            break

    # Amount Patterns
    amount_patterns = [
        r'\b(?:total|amount|amt|grand total|balance)\s*[:\\-]?\s*₹?\$?\s*(\d{1,3}(?:[,\d{3}]*)(?:\.\d{2})?)',
        r'₹\s?(\d{1,3}(?:[,\d{3}]*)(?:\.\d{2})?)',
        r'\$\s?(\d+(?:\.\d{2})?)'
    ]
    amount = None
    for pattern in amount_patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            amount = match.group(1)
            break

    # Category Detection
    if any(keyword in text_lower for keyword in ["restaurant", "food", "dining", "cafe", "meal"]):
        category = "Food"
    elif any(keyword in text_lower for keyword in ["flight", "uber", "taxi", "bus", "travel", "trip", "train"]):
        category = "Travel"
    elif any(keyword in text_lower for keyword in ["movie", "theater", "concert", "netflix", "event", "entertainment"]):
        category = "Entertainment"
    else:
        category = "Other"

    return {
        "date": date if date else "Not found",
        "amount": amount if amount else "Not found",
        "category": category
    }

def analyze_receipt(image_path):
    try:
        print(f"Processing image: {image_path}")
        text = extract_text(image_path)
        print(f"Extracted text: {text[:100]}...")  # Print first 100 chars of extracted text
        receipt_type = classify_type(text)
        fields = extract_fields(text)
        result = {
            "type": receipt_type,
            **fields
        }
        print(f"Analysis result: {result}")
        return result, os.path.basename(image_path)
    except Exception as e:
        print(f"Error in analyze_receipt: {str(e)}")
        raise

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        try:
            # Generate a unique filename for camera captures
            if file.filename == 'captured_receipt.jpg':
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'captured_receipt_{timestamp}.jpg'
            else:
                filename = secure_filename(file.filename)
                
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Save the file
            file.save(filepath)
            print(f"Saved file to: {filepath}")
            
            # Verify the image was saved correctly
            if not os.path.exists(filepath):
                return jsonify({'error': 'Failed to save image'}), 500
                
            # Process the image
            result, saved_filename = analyze_receipt(filepath)
            print(f"Analysis result: {result}")
            
            # Save to CSV
            df = pd.DataFrame([{**result, 'filename': saved_filename}])
            output_csv = os.path.join("extracted_data", "output.csv")
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_csv), exist_ok=True)
            
            if os.path.exists(output_csv):
                df.to_csv(output_csv, mode='a', header=False, index=False)
            else:
                df.to_csv(output_csv, index=False)
                
            print(f"Saved data to CSV: {output_csv}")

            return jsonify({**result, 'file': saved_filename})
            
        except Exception as e:
            print(f"Error in upload_file: {str(e)}")
            return jsonify({'error': str(e)}), 500

@app.route('/get_data')
def get_data():
    try:
        # Use absolute path for CSV file
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'extracted_data', 'output.csv')
        print(f"Looking for CSV file at: {csv_path}")
        
        if not os.path.exists(csv_path):
            print("CSV file does not exist")
            return jsonify([])
            
        print("Reading CSV file...")
        df = pd.read_csv(csv_path)
        print(f"CSV raw contents: {df.to_dict('records')}")
        
        if df.empty:
            print("CSV file is empty")
            return jsonify([])
            
        # Map the columns correctly
        records = []
        for _, row in df.iterrows():
            # Convert row to dict and get the first value of each column as the key
            row_dict = row.to_dict()
            keys = list(row_dict.keys())
            
            record = {
                'type': row_dict.get(keys[0], 'Unknown'),
                'date': row_dict.get(keys[1], 'Not found'),
                'amount': row_dict.get(keys[2], 'Not found'),
                'category': row_dict.get(keys[3], 'Other'),
                'file': row_dict.get(keys[4], None)
            }
            
            # Only add records that have a valid filename
            if record['file'] and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], record['file'])):
                records.append(record)
            else:
                print(f"Skipping record due to missing or invalid file: {record}")
        
        print(f"Returning {len(records)} processed records: {records}")
        return jsonify(records)
    except Exception as e:
        print(f"Error in get_data: {str(e)}")
        return jsonify([])

@app.route('/input_images/<filename>')
def serve_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/export/excel')
def export_excel():
    try:
        output_csv = os.path.join("extracted_data", "output.csv")
        if not os.path.exists(output_csv):
            return jsonify({'error': 'No data available'}), 404
            
        df = pd.read_csv(output_csv)
        if df.empty:
            return jsonify({'error': 'No data available'}), 404
            
        # Create Excel file in memory
        excel_file = io.BytesIO()
        df.to_excel(excel_file, index=False)
        excel_file.seek(0)
        
        return send_file(
            excel_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='receipts.xlsx'
        )
    except Exception as e:
        print(f"Error exporting to Excel: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/export/csv')
def export_csv():
    try:
        output_csv = os.path.join("extracted_data", "output.csv")
        if not os.path.exists(output_csv):
            return jsonify({'error': 'No data available'}), 404
            
        return send_file(
            output_csv,
            mimetype='text/csv',
            as_attachment=True,
            download_name='receipts.csv'
        )
    except Exception as e:
        print(f"Error exporting to CSV: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete/<filename>', methods=['DELETE'])
def delete_receipt(filename):
    try:
        # Secure the filename and get paths
        filename = secure_filename(filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'extracted_data', 'output.csv')
        
        print(f"Attempting to delete receipt: {filename}")
        
        # Check if CSV exists and update it first
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                print(f"Current records in CSV: {len(df)}")
                
                # Remove the record from DataFrame
                df_filtered = df[df['file'] != filename]
                print(f"Records after filtering: {len(df_filtered)}")
                
                # Save updated DataFrame back to CSV
                df_filtered.to_csv(csv_path, index=False)
                print(f"Updated CSV saved with {len(df_filtered)} records")
            except Exception as e:
                print(f"Error updating CSV: {str(e)}")
                return jsonify({'error': 'Failed to update database'}), 500
        
        # Now try to delete the file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Successfully deleted file: {file_path}")
            except Exception as e:
                print(f"Error deleting file: {str(e)}")
                return jsonify({'error': 'Failed to delete file'}), 500
        else:
            print(f"File not found: {file_path}")
            # Continue even if file doesn't exist, as we want to remove the database entry
        
        return jsonify({
            'message': 'Receipt deleted successfully',
            'filename': filename
        })
        
    except Exception as e:
        print(f"Error in delete_receipt: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/process_existing_images')
def process_existing_images():
    try:
        # Get all images in the input_images directory
        image_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if not image_files:
            return jsonify({'message': 'No images found to process'})
            
        # Process each image
        processed_data = []
        for filename in image_files:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                # Process the image
                result, saved_filename = analyze_receipt(filepath)
                print(f"Analysis result for {filename}: {result}")
                
                # Add to processed data with correct structure
                processed_data.append({
                    'type': result.get('type', 'Unknown'),
                    'date': result.get('date', 'Not found'),
                    'amount': result.get('amount', 'Not found'),
                    'category': result.get('category', 'Other'),
                    'file': saved_filename
                })
                
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
                continue
        
        if processed_data:
            # Create DataFrame with correct column names
            df = pd.DataFrame(processed_data)
            
            # Ensure the extracted_data directory exists
            csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'extracted_data', 'output.csv')
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            
            # Save to CSV with proper column names
            df.to_csv(csv_path, index=False, columns=['type', 'date', 'amount', 'category', 'file'])
            print(f"Saved {len(processed_data)} records to CSV: {csv_path}")
            
            return jsonify({
                'message': f'Processed {len(processed_data)} images successfully',
                'data': processed_data
            })
        else:
            return jsonify({'message': 'No images were successfully processed'})
            
    except Exception as e:
        print(f"Error in process_existing_images: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/update_receipt', methods=['POST'])
def update_receipt():
    try:
        data = request.json
        if not data or 'filename' not in data:
            return jsonify({'error': 'Invalid request data'}), 400

        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'extracted_data', 'output.csv')
        
        if not os.path.exists(csv_path):
            return jsonify({'error': 'No receipt data found'}), 404
            
        # Read existing data
        df = pd.read_csv(csv_path)
        
        # Find the row with matching filename
        mask = df['file'] == data['filename']
        if not any(mask):
            return jsonify({'error': 'Receipt not found'}), 404
            
        # Update the row
        df.loc[mask, 'type'] = data['type']
        df.loc[mask, 'date'] = data['date']
        df.loc[mask, 'amount'] = data['amount']
        df.loc[mask, 'category'] = data['category']
        
        # Save back to CSV
        df.to_csv(csv_path, index=False)
        
        return jsonify({
            'message': 'Receipt updated successfully',
            'data': {
                'filename': data['filename'],
                'type': data['type'],
                'date': data['date'],
                'amount': data['amount'],
                'category': data['category']
            }
        })
        
    except Exception as e:
        print(f"Error in update_receipt: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/profile')
@login_required
def profile():
    # Generate email hash for Gravatar
    if 'email' in session:
        email_hash = hashlib.md5(session['email'].lower().encode()).hexdigest()
        session['email_hash'] = email_hash
    return render_template('profile.html')

@app.route('/api/user-stats')
@login_required
def user_stats():
    try:
        # Read the CSV file to get statistics
        csv_path = os.path.join(app.root_path, 'extracted_data', 'output.csv')
        total_receipts = 0
        total_expenses = 0.0
        
        if os.path.exists(csv_path):
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                receipts = list(reader)
                total_receipts = len(receipts)
                
                for receipt in receipts:
                    try:
                        # Remove currency symbols and commas, then convert to float
                        amount_str = receipt.get('amount', '0')
                        amount_str = ''.join(c for c in amount_str if c.isdigit() or c in '.-')
                        amount = float(amount_str) if amount_str else 0
                        total_expenses += amount
                    except (ValueError, TypeError):
                        continue
        
        return jsonify({
            'totalReceipts': total_receipts,
            'totalExpenses': total_expenses
        })
    except Exception as e:
        app.logger.error(f"Error getting user stats: {str(e)}")
        return jsonify({'error': 'Failed to load user statistics'}), 500

@app.route('/api/update-profile', methods=['POST'])
@login_required
def update_profile():
    try:
        data = request.get_json()
        email = data.get('email')
        new_password = data.get('newPassword')
        
        # Update user data in users.json
        users_file = os.path.join(app.root_path, 'users.json')
        with open(users_file, 'r') as f:
            users = json.load(f)
        
        if session['username'] in users:
            if email:
                users[session['username']]['email'] = email
                session['email'] = email
                session['email_hash'] = hashlib.md5(email.lower().encode()).hexdigest()
            
            if new_password:
                users[session['username']]['password'] = hashlib.sha256(new_password.encode()).hexdigest()
            
            with open(users_file, 'w') as f:
                json.dump(users, f, indent=4)
            
            return jsonify({'message': 'Profile updated successfully'})
        
        return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        app.logger.error(f"Error updating profile: {str(e)}")
        return jsonify({'error': 'Failed to update profile'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
