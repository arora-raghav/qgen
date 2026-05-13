import random
import string
import re
from typing import List, Dict, Union, Optional
from datetime import datetime, timedelta

# --- Passport Number ---

# Passport Formats (Based on common formats, not exhaustive or official):
# 'regex': Regex pattern for validation.
# 'example_generator': A simple function to generate an example matching the regex.
PASSPORT_FORMATS = {
    "USA": {"regex": r"^\d{9}$", "example_generator": lambda: "".join(random.choices(string.digits, k=9))},  # 9 digits
    "GBR": {"regex": r"^[A-Z0-9]{9}$", "example_generator": lambda: "".join(random.choices(string.ascii_uppercase + string.digits, k=9))},  # 9 alphanumeric characters (UK)
    "IND": {"regex": r"^[A-Z]\d{7}$", "example_generator": lambda: random.choice(string.ascii_uppercase) + "".join(random.choices(string.digits, k=7))},  # 1 letter + 7 digits (India)
    "DEU": {"regex": r"^[A-Z0-9]{9}$", "example_generator": lambda: "".join(random.choices(string.ascii_uppercase + string.digits, k=9))}, # 9 alphanumeric characters (Germany) - Simplified
    "CAN": {"regex": r"^[A-Z]{2}\d{6}$", "example_generator": lambda: "".join(random.choices(string.ascii_uppercase, k=2)) + "".join(random.choices(string.digits, k=6))},  # 2 letters + 6 digits
    "AUS": {"regex": r"^[A-Z]\d{7}$", "example_generator": lambda: random.choice(string.ascii_uppercase) + "".join(random.choices(string.digits, k=7))},  # 1 letter + 7 digits (e.g., N1234567)
    "CHN": {"regex": r"^[EG]\d{8}$", "example_generator": lambda: random.choice(['E', 'G']) + "".join(random.choices(string.digits, k=8))},  # 1 letter (E or G) + 8 digits
}

def generate_passport_number(country_code: str, count: int = 1) -> Union[Dict[str, str], List[Dict[str, str]]]:
    """
    Generates passport numbers for a specific country.
    Supported countries: USA, GBR, IND, DEU, CAN, AUS, CHN.

    Args:
        country_code (str): The 3-letter country code (ISO 3166-1 alpha-3).
        count (int): The number of passport numbers to generate. Defaults to 1.

    Returns:
        Union[Dict[str, str], List[Dict[str, str]]]:  A dictionary or list of dictionaries
                                                  containing the generated passport numbers.
    Raises:
        ValueError: If the country_code is not supported for generation.
    """
    country_code_upper = country_code.upper()
    spec = PASSPORT_FORMATS.get(country_code_upper)

    if not spec:
        raise ValueError(f"Passport generation for country code '{country_code}' is not supported.")

    def _generate_single_item():
        # Use the example_generator from the spec for generation
        return {"passport_number": spec["example_generator"]()}

    if count == 1:
        return _generate_single_item()
    else:
        return [_generate_single_item() for _ in range(count)]

def validate_passport_number(passport_number: str, country_code: str) -> tuple[bool, str, Optional[str]]:
    """
    Validates a Passport number format for a given country.
    Supported countries: USA, GBR, IND, DEU, CAN, AUS, CHN.

    Note: This performs format validation based on predefined regex.
    It does NOT include check digit algorithms, which are complex and vary.
    """
    country_code_upper = country_code.upper()
    spec = PASSPORT_FORMATS.get(country_code_upper)

    if not spec:
        return False, f"Validation for country code '{country_code_upper}' is not supported.", None

    passport_format_regex = spec["regex"]
    cleaned_number = re.sub(r'\s+', '', passport_number).upper()

    if re.fullmatch(passport_format_regex, cleaned_number):
        return True, f"Passport number format is valid for {country_code_upper}.", cleaned_number
    return False, f"Passport number does not match the expected format for {country_code_upper}.", None

# --- Credit Card Number ---

def _calculate_luhn_check_digit(partial_card_number: str) -> str:
    """Calculates the Luhn check digit for a partial card number."""
    digits = [int(d) for d in partial_card_number]
    # Double every second digit from the right
    for i in range(len(digits) - 1, -1, -2):
        digits[i] *= 2
        if digits[i] > 9:
            digits[i] -= 9
    # Sum all digits
    total = sum(digits)
    # The check digit is the amount needed to reach a multiple of 10
    check_digit = (10 - (total % 10)) % 10
    return str(check_digit)

def _generate_single_credit_card_details(network: str) -> Dict[str, str]:
    """Helper to generate a single credit card number, CVV, and expiry date."""
    network_upper = network.upper()

    if network_upper == "VISA":
        prefix = "4"
        length = 16
        cvv_length = 3
    elif network_upper == "MASTERCARD":
        prefixes = ["51", "52", "53", "54", "55"] + [str(i) for i in range(2221, 2721)]
        prefix = random.choice(prefixes)
        length = 16
        cvv_length = 3
    elif network_upper == "AMEX":
        prefix = random.choice(["34", "37"])
        length = 15
        cvv_length = 4
    elif network_upper == "DISCOVER":
        # Simplified Discover prefixes for generation
        prefixes = ["6011", "65"] + [str(i) for i in range(644, 650)] \
                   + [f"622{i:03d}" for i in range(126, 926)] # 622126–622925
        prefix = random.choice(prefixes)
        length = 16
        cvv_length = 3
    elif network_upper == "UNIONPAY":
        prefix = "62"
        length = random.choice(range(16, 20)) # 16-19
        cvv_length = 3
    elif network_upper == "RUPAY":
        prefix = random.choice(["60", "65", "81", "82"])
        length = 16
        cvv_length = 3
    else:
        raise ValueError(f"Unsupported credit card network: {network}")

    remaining_len = length - len(prefix) - 1
    if remaining_len < 0: # Handle cases where prefix might be too long for min length (e.g., UnionPay 16-19)
         # Adjust length if prefix is too long
         length = len(prefix) + 1 + random.randint(0, 3) # Ensure minimum length allows for prefix + check digit + at least 0-3 random digits
         remaining_len = length - len(prefix) - 1
         if remaining_len < 0: remaining_len = 0 # Should not happen with correct prefixes/lengths

    partial_num = prefix + "".join(random.choices(string.digits, k=remaining_len))

    check_digit = _calculate_luhn_check_digit(partial_num)
    card_number = partial_num + check_digit

    # Generate CVV
    cvv = "".join(random.choices(string.digits, k=cvv_length))

    # Generate Expiry Date (MM/YY format, 1-5 years in the future)
    current_year = datetime.now().year
    expiry_year = random.randint(current_year + 1, current_year + 5)
    expiry_month = random.randint(1, 12)
    expiry_date_str = f"{expiry_month:02d}/{str(expiry_year)[-2:]}"

    return {"credit_card_number": card_number, "cvv": cvv, "expiry_date": expiry_date_str, "network": network_upper}


def generate_credit_card_number(network: str, count: int = 1) -> Union[Dict[str, str], List[Dict[str, str]]]:
    """
    Generates credit card numbers for a specific network, including CVV and expiry date.
    Supported networks: VISA, MASTERCARD, AMEX, DISCOVER, UNIONPAY, RUPAY.

    Args:
        network (str): The credit card network.
        count (int): The number of credit card details to generate.

    Returns:
        Union[Dict[str, str], List[Dict[str, str]]]: A dictionary or list of dictionaries.
    """
    def _generate_single_item():
        return _generate_single_credit_card_details(network)

    if count == 1:
        return _generate_single_item()
    else:
        return [_generate_single_item() for _ in range(count)]

# --- IBAN (International Bank Account Number) ---

# IBAN Country Specifications (Based on SWIFT IBAN Registry and common formats):
# 'bban_parts': A list of tuples, where each tuple is (length, char_type).
# char_type: 'N' (Numeric), 'A' (Uppercase Alphabetic), 'C' (Uppercase Alphanumeric)
# 'total_iban_length': The total length of the IBAN for that country (Country Code + Check Digits + BBAN).
IBAN_COUNTRY_SPECS = {
    "AT": {"bban_parts": [(5, "N"), (11, "N")], "total_iban_length": 20},  # Austria: Bank Code (5N), Account Number (11N)
    "AU": {"bban_parts": [(4, "A"), (6, "N"), (9, "N")], "total_iban_length": 23},  # Australia: Bank Identifier (4A), BSB (6N), Account Number (9N)
    "BE": {"bban_parts": [(3, "N"), (7, "N"), (2, "N")], "total_iban_length": 16},  # Belgium: Bank Code (3N), Account Number (7N), Check Digits (2N)
    "CH": {"bban_parts": [(5, "N"), (12, "C")], "total_iban_length": 21},  # Switzerland: Bank Code (5N), Account Number (12C)
    "CZ": {"bban_parts": [(4, "N"), (6, "N"), (10, "N")], "total_iban_length": 24},  # Czech Republic: Bank Code (4N), Branch Code (6N), Account Number (10N)
    "DE": {"bban_parts": [(8, "N"), (10, "N")], "total_iban_length": 22},  # Germany: Bank Code (8N), Account Number (10N)
    "DK": {"bban_parts": [(4, "N"), (9, "N"), (1, "N")], "total_iban_length": 18},  # Denmark: Bank Code (4N), Account Number (9N), National Check Digit (1N)
    "ES": {"bban_parts": [(4, "N"), (4, "N"), (2, "N"), (10, "N")], "total_iban_length": 24},  # Spain: Bank Code (4N), Branch Code (4N), National Check Digits (2N), Account Number (10N)
    "FI": {"bban_parts": [(6, "N"), (7, "N"), (1, "N")], "total_iban_length": 18},  # Finland: Bank Code (6N), Account Number (7N), National Check Digit (1N)
    "FR": {"bban_parts": [(5, "N"), (5, "N"), (11, "C"), (2, "N")], "total_iban_length": 27},  # France: Bank Code (5N), Branch Code (5N), Account Number (11C), RIB Key (2N)
    "GB": {"bban_parts": [(4, "A"), (6, "N"), (8, "N")], "total_iban_length": 22},  # UK: Bank Code (4A), Sort Code (6N), Account Number (8N)
    "HU": {"bban_parts": [(3, "N"), (4, "N"), (1, "N"), (15, "N"), (1, "N")], "total_iban_length": 28}, # Hungary: Bank (3N), Branch (4N), Check (1N), Account (15N), Check (1N)
    "IE": {"bban_parts": [(4, "A"), (6, "N"), (8, "N")], "total_iban_length": 22},  # Ireland: Bank Code (4A), Sort Code (6N), Account Number (8N)
    "IT": {"bban_parts": [(1, "A"), (5, "N"), (5, "N"), (12, "C")], "total_iban_length": 27},  # Italy: National Check Character (1A), Bank Code (5N), Branch Code (5N), Account Number (12C)
    "NL": {"bban_parts": [(4, "A"), (10, "N")], "total_iban_length": 18},  # Netherlands: Bank Code (4A), Account Number (10N)
    "NO": {"bban_parts": [(4, "N"), (6, "N"), (1, "N")], "total_iban_length": 15},  # Norway: Bank Code (4N), Account Number (6N), National Check Digit (1N)
    "PL": {"bban_parts": [(3, "N"), (4, "N"), (1, "N"), (16, "N")], "total_iban_length": 28},  # Poland: Bank Code (3N), Branch (4N), National Check (1N), Account (16N) - Simplified, actual is 8N (Bank+Branch) + 16N (Account)
    "PT": {"bban_parts": [(4, "N"), (4, "N"), (11, "N"), (2, "N")], "total_iban_length": 25},  # Portugal: Bank Code (4N), Branch Code (4N), Account Number (11N), National Check Digits (2N)
    "RO": {"bban_parts": [(4, "A"), (16, "C")], "total_iban_length": 24},  # Romania: Bank Code (4A), Account Number (16C)
    "SE": {"bban_parts": [(3, "N"), (16, "N"), (1, "N")], "total_iban_length": 24},  # Sweden: Bank Code (3N), Account Number (16N), National Check Digit (1N)
    "TR": {"bban_parts": [(5, "N"), (1, "C"), (16, "C")], "total_iban_length": 26},  # Turkey: Bank Code (5N), Reserved (1C, usually '0'), Account Number (16C)
}

def _calculate_iban_checksum(country_code: str, bban: str) -> str:
    """Calculates the IBAN checksum (MOD-97-10)."""
    temp_iban = bban + country_code + "00"
    numeric_iban_str = ""
    for char_val in temp_iban:
        if char_val.isdigit():
            numeric_iban_str += char_val
        elif char_val.isalpha():
            numeric_iban_str += str(ord(char_val.upper()) - ord('A') + 10)
        # Other characters are typically not allowed or handled by pre-validation

    try:
        remainder = int(numeric_iban_str) % 97
        check_digits = 98 - remainder
        return f"{check_digits:02d}"
    except ValueError: # Should not happen if BBAN and country code are valid
        return "XX" # Error placeholder

def _generate_random_bban_part(length: int, char_type: str) -> str:
    """Generates a random string for a part of BBAN based on character type."""
    if char_type == "N":
        return "".join(random.choices(string.digits, k=length))
    elif char_type == "A":
        return "".join(random.choices(string.ascii_uppercase, k=length))
    elif char_type == "C":
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
    # Fallback for an undefined char_type, though specs should be precise
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def _generate_random_bban_from_parts(bban_parts: List[tuple[int, str]]) -> str:
    """Constructs a BBAN string from its defined parts."""
    bban_str = ""
    for length, char_type in bban_parts:
        bban_str += _generate_random_bban_part(length, char_type)
    return bban_str

def _generate_single_iban(country_code: str) -> Dict[str, str]:
    """Generates a single IBAN with its components for a given country."""
    country_code_upper = country_code.upper()
    spec = IBAN_COUNTRY_SPECS.get(country_code_upper)

    if not spec:
        raise ValueError(f"IBAN generation for country code '{country_code}' is not supported or specs are missing.")

    bban = _generate_random_bban_from_parts(spec["bban_parts"])
    check_digits = _calculate_iban_checksum(country_code_upper, bban)

    iban = f"{country_code_upper}{check_digits}{bban}"
    return {"iban": iban, "country_code": country_code_upper, "bban": bban, "check_digits": check_digits}

def generate_iban(country_code: str, count: int = 1) -> Union[Dict[str, str], List[Dict[str, str]]]:
    """
    Generates IBAN(s) for a specified country.
    Supported countries are defined in IBAN_COUNTRY_SPECS.

    Args:
        country_code (str): The 2-letter ISO country code.
        count (int): Number of IBANs to generate.

    Returns:
        A dictionary or list of dictionaries with IBAN details.

    Raises:
        ValueError: If the country_code is not supported.
    """
    items = [_generate_single_iban(country_code) for _ in range(count)]
    return items[0] if count == 1 else items

def validate_iban(iban: str) -> tuple[bool, str, Optional[str]]:
    """
    Validates an IBAN structure (length, country code, BBAN format) and checksum (MOD-97-10).
    Supported countries are defined in IBAN_COUNTRY_SPECS.
    """
    iban_cleaned = iban.replace(" ", "").upper()

    if not iban_cleaned.isalnum():
        return False, "IBAN contains invalid characters (must be alphanumeric).", None

    country_code = iban_cleaned[:2]
    spec = IBAN_COUNTRY_SPECS.get(country_code)

    if not spec:
        return False, f"Country code '{country_code}' is not supported for detailed IBAN validation.", None

    if len(iban_cleaned) != spec["total_iban_length"]:
        return False, f"Invalid IBAN length for {country_code}. Expected {spec['total_iban_length']}, got {len(iban_cleaned)}.", None

    # Validate BBAN structure part-by-part
    bban_from_iban = iban_cleaned[4:]
    current_pos = 0
    for part_len, part_type in spec["bban_parts"]:
        part_str = bban_from_iban[current_pos : current_pos + part_len]

        if len(part_str) != part_len: # Should be caught by total length check, but good for safety
             return False, f"BBAN structure error for {country_code} (part length mismatch).", None

        if part_type == "N" and not part_str.isdigit():
            return False, f"BBAN part '{part_str}' for {country_code} expected numeric.", None
        if part_type == "A" and not part_str.isalpha():
            return False, f"BBAN part '{part_str}' for {country_code} expected alphabetic.", None
        if part_type == "C" and not part_str.isalnum(): # This check is somewhat redundant if the whole IBAN is alnum, but good for part-specific logic
             return False, f"BBAN part '{part_str}' for {country_code} expected alphanumeric.", None
        current_pos += part_len

    if current_pos != len(bban_from_iban): # Ensure all parts of BBAN were consumed
        return False, f"BBAN structure error for {country_code} (total BBAN part length mismatch).", None

    # Validate MOD-97 checksum
    rearranged_iban = iban_cleaned[4:] + iban_cleaned[:4]
    numeric_iban_str = "".join(str(ord(char_val) - ord('A') + 10) if char_val.isalpha() else char_val for char_val in rearranged_iban)

    try:
        if int(numeric_iban_str) % 97 == 1:
            return True, "Valid IBAN.", iban_cleaned
        else:
            return False, "Invalid IBAN checksum.", None
    except ValueError: # Should not happen if previous checks pass
        return False, "IBAN contains invalid characters after conversion for checksum.", None
