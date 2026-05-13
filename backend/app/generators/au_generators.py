import random,re
from typing import List, Dict, Union, Optional

# Weights for checksum calculations
ABN_WEIGHTS = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
ACN_WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 1]
TFN_WEIGHTS_FIRST_8 = [1, 4, 3, 7, 5, 8, 6, 9] # For the first 8 digits
TFN_WEIGHT_9TH_DIGIT = 10 # For the 9th digit
MEDICARE_CHECKSUM_WEIGHTS = [1, 3, 7, 9, 1, 3, 7, 9, 1]

def _calculate_abn_checksum_digit(base_digits):
    """
    Helper to calculate the final checksum part for ABN.
    The full ABN validation is (sum_of_weighted_digits % 89) == 0.
    This function finds the 11th digit.
    """
    # First digit processing
    processed_first_digit = base_digits[0] - 1
    
    current_sum = processed_first_digit * ABN_WEIGHTS[0]
    for i in range(1, 10): # Next 9 digits (d2 to d10)
        current_sum += base_digits[i] * ABN_WEIGHTS[i]
        
    # We need (current_sum + d11 * 19) % 89 == 0
    # So, d11 * 19 % 89 = (89 - (current_sum % 89)) % 89
    target_remainder = (89 - (current_sum % 89)) % 89
    
    for d11 in range(10): # Try d11 from 0 to 9
        if (d11 * ABN_WEIGHTS[10]) % 89 == target_remainder:
            return d11
            
    return None # Should not happen if logic is correct and a solution exists

def generate_abn():
    """
    Generates a pseudo-random 11-digit Australian Business Number (ABN).
    The first digit cannot be 0.
    """
    # Generate first digit (1-9)
    d1 = random.randint(1, 9)
    # Generate next 9 digits (0-9) for d2 to d10
    remaining_9_digits = [random.randint(0, 9) for _ in range(9)]
    
    base_10_digits = [d1] + remaining_9_digits
    
    checksum_digit = _calculate_abn_checksum_digit(base_10_digits)
    
    if checksum_digit is not None:
        return "".join(map(str, base_10_digits + [checksum_digit]))
    else:
        # Fallback or error, though _calculate_abn_checksum_digit should ideally always find one.
        # For simplicity, we might retry or raise an error. Here, let's retry once.
        return generate_abn() 

def _calculate_acn_checksum_digit(digits):
    """Calculates the checksum digit for an 8-digit ACN base."""
    s = sum(d * w for d, w in zip(digits, ACN_WEIGHTS))
    remainder = s % 10
    check_digit = (10 - remainder) % 10
    return check_digit

def generate_acn():
    """
    Generates a pseudo-random 9-digit Australian Company Number (ACN).
    """
    first_8_digits = [random.randint(0, 9) for _ in range(8)]
    check_digit = _calculate_acn_checksum_digit(first_8_digits)
    return "".join(map(str, first_8_digits + [check_digit]))

def _calculate_tfn_checksum_digit(digits):
    """
    Calculates the checksum digit for an 8-digit TFN base to form a 9-digit TFN.
    Sum of (digit * weight) % 11 must be 0.
    """
    current_sum = sum(d * w for d, w in zip(digits, TFN_WEIGHTS_FIRST_8))
    
    # We need (current_sum + d9 * 10) % 11 == 0
    # So, d9 * 10 % 11 = (11 - (current_sum % 11)) % 11
    # Since 10 % 11 is -1 % 11:
    # -d9 % 11 = (11 - (current_sum % 11)) % 11
    # d9 % 11 = (current_sum % 11) % 11
    
    target_mod_11_for_d9 = (current_sum % 11) # This is what d9 needs to be to make the sum_mod_11 zero
                                            # if d9's weight was -1.
                                            # (S + d9*w9) % 11 = 0 => d9*w9 % 11 = (-S) % 11
                                            # d9*10 % 11 = (-current_sum) % 11

    for d9 in range(10): # Try d9 from 0 to 9
        if (d9 * TFN_WEIGHT_9TH_DIGIT) % 11 == (11 - (current_sum % 11)) % 11:
            return d9
            
    return None # Should ideally find a digit

def generate_tfn():
    """
    Generates a pseudo-random 9-digit Tax File Number (TFN).
    """
    # TFNs can be 8 or 9 digits. We'll generate 9-digit ones with a checksum.
    first_8_digits = [random.randint(0, 9) for _ in range(8)]
    
    # Ensure the first digit is not 0 for more realistic test TFNs, though not a strict rule for all TFNs.
    if first_8_digits[0] == 0:
        first_8_digits[0] = random.randint(1,9)

    check_digit = _calculate_tfn_checksum_digit(first_8_digits)
    if check_digit is not None:
        return "".join(map(str, first_8_digits + [check_digit]))
    else:
        # Fallback or error
        return generate_tfn() # Retry

def _calculate_medicare_checksum(digits):
    """Calculates checksum for the first 9 digits of a Medicare number."""
    s = sum(d * w for d, w in zip(digits, MEDICARE_CHECKSUM_WEIGHTS))
    return (10 - (s % 10)) % 10

def generate_medicare_number():
    """
    Generates a pseudo-random 11-digit Australian Medicare number for testing.
    The format is a 10-digit card number (9 base digits + 1 checksum digit)
    followed by a 1-digit Individual Reference Number (IRN).
    """
    # Generate the first 9 digits of the Medicare card number
    # Ensure the first digit isn't 0 for more realism
    first_digit = random.randint(1, 9)
    next_8_digits = [random.randint(0, 9) for _ in range(8)]
    first_9_digits = [first_digit] + next_8_digits

    # Calculate the 10th digit (checksum)
    checksum_digit = _calculate_medicare_checksum(first_9_digits)

    # Generate the 11th digit (Individual Reference Number - IRN), typically 1-9
    irn_digit = random.randint(1, 9)

    return "".join(map(str, first_9_digits + [checksum_digit, irn_digit]))

def generate_driving_licence_number(state: str = None):
    """
    Generates a pseudo-random test driving licence number, optionally for a specific Australian state/territory.
    Note: Actual Australian driving licence formats vary significantly by state.
    This provides plausible-looking mock numbers for testing.

    Args:
        state (str, optional): The state/territory code (e.g., "NSW", "VIC"). Defaults to None for a generic format.

    Returns:
        str: A generated test driving licence number.
    """
    state = state.upper() if state else "GENERIC"

    if state == "NSW": # New South Wales
        # Typically 8 digits, often starting with 4 or 5
        return str(random.choice([4, 5])) + "".join([str(random.randint(0, 9)) for _ in range(7)])
    elif state == "VIC": # Victoria
        # Often 9 characters, can be alphanumeric. Let's do 1 letter + 8 digits.
        return random.choice("ABCDEFGHJKLMNPRSTUVWXYZ") + "".join([str(random.randint(0, 9)) for _ in range(8)])
    elif state == "QLD": # Queensland
        # Often 8 or 9 digits. Let's do 8 digits, starting with 1, 2, or 3.
        return str(random.randint(1, 3)) + "".join([str(random.randint(0, 9)) for _ in range(7)])
    elif state == "WA": # Western Australia
        # Often 9 digits. Let's prefix with 'W'.
        return "W" + "".join([str(random.randint(0, 9)) for _ in range(8)])
    elif state == "SA": # South Australia
        # Typically 9 digits. Let's start with 6.
        return "6" + "".join([str(random.randint(0, 9)) for _ in range(8)])
    elif state == "TAS": # Tasmania
        # Typically 7 digits.
        return "".join([str(random.randint(0, 9)) for _ in range(7)])
    elif state == "ACT": # Australian Capital Territory
        # Often 7 or 8 digits. Let's use 'Y' + 6 digits.
        return "Y" + "".join([str(random.randint(0, 9)) for _ in range(6)])
    elif state == "NT": # Northern Territory
        # Can be alphanumeric. Let's do 2 letters + 6 digits.
        return random.choice("ABCDEFGHJKLMNPRSTUVWXYZ") + random.choice("ABCDEFGHJKLMNPRSTUVWXYZ") + "".join([str(random.randint(0, 9)) for _ in range(6)])
    else: # Generic or unknown state
        # Fallback to a generic 9-digit number
        return "".join([str(random.randint(0, 9)) for _ in range(9)])
    

BANK_BSB_PREFIXES = {
    "CBA": "06", # Commonwealth Bank
    "WBC": "03", # Westpac
    "NAB": "08", # National Australia Bank
    "ANZ": "01", # ANZ
    "BEN": "633",# Bendigo Bank
    "BOQ": "12", # Bank of Queensland
    "SUN": "484",# Suncorp
    "ING": "923",# ING Australia
    "HSBC": "34",# HSBC Bank Australia
    "MQG": "182",# Macquarie Bank (example, often 182-xxx)
    "GENERIC": None # For a generic BSB
}

def generate_bank_account_number(bank_code: str = None):
    """
    Generates a pseudo-random Australian Bank Account Number (BSB and Account Number) for testing.
    Includes a selection of major banks.

    Disclaimer: These numbers are for testing and development purposes ONLY.
    They are not real bank account numbers and should not be used for actual transactions.
    If you face any issue or have any concern, please send an email to contact@globalsqa.com

    Args:
        bank_code (str, optional): The code for a specific bank (e.g., "CBA", "WBC").
                                   Defaults to None for a generic BSB.

    Returns:
        dict: A dictionary containing 'bank_name', 'bsb', and 'account_number'.
    """
    bank_code = bank_code.upper() if bank_code else "GENERIC"
    prefix = BANK_BSB_PREFIXES.get(bank_code)

    if prefix:
        bsb_suffix_len = 6 - len(prefix)
        bsb = prefix + "".join([str(random.randint(0, 9)) for _ in range(bsb_suffix_len)])
    else: # Generic BSB
        bsb = "".join([str(random.randint(0, 9)) for _ in range(6)])

    account_number_length = random.randint(6, 9) # Account numbers are typically 6-9 digits
    account_number = "".join([str(random.randint(0, 9)) for _ in range(account_number_length)])

    return {
        "bank_code": bank_code if bank_code != "GENERIC" else "Generic Bank",
        "bsb": bsb,
        "account_number": account_number
    }

def validate_abn(abn_str: str) -> tuple[bool, str]:
    """Validates an Australian Business Number (ABN)."""
    abn_str = abn_str.replace(" ", "")
    if not abn_str.isdigit() or len(abn_str) != 11:
        return False, "ABN must be 11 digits."

    digits = [int(d) for d in abn_str]
    
    # Apply ABN validation rule: (sum_of_weighted_digits % 89) == 0
    # First digit is processed as (digit - 1)
    processed_digits = [digits[0] - 1] + digits[1:]
    
    weighted_sum = sum(d * w for d, w in zip(processed_digits, ABN_WEIGHTS))
    
    if weighted_sum % 89 == 0:
        return True, "Valid ABN."
    else:
        return False, "Invalid ABN checksum."

def validate_acn(acn_str: str) -> tuple[bool, str]:
    """Validates an Australian Company Number (ACN)."""
    acn_str = acn_str.replace(" ", "")
    if not acn_str.isdigit() or len(acn_str) != 9:
        return False, "ACN must be 9 digits."

    digits = [int(d) for d in acn_str]
    first_8_digits = digits[:-1]
    provided_checksum = digits[-1]
    
    expected_checksum = _calculate_acn_checksum_digit(first_8_digits)
    
    if provided_checksum == expected_checksum:
        return True, "Valid ACN."
    else:
        return False, "Invalid ACN checksum."

def validate_tfn(tfn_str: str) -> tuple[bool, str]:
    """Validates a 9-digit Australian Tax File Number (TFN)."""
    tfn_str = tfn_str.replace(" ", "")
    if not tfn_str.isdigit() or len(tfn_str) != 9:
        return False, "TFN must be 9 digits for this validation."

    digits = [int(d) for d in tfn_str]
    
    # Apply TFN validation rule: (sum_of_weighted_digits % 11) == 0
    # Weights for all 9 digits: TFN_WEIGHTS_FIRST_8 + [TFN_WEIGHT_9TH_DIGIT]
    # However, the TFN_WEIGHT_9TH_DIGIT is the weight for the 9th digit itself, not part of a sequence for sum.
    # The _calculate_tfn_checksum_digit finds the 9th digit.
    # So, we check if the provided 9th digit matches the calculated one.

    first_8_digits = digits[:-1]
    provided_checksum = digits[-1]

    expected_checksum = _calculate_tfn_checksum_digit(first_8_digits)

    if expected_checksum is not None and provided_checksum == expected_checksum:
        return True, "Valid TFN."
    else:
        return False, "Invalid TFN checksum or format."

def validate_medicare_number(medicare_str: str) -> tuple[bool, str]:
    """Validates an 11-digit Australian Medicare Number."""
    medicare_str = medicare_str.replace(" ", "")
    if not medicare_str.isdigit() or len(medicare_str) != 11:
        return False, "Medicare number must be 11 digits."

    digits = [int(d) for d in medicare_str]
    
    first_9_digits = digits[:9]
    provided_checksum = digits[9] # 10th digit is the checksum
    irn = digits[10] # 11th digit is the IRN

    if not (1 <= irn <= 9):
        return False, "Invalid Medicare IRN (must be 1-9)."

    expected_checksum = _calculate_medicare_checksum(first_9_digits)
    
    if provided_checksum == expected_checksum:
        return True, "Valid Medicare number."
    else:
        return False, "Invalid Medicare number checksum."

def validate_driving_licence_number(licence_str: str, state: str = None) -> tuple[bool, str]:
    """
    Validates a test driving licence number against generated formats.
    Note: This validates against the patterns used by the generator, not official state rules.
    """
    licence_str = licence_str.replace(" ", "")
    state_upper = state.upper() if state else "GENERIC"
    
    # Basic checks based on generated patterns
    if state_upper == "NSW":
        if not (licence_str.isdigit() and len(licence_str) == 8 and licence_str[0] in ['4', '5']):
            return False, "Invalid NSW test licence format."
    elif state_upper == "VIC":
        if not (len(licence_str) == 9 and licence_str[0].isalpha() and licence_str[1:].isdigit()):
            return False, "Invalid VIC test licence format."
    elif state_upper == "QLD":
        if not (licence_str.isdigit() and len(licence_str) == 8 and licence_str[0] in ['1', '2', '3']):
            return False, "Invalid QLD test licence format."
    elif state_upper == "WA":
        if not (len(licence_str) == 9 and licence_str[0] == 'W' and licence_str[1:].isdigit()):
            return False, "Invalid WA test licence format."
    elif state_upper == "SA":
        if not (licence_str.isdigit() and len(licence_str) == 9 and licence_str[0] == '6'):
            return False, "Invalid SA test licence format."
    elif state_upper == "TAS":
        if not (licence_str.isdigit() and len(licence_str) == 7):
            return False, "Invalid TAS test licence format."
    elif state_upper == "ACT":
        if not (len(licence_str) == 7 and licence_str[0] == 'Y' and licence_str[1:].isdigit()):
            return False, "Invalid ACT test licence format."
    elif state_upper == "NT":
        if not (len(licence_str) == 8 and licence_str[0:2].isalpha() and licence_str[2:].isdigit()):
            return False, "Invalid NT test licence format."
    elif state_upper == "GENERIC":
        if not (licence_str.isdigit() and len(licence_str) == 9):
            return False, "Invalid generic test licence format (must be 9 digits)."
    else:
        return False, "Unknown state for licence validation."
        
    return True, f"Valid test licence format for {state_upper}."

def validate_bank_account_number(bsb_str: str, account_number_str: str, bank_code: str = None) -> tuple[bool, str]:
    """Validates test BSB and Account Number."""
    bsb_str = bsb_str.replace(" ", "")
    account_number_str = account_number_str.replace(" ", "")
    if not bsb_str.isdigit() or len(bsb_str) != 6:
        return False, "BSB must be 6 digits."

    if bank_code:
        bank_code_upper = bank_code.upper()
        prefix = BANK_BSB_PREFIXES.get(bank_code_upper)
        if prefix and not bsb_str.startswith(prefix):
            return False, f"BSB does not match prefix for bank {bank_code_upper}."
        elif not prefix and bank_code_upper != "GENERIC":
            return False, f"Unknown bank code {bank_code_upper} for BSB prefix validation."

    if not account_number_str.isdigit() or not (6 <= len(account_number_str) <= 9):
        return False, "Account number must be 6-9 digits."

    return True, "Valid test bank account format."
