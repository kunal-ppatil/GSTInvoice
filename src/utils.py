import cv2
import numpy as np
import pandas as pd
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
import json
import os
from datetime import datetime
from config import Config

def create_annotated_image(image_path, gst_data):
    """Create annotated image with detection bounding boxes"""
    try:
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            return None
            
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Create matplotlib figure
        fig, ax = plt.subplots(1, 1, figsize=(15, 10))
        ax.imshow(image_rgb)
        ax.set_title('GST Invoice - Detected Fields', fontsize=16, fontweight='bold')
        ax.axis('off')
        
        # Colors for different categories
        colors = {
            'invoice_metadata': '#FF6B6B',
            'business_information': '#4ECDC4',
            'tax_information': '#45B7D1',
            'default': '#FFA726'
        }
        
        # Draw bounding boxes
        for category, fields in gst_data.items():
            if category == 'summary':
                continue
            
            color = colors.get(category, colors['default'])
            
            for field_type, detections in fields.items():
                for detection in detections:
                    if 'bbox' in detection:
                        bbox = detection['bbox']
                        x1, y1, x2, y2 = bbox
                        
                        # Draw rectangle
                        rect = patches.Rectangle((x1, y1), x2-x1, y2-y1, 
                                               linewidth=2, edgecolor=color, 
                                               facecolor='none', alpha=0.8)
                        ax.add_patch(rect)
                        
                        # Add text label
                        label = f"{detection['field_type']}: {detection['text_content'][:15]}..."
                        ax.text(x1, y1-5, label, color=color, fontsize=8, 
                               weight='bold', bbox=dict(boxstyle="round,pad=0.3", 
                               facecolor='white', alpha=0.8))
        
        # Convert to PIL Image
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
        buf.seek(0)
        
        pil_image = Image.open(buf)
        plt.close()
        
        return pil_image
        
    except Exception as e:
        print(f"Error creating annotated image: {str(e)}")
        return None

def create_results_dataframe(gst_data):
    """Create structured DataFrame from GST extraction results"""
    try:
        all_detections = []
        
        for category, fields in gst_data.items():
            if category == 'summary':
                continue
            
            for field_type, detections in fields.items():
                for detection in detections:
                    confidence = detection['confidence']
                    
                    # Confidence level
                    if confidence >= 0.8:
                        conf_level = "High"
                        conf_emoji = "🟢"
                    elif confidence >= 0.6:
                        conf_level = "Medium"
                        conf_emoji = "🟡"
                    else:
                        conf_level = "Low"
                        conf_emoji = "🔴"
                    
                    all_detections.append({
                        'Category': category.replace('_', ' ').title(),
                        'Field Type': detection['field_type'],
                        'Extracted Text': detection['text_content'],
                        'Confidence': f"{confidence:.3f}",
                        'Confidence Level': f"{conf_emoji} {conf_level}"
                    })
        
        if not all_detections:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_detections)
        return df.sort_values('Confidence', ascending=False)
        
    except Exception as e:
        print(f"Error creating results DataFrame: {str(e)}")
        return pd.DataFrame()

def save_results(gst_data, filename):
    """Save extraction results to files"""
    try:
        results_dir = Config.RESULTS_DIR
        os.makedirs(results_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = os.path.splitext(filename)[0]
        
        # Save JSON
        json_path = os.path.join(results_dir, f"{base_name}_{timestamp}.json")
        with open(json_path, 'w') as f:
            json.dump(gst_data, f, indent=2)
        
        print(f"Results saved to {results_dir}")
        
    except Exception as e:
        print(f"Error saving results: {str(e)}")
