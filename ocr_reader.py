import pytesseract
from PIL import Image
import cv2
import os
import sys

def preprocess_image(image_path):
    """Preprocess the image for better OCR results"""
    # Read the image
    image = cv2.imread(image_path, cv2.IMREAD_COLOR)
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply thresholding to preprocess the image
    _, threshold = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    
    return threshold

def extract_text(image_path):
    """Extract text from the image using OCR"""
    try:
        print(f"\nProcessing image: {image_path}")
        
        # Preprocess the image
        processed_image = preprocess_image(image_path)
        
        # Perform OCR
        text = pytesseract.image_to_string(processed_image)
        
        # Print the extracted text
        print("\nExtracted Text:")
        print("-" * 50)
        print(text)
        print("-" * 50)
        
        return text
        
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return None

def main():
    # Set Tesseract path (adjust if needed)
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
    # Check if image path is provided
    if len(sys.argv) != 2:
        print("Usage: python ocr_reader.py <image_path>")
        print("Example: python ocr_reader.py input_images/receipt.jpg")
        return
    
    image_path = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(image_path):
        print(f"Error: File not found - {image_path}")
        return
    
    # Extract and print text
    extract_text(image_path)

if __name__ == "__main__":
    main() 