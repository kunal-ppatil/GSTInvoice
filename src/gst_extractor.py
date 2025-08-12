import cv2
import numpy as np
import logging
from datetime import datetime
from ultralytics import YOLO
from .ocr_processor import OCRProcessor
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GSTInvoiceExtractor:
    """Main GST Invoice Extraction class using YOLOv9c + OCR"""
    
    def __init__(self, model_path):
        """Initialize GST invoice extractor"""
        try:
            self.model = YOLO(model_path)
            self.ocr = OCRProcessor()
            self.field_ocr_types = Config.FIELD_OCR_MAPPING
            logger.info(f"GST Extractor initialized with model: {model_path}")
        except Exception as e:
            logger.error(f"Failed to initialize GST extractor: {str(e)}")
            raise
    
    def extract_gst_information(self, image_path, confidence_threshold=0.5):
        """Extract complete GST information from invoice image"""
        try:
            # Load and validate image
            image = cv2.imread(image_path)
            if image is None:
                return {"error": "Could not load image"}
            
            logger.info(f"Processing invoice: {image_path}")
            
            # Run YOLOv9c detection
            results = self.model(image_path)
            
            # Initialize structured data
            gst_data = {
                'invoice_metadata': {
                    'invoice_number': [],
                    'invoice_date': [],
                    'total_amount': [],
                    'po_number': []
                },
                'business_information': {
                    'merchant_name': [],
                    'merchant_address': [],
                    'gst_numbers': []
                },
                'tax_information': {
                    'cgst': [],
                    'sgst': [],
                    'igst': [],
                    'total_gst': [],
                    'tcs': [],
                    'compensation_cess': []
                },
                'summary': {
                    'total_detections': 0,
                    'confidence_scores': [],
                    'average_confidence': 0,
                    'extraction_timestamp': datetime.now().isoformat()
                }
            }
            
            # Process each detection
            for r in results:
                boxes = r.boxes
                if boxes is not None:
                    for box in boxes:
                        class_id = int(box.cls)
                        confidence = float(box.conf)
                        class_name = self.model.names[class_id]
                        
                        if confidence >= confidence_threshold:
                            # Get bounding box coordinates
                            bbox = box.xyxy[0].cpu().numpy().astype(int)
                            x1, y1, x2, y2 = bbox
                            
                            # Crop region from image
                            cropped_region = image[y1:y2, x1:x2]
                            
                            # Determine OCR type
                            ocr_type = self.field_ocr_types.get(class_name, 'text')
                            
                            # Extract text using OCR
                            extracted_text = self.ocr.extract_text(cropped_region, ocr_type)
                            
                            # Create detection entry
                            detection = {
                                'field_type': class_name,
                                'text_content': extracted_text,
                                'confidence': confidence,
                                'bbox': bbox.tolist()
                            }
                            
                            # Categorize detection
                            self._categorize_detection(detection, gst_data)
                            
                            # Update summary
                            gst_data['summary']['total_detections'] += 1
                            gst_data['summary']['confidence_scores'].append(confidence)
            
            # Calculate average confidence
            if gst_data['summary']['confidence_scores']:
                gst_data['summary']['average_confidence'] = sum(gst_data['summary']['confidence_scores']) / len(gst_data['summary']['confidence_scores'])
            
            return gst_data
            
        except Exception as e:
            logger.error(f"Error during GST extraction: {str(e)}")
            return {"error": f"Extraction failed: {str(e)}"}
    
    def _categorize_detection(self, detection, gst_data):
        """Categorize detection into appropriate GST data section"""
        field_type = detection['field_type']
        
        if 'Invoice Number' in field_type:
            gst_data['invoice_metadata']['invoice_number'].append(detection)
        elif 'Invoice Date' in field_type:
            gst_data['invoice_metadata']['invoice_date'].append(detection)
        elif 'Total Amount' in field_type:
            gst_data['invoice_metadata']['total_amount'].append(detection)
        elif 'PO' in field_type:
            gst_data['invoice_metadata']['po_number'].append(detection)
        elif 'Name' in field_type:
            gst_data['business_information']['merchant_name'].append(detection)
        elif 'Address' in field_type:
            gst_data['business_information']['merchant_address'].append(detection)
        elif 'GST Number' in field_type:
            gst_data['business_information']['gst_numbers'].append(detection)
        elif 'CGST' in field_type:
            gst_data['tax_information']['cgst'].append(detection)
        elif 'SGST' in field_type:
            gst_data['tax_information']['sgst'].append(detection)
        elif 'IGST' in field_type:
            gst_data['tax_information']['igst'].append(detection)
        elif 'Total GST' in field_type:
            gst_data['tax_information']['total_gst'].append(detection)
        elif 'TCS' in field_type:
            gst_data['tax_information']['tcs'].append(detection)
        elif 'Compensation Cess' in field_type:
            gst_data['tax_information']['compensation_cess'].append(detection)
