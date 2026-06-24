import re
from typing import Dict, Any

# Map of GST State Codes to Names
GST_STATE_CODES = {
    "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana",
    "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
    "13": "Nagaland", "14": "Manipur", "15": "Mizoram",
    "16": "Tripura", "17": "Meghalaya", "18": "Assam",
    "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
    "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "26": "Dadra & Nagar Haveli and Daman & Diu", "27": "Maharashtra",
    "28": "Andhra Pradesh (New)", "29": "Karnataka", "30": "Goa",
    "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu",
    "34": "Puducherry", "35": "Andaman & Nicobar", "36": "Telangana",
    "37": "Andhra Pradesh", "38": "Ladakh"
}

def char_to_val(c: str) -> int:
    """Helper to convert GSTIN character to its Luhn value (0-9 -> 0-9, A-Z -> 10-35)"""
    if '0' <= c <= '9':
        return ord(c) - ord('0')
    elif 'A' <= c <= 'Z':
        return ord(c) - ord('A') + 10
    else:
        raise ValueError(f"Invalid character in GSTIN: {c}")

def val_to_char(v: int) -> str:
    """Helper to convert Luhn value back to GSTIN character"""
    if 0 <= v <= 9:
        return str(v)
    elif 10 <= v <= 35:
        return chr(v - 10 + ord('A'))
    else:
        raise ValueError(f"Invalid Luhn value: {v}")

def verify_gstin_checksum(gstin: str) -> bool:
    """Luhn Mod 36 Checksum Verification for GSTIN"""
    try:
        if len(gstin) != 15:
            return False
        
        gstin = gstin.upper()
        total_sum = 0
        
        # Calculate checksum for the first 14 characters
        for i in range(14):
            val = char_to_val(gstin[i])
            # Multiplier: 1 for odd positions (1st, 3rd, 5th, etc., 0-indexed: 0, 2, 4...)
            # 2 for even positions (2nd, 4th, 6th, etc., 0-indexed: 1, 3, 5...)
            multiplier = 1 if (i % 2 == 0) else 2
            
            prod = val * multiplier
            # Add quotient and remainder of division by 36
            total_sum += (prod // 36) + (prod % 36)
            
        rem = total_sum % 36
        check_val = (36 - rem) % 36
        expected_check_digit = val_to_char(check_val)
        
        return gstin[14] == expected_check_digit
    except Exception:
        return False

def validate_gstin(gstin: str) -> Dict[str, Any]:
    """
    Validates a GSTIN based on:
    - Length (15 characters)
    - State code existence
    - PAN structure
    - Checksum
    """
    if not gstin:
        return {
            "status": "INVALID",
            "message": "GSTIN cannot be empty"
        }
        
    gstin = gstin.strip().upper()
    
    if len(gstin) != 15:
        return {
            "status": "INVALID",
            "message": f"GSTIN must be exactly 15 characters (got {len(gstin)})"
        }
        
    state_code = gstin[0:2]
    pan = gstin[2:12]
    
    # 1. State Code Check
    if state_code not in GST_STATE_CODES:
        return {
            "status": "INVALID",
            "message": f"Invalid State Code: '{state_code}' does not match any Indian State/UT"
        }
    
    # 2. PAN Format Check (5 letters, 4 digits, 1 letter)
    pan_regex = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
    if not re.match(pan_regex, pan):
        return {
            "status": "SUSPICIOUS",
            "message": f"Suspicious PAN format: '{pan}' does not follow standard PAN structure (5 Letters, 4 Digits, 1 Letter)",
            "state_code": state_code,
            "state": GST_STATE_CODES[state_code],
            "pan": pan
        }
        
    # 3. Complete regex format check
    gstin_regex = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
    if not re.match(gstin_regex, gstin):
        # Allow validation even if 14th character is not 'Z', but flag it as suspicious
        checksum_ok = verify_gstin_checksum(gstin)
        if checksum_ok:
            return {
                "status": "VALID",
                "message": "GSTIN format is slightly non-standard but checksum is VALID",
                "state_code": state_code,
                "state": GST_STATE_CODES[state_code],
                "pan": pan
            }
        else:
            return {
                "status": "INVALID",
                "message": "GSTIN pattern is invalid and does not follow standard structure",
                "state_code": state_code,
                "state": GST_STATE_CODES[state_code],
                "pan": pan
            }
            
    # 4. Checksum verification
    if verify_gstin_checksum(gstin):
        return {
            "status": "VALID",
            "message": "GSTIN is VALID and checksum matches",
            "state_code": state_code,
            "state": GST_STATE_CODES[state_code],
            "pan": pan
        }
    else:
        return {
            "status": "INVALID",
            "message": "Invalid GSTIN Checksum digit: Checksum validation failed",
            "state_code": state_code,
            "state": GST_STATE_CODES[state_code],
            "pan": pan
        }

def calculate_gst_values(taxable_value: float, gst_rate: float, is_interstate: bool) -> Dict[str, Any]:
    """Calculates CGST, SGST, IGST and Totals based on tax rules"""
    rate_fraction = gst_rate / 100.0
    total_gst = taxable_value * rate_fraction
    
    if is_interstate:
        igst = total_gst
        cgst = 0.0
        sgst = 0.0
    else:
        igst = 0.0
        cgst = total_gst / 2.0
        sgst = total_gst / 2.0
        
    grand_total = taxable_value + total_gst
    
    return {
        "taxable_value": taxable_value,
        "gst_rate": gst_rate,
        "cgst": cgst,
        "sgst": sgst,
        "igst": igst,
        "total_gst": total_gst,
        "grand_total": grand_total
    }
