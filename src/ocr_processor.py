import cv2
import numpy as np
import pytesseract
import re
import logging
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRProcessor:
    """OCR processor for extracting text from detected regions"""
    
    def __init__(self):
        """Initialize OCR processor with optimized configurations"""
        self.ocr_configs = Config.OCR_CONFIGS
        logger.info("OCR processor initialized")
    
    def preprocess_image(self, image_region):
        """Preprocess image region for better OCR accuracy"""
        try:
            # Convert to grayscale if needed
            if len(image_region.shape) == 3:
                gray = cv2.cvtColor(image_region, cv2.COLOR_BGR2GRAY)
            else:
                gray = image_region
            
            # Enhance contrast
            enhanced = cv2.convertScaleAbs(gray, alpha=1.2, beta=10)
            
            # Resize for better OCR (2x scaling)
            height, width = enhanced.shape
            resized = cv2.resize(enhanced, (width*2, height*2), interpolation=cv2.INTER_CUBIC)
            
            # Apply slight Gaussian blur to smooth text
            blurred = cv2.GaussianBlur(resized, (1, 1), 0)
            
            return blurred
            
        except Exception as e:
            logger.error(f"Error in image preprocessing: {str(e)}")
            return image_region
    
    def extract_text(self, image_region, field_type='text'):
        """Extract text from image region using appropriate OCR configuration"""
        try:
            # Validate input
            if image_region is None or image_region.size == 0:
                return ""
            
            # Preprocess image
            processed = self.preprocess_image(image_region)
            
            # Get appropriate OCR configuration
            config = self.ocr_configs.get(field_type, self.ocr_configs['text'])
            
            # Extract text using Tesseract
            text = pytesseract.image_to_string(processed, config=config).strip()
            
            # Clean up extracted text
            text = self._clean_text(text, field_type)
            
            return text
            
        except Exception as e:
            logger.error(f"OCR extraction error: {str(e)}")
            return ""
    
    def _clean_text(self, text, field_type):
        """Clean and format extracted text based on field type"""
        if not text:
            return ""
        
        # Basic cleaning - remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('\n', ' ').replace('\r', ' ').strip()
        
        # Field-specific cleaning
        if field_type == 'amounts':
            text = re.sub(r'[^\d₹.,\-\s]', '', text)
            text = re.sub(r'\s+', ' ', text)
        elif field_type == 'dates':
            text = re.sub(r'[^\d/\-.\s]', '', text)
            text = re.sub(r'\s+', '', text)
        elif field_type == 'gst_number':
            text = re.sub(r'[^A-Z0-9]', '', text.upper())
        elif field_type == 'numbers':
            text = re.sub(r'[^\d]', '', text)
        elif field_type == 'alphanumeric':
            text = re.sub(r'[^A-Za-z0-9\s\-/]', '', text)
            text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
