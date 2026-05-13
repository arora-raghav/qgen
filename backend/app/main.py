import os
from fastapi import FastAPI, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .generators.au_generators import (
    generate_abn, generate_acn, generate_tfn, generate_medicare_number, 
    generate_driving_licence_number, generate_bank_account_number,
    validate_abn, validate_acn, validate_tfn, validate_medicare_number,
    validate_driving_licence_number, validate_bank_account_number
)
from .generators.international_identifiers import generate_passport_number, validate_passport_number, generate_credit_card_number, generate_iban, validate_iban # Import international functions
from .generators.uuid_generators import generate_uuids, decode_uuid_string # New import for UUIDs

from .auth import get_api_key # Import the authenticator
from .document_routes import router as document_router
from .admin_routes import router as admin_router  # Document processing routes
from typing import List, Dict, Union, Optional
from enum import Enum
app = FastAPI(
    title="Test Data Generator API",
    description="An API to generate various Australian test identifiers (ABN, ACN, TFN, Medicare, Driving Licence, Bank Accounts) for development, demo, or testing purposes.",
    version="0.6.1"  # Increment version for UUID decoding improvements
)

# Add CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://qelab.org",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include document processing routes
app.include_router(document_router, tags=["Document Processing"],include_in_schema=False)
app.include_router(admin_router, tags=["Admin - Document Workspace"],include_in_schema=False)

class CreditCardNetwork(str, Enum):
    VISA = "VISA"
    MASTERCARD = "MASTERCARD"
    AMEX = "AMEX"
    DISCOVER = "DISCOVER"
    UNIONPAY = "UNIONPAY"
    RUPAY = "RUPAY"

class UUIDVersion(int, Enum):
    V1 = 1
    V3 = 3
    V4 = 4
    V5 = 5
    V6 = 6
    V7 = 7
    V8 = 8

class SupportedPassportCountry(str, Enum):
    USA = "USA"
    GBR = "GBR"
    IND = "IND"
    DEU = "DEU"
    CAN = "CAN"
    AUS = "AUS"
    CHN = "CHN"

class IBANSupportedCountry(str, Enum):
    AT = "AT"  # Austria
    AU = "AU"  # Australia
    BE = "BE"  # Belgium
    CH = "CH"  # Switzerland
    CZ = "CZ"  # Czech Republic
    DE = "DE"  # Germany
    DK = "DK"  # Denmark
    ES = "ES"  # Spain
    FI = "FI"  # Finland
    FR = "FR"  # France
    GB = "GB"  # United Kingdom
    HU = "HU"  # Hungary
    IE = "IE"  # Ireland
    IT = "IT"  # Italy
    NL = "NL"  # Netherlands
    NO = "NO"  # Norway
    PL = "PL"  # Poland
    PT = "PT"  # Portugal
    RO = "RO"  # Romania
    SE = "SE"  # Sweden
    TR = "TR"  # Turkey

class AUBank(str, Enum):
    CBA = "CBA"
    WBC = "WBC"
    NAB = "NAB"
    ANZ = "ANZ"
    BEN = "BEN"
    BOQ = "BOQ"
    SUN = "SUN"
    ING = "ING"
    HSBC = "HSBC"
    MQG = "MQG"
    GENERIC = "GENERIC"
    
class AUState(str, Enum):
    NSW = "NSW"
    VIC = "VIC"
    QLD = "QLD"
    WA = "WA"
    SA = "SA"
    TAS = "TAS"
    ACT = "ACT"
    NT = "NT"
    GENERIC = "GENERIC"

@app.get("/")
async def read_root():
    return {
        "message": "Welcome to the Test Number Generator API. Use /docs to see available endpoints.",
        "info": "To use the generation and validation endpoints, please request an API token by emailing contact@globalsqa.com if not done earlier.",
        "note": "This API is for development, demo, or testing purposes only. The generated numbers are not valid for real-world use.",
        "version": "0.2.0"
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify if the API is running.
    """
    return {"status": "ok"}

# --- Pydantic Models for Validation Requests ---
class ABNValidationRequest(BaseModel):
    abn: str = Field(..., description="ABN to validate.")

class ACNValidationRequest(BaseModel):
    acn: str = Field(..., description="ACN to validate.")

class TFNValidationRequest(BaseModel):
    tfn: str = Field(..., description="TFN to validate.")

class MedicareValidationRequest(BaseModel):
    medicare_number: str = Field(..., description="Medicare number to validate.")

class DrivingLicenceValidationRequest(BaseModel):
    driving_licence_number: str = Field(..., description="Driving licence number to validate.")
    state: Optional[AUState] = Field(None, description="Australian state/territory for specific format validation.")

class BankAccountValidationRequest(BaseModel):
    bsb: str = Field(..., description="BSB to validate.")
    account_number: str = Field(..., description="Account number to validate.")
    bank_code: Optional[AUBank] = Field(None, description="Australian bank code for BSB prefix validation.")

class ValidationResponse(BaseModel):
    input_value: Union[str, Dict[str, str]]
    is_valid: bool
    message: str

# --- Pydantic Models for Request/Response Schemas ---

class PassportValidationRequest(BaseModel):
    country_code: SupportedPassportCountry = Field(..., description="The 3-letter country code (ISO 3166-1 alpha-3).")
    passport_number: str = Field(
        ...,
        example="123456789",
        description="The Passport number to validate."
    )

class PassportValidationResponse(BaseModel):
    valid: bool
    message: str
    formatted_value: Optional[str] = Field(None, example="E12345678")

class IBANValidationRequest(BaseModel):
    iban: str = Field(..., example="DE89370400440532013000", description="The IBAN to validate.")

class IBANValidationResponse(BaseModel):
    valid: bool
    message: str
    formatted_value: Optional[str] = Field(None, description="The validated IBAN if valid, otherwise None.")

class IBANDetailsResponse(BaseModel):
    iban: str = Field(..., example="DE89370400440532013000")
    country_code: str = Field(..., example="DE")
    bban: str = Field(..., example="370400440532013000")
    check_digits: str = Field(..., example="89")


class UUIDResponse(BaseModel):
    uuid: str
    version_generated: int

class UUIDDecodedResponse(BaseModel):
    uuid_string: str
    version: Optional[int] = None
    version_details: Optional[str] = Field(None, description="Description of the UUID version.")
    variant: Optional[str] = None
    integer_value: Optional[str] = Field(None, description="The UUID represented as a single large integer string.")
    contents_hex: Optional[str] = Field(None, description="The 16 bytes of the UUID as a colon-separated hex string.")
    contents_semantics: Optional[str] = Field(None, description="A description of the semantics of the UUID's contents based on its version.")
    time_iso: Optional[str] = Field(None, description="Timestamp in ISO 8601 format (for V1, V6, V7)")
    timestamp_value_100ns: Optional[int] = Field(None, description="Raw 100-nanosecond interval timestamp (for V1, V6, V7)")
    node_mac: Optional[str] = Field(None, description="Node MAC address as hex string (for V1, V6)")
    clock_sequence: Optional[int] = Field(None, description="Clock sequence (for V1, V6)")
    fields: Optional[Dict[str, Optional[str]]] = Field(None, description="Raw UUID fields as hex strings")

class UUIDDecodeRequest(BaseModel):
    uuid_string: str = Field(..., description="The UUID string to decode.")

@app.get("/generate/uuid",
         tags=["UUID/GUID"],
         response_model=Union[UUIDResponse, List[UUIDResponse]],
         responses={
             200: {
                 "description": "Successfully generated UUID(s).",
                 "content": {
                     "application/json": {
                         "examples": {
                             "single_v4": {
                                 "summary": "Single UUIDv4",
                                 "value": {"uuid": "123e4567-e89b-12d3-a456-426614174000", "version_generated": 4}
                             },
                             "multiple_v1": {
                                 "summary": "Multiple UUIDv1",
                                 "value": [
                                     {"uuid": "a1b2c3d4-e5f6-11ea-87d0-0242ac130003", "version_generated": 1},
                                     {"uuid": "f0e1d2c3-b4a5-11eb-b378-0242ac130002", "version_generated": 1}
                                 ]
                             }
                         }
                     }
                 }},
             400: {"description": "Invalid input, e.g., unsupported version or invalid parameters."}
         })
async def get_uuid(
    version: Optional[UUIDVersion] = Query(UUIDVersion.V4, description="UUID version to generate. Defaults to V4."),
    count: int = Query(1, ge=1, le=100, description="Number of UUIDs to generate."),
    name: Optional[str] = Query(None, description="Name for V3/V5 UUIDs. If not provided, a random name will be used."),
    namespace: Optional[str] = Query(None, description="Namespace UUID string for V3/V5. If not provided, a random V4 UUID will be used as namespace."),
    node: Optional[str] = Query(None, description="MAC address for V1/V6 UUIDs (e.g., '00:1B:44:11:3A:B7' or '001B44113AB7'). If not provided, a random MAC will be used."),
    api_key: str = Depends(get_api_key)
):
    """
    Generate one or more UUIDs (Universally Unique Identifiers) or GUIDs (Globally Unique Identifiers).
    Supports versions V1, V3, V4 (default), V5, V6, V7, V8.
    - **version**: Specify the UUID version.
    - **count**: Number of UUIDs to generate.
    - **name**: Required for V3/V5 if `namespace` is provided, otherwise generated.
    - **namespace**: Namespace UUID for V3/V5, otherwise generated.
    - **node**: MAC address for V1/V6, otherwise generated.
    """
    try:
        return generate_uuids(version=version.value, count=count, name=name, namespace=namespace, node=node)
    except (ValueError, NotImplementedError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/decode/uuid",
          tags=["UUID/GUID"],
          response_model=UUIDDecodedResponse,
          responses={
              200: {"description": "Successfully decoded UUID."},
              400: {"description": "Invalid UUID string provided."}
          })
async def post_decode_uuid(request: UUIDDecodeRequest, api_key: str = Depends(get_api_key)):
    """Decodes a given UUID string and returns its components and properties."""
    try:
        return decode_uuid_string(request.uuid_string)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Generation Endpoints ---
@app.get("/generate/iban",
         tags=["IBAN"],
         response_model=Union[IBANDetailsResponse, List[IBANDetailsResponse]],
         responses={
             200: {
                 "description": "Successfully generated IBAN(s).",
                 "content": {
                     "application/json": {
                         "examples": {
                             "single_de": {
                                 "summary": "Single German IBAN",
                                 "value": {"iban": "DE89370400440532013000", "country_code": "DE", "bban": "370400440532013000", "check_digits": "89"}
                             },
                             "multiple_gb": {
                                 "summary": "Multiple UK IBANs",
                                 "value": [
                                     {"iban": "GB29NWBK60161331926819", "country_code": "GB", "bban": "NWBK60161331926819", "check_digits": "29"},
                                     {"iban": "GB98MIDL07009312345678", "country_code": "GB", "bban": "MIDL07009312345678", "check_digits": "98"}
                                 ]
                             }
                         }
                     }
                 }},
             400: {"description": "Invalid input, e.g., unsupported country code."}
         })

async def get_iban_details( # Renamed to avoid conflict if you had a get_iban before
    country_code: IBANSupportedCountry = Query(..., description="The 2-letter ISO country code for IBAN generation."),
    count: int = Query(1, ge=1, le=100, description="Number of IBANs to generate (max 100)."),
    api_key: str = Depends(get_api_key)
):
    """
    Generate IBAN(s) for a specified country.
    Supported countries: AT, AU, BE, CH, CZ, DE, DK, ES, FI, FR, GB, HU, IE, IT, NL, NO, PL, PT, RO, SE, TR.
    """
    try:
        return generate_iban(country_code.value, count)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/validate/iban",
          tags=["IBAN"],
          response_model=IBANValidationResponse,
          responses={
              200: {"description": "IBAN validation result."},
              400: {"description": "Invalid input (e.g., missing iban in request body)."},
              422: {"description": "Validation Error (e.g., request body does not match schema)."}
          })

async def post_validate_iban_details( # Renamed to avoid conflict
    request: IBANValidationRequest,
    api_key: str = Depends(get_api_key)
):
    """Validate an International Bank Account Number (IBAN) for supported countries."""
    is_valid, message, formatted_value = validate_iban(request.iban)
    return {"valid": is_valid, "message": message, "formatted_value": formatted_value}

@app.get("/generate/au/abn",
         tags=["Australia"],
         response_model=Dict[str, Union[str, List[str]]],
         responses={
             200: {
                 "description": "Successfully generated ABN(s).",
                 "content": {
                     "application/json": {
                         "examples": {
                             "single": {
                                 "summary": "Single ABN",
                                 "value": {"abn": "12345678901"}
                             },
                             "multiple": {
                                 "summary": "Multiple ABNs",
                                 "value": {"abns": ["12345678901", "98765432109"]}
                             }
                         }
                     }
                 }}})
async def get_abn(count: int = Query(1, description="Number of ABNs to generate.", ge=1, le=100),
                  api_key: str = Depends(get_api_key)):
    """
    Generates one or more test Australian Business Numbers (ABNs).
    - **count**: Number of ABNs to generate (1-100).
    """
    if count == 1:
        return {"abn": generate_abn()}
    abns = [generate_abn() for _ in range(count)]
    return {"abns": abns}

@app.get("/generate/au/acn",
         tags=["Australia"],
         response_model=Dict[str, Union[str, List[str]]],
         responses={
             200: {
                 "description": "Successfully generated ACN(s).",
                 "content": {
                     "application/json": {
                         "examples": {
                             "single": {
                                 "summary": "Single ACN",
                                 "value": {"acn": "123456789"}
                             },
                             "multiple": {
                                 "summary": "Multiple ACNs",
                                 "value": {"acns": ["123456789", "987654321"]}
                             }
                         }
                     }
                 }}})
async def get_acn(count: int = Query(1, description="Number of ACNs to generate.", ge=1, le=100),
                  api_key: str = Depends(get_api_key)):
    """
    Generates one or more test Australian Company Numbers (ACNs).
    - **count**: Number of ACNs to generate (1-100).
    """
    if count == 1:
        return {"acn": generate_acn()}
    acns = [generate_acn() for _ in range(count)]
    return {"acns": acns}

@app.get("/generate/au/tfn",
         tags=["Australia"],
         response_model=Dict[str, Union[str, List[str]]],
         responses={
             200: {
                 "description": "Successfully generated TFN(s).",
                 "content": {
                     "application/json": {
                         "examples": {
                             "single": {
                                 "summary": "Single TFN",
                                 "value": {"tfn": "123456789"}
                             },
                             "multiple": {
                                 "summary": "Multiple TFNs",
                                 "value": {"tfns": ["123456789", "987654321"]}
                             }
                         }
                     }
                 }}})
async def get_tfn(count: int = Query(1, description="Number of TFNs to generate.", ge=1, le=100),
                  api_key: str = Depends(get_api_key)):
    """
    Generates one or more test Australian Tax File Numbers (TFNs).
    - **count**: Number of TFNs to generate (1-100).
    """
    if count == 1:
        return {"tfn": generate_tfn()}
    tfns = [generate_tfn() for _ in range(count)]
    return {"tfns": tfns}

@app.get("/generate/au/all",
         tags=["Australia"],
         response_model=Dict[str, List[str]],
         responses={
             200: {
                 "description": "Successfully generated all specified numbers.",
                 "content": {
                     "application/json": {
                         "example": {
                             "abns": ["12345678901"],
                             "acns": ["123456789"],
                             "tfns": ["123456789"],
                             "medicare_number": ["12345678901"],
                             "driving_licence_number": ["123456789"]
                         }
                     }
                 }}})
async def get_all_au_numbers(count: int = Query(1, description="Number of sets (ABN, ACN, TFN) to generate.", ge=1, le=100),
                             api_key: str = Depends(get_api_key)):
    """
    Generates one or more sets of test Australian Business Numbers (ABNs),
    Australian Company Numbers (ACNs), and Tax File Numbers (TFNs).
    - **count**: Number of sets to generate (1-100). Each set includes one ABN, one ACN, and one TFN.
    """
    response: Dict[str, List[str]] = {
        "abns": [generate_abn() for _ in range(count)],
        "acns": [generate_acn() for _ in range(count)],
        "tfns": [generate_tfn() for _ in range(count)],
        "medicare_number": [generate_medicare_number() for _ in range(count)],
        "driving_licence_number": [generate_driving_licence_number() for _ in range(count)],
    }
    return response

@app.get("/generate/au/medicare",
         tags=["Australia"],
         response_model=Dict[str, Union[str, List[str]]],
         responses={
             200: {
                 "description": "Successfully generated Medicare number(s).",
                 "content": {
                     "application/json": {
                         "examples": {
                             "single": {
                                 "summary": "Single Medicare Number",
                                 "value": {"medicare_number": "12345678901"}
                             },
                             "multiple": {
                                 "summary": "Multiple Medicare Numbers",
                                 "value": {"medicare_numbers": ["12345678901", "98765432109"]}
                             }
                         }
                     }
                 }}})
async def get_medicare_number(count: int = Query(1, description="Number of Medicare numbers to generate.", ge=1, le=100),
                              api_key: str = Depends(get_api_key)):
    """
    Generates one or more test Australian Medicare Numbers.
    - **count**: Number of Medicare numbers to generate (1-100).
    """
    if count == 1:
        return {"medicare_number": generate_medicare_number()}
    numbers = [generate_medicare_number() for _ in range(count)]
    return {"medicare_numbers": numbers}

@app.get("/generate/au/driving_licence",
         tags=["Australia"],
         response_model=Dict[str, Union[str, List[str]]],
         responses={
             200: {
                 "description": "Successfully generated driving licence number(s).",
                 "content": {
                     "application/json": {
                         "examples": {
                             "single": {
                                 "summary": "Single Driving Licence",
                                 "value": {"driving_licence_number": "Y123456"}
                             },
                             "multiple": {
                                 "summary": "Multiple Driving Licences",
                                 "value": {"driving_licence_numbers": ["Y123456", "W9876543"]}
                             }
                         }
                     }
                 }}})
async def get_driving_licence_number(
    count: int = Query(1, description="Number of driving licence numbers to generate.", ge=1, le=100),
    state: Optional[AUState] = Query(None, description="Specify Australian state/territory for specific format (e.g., NSW, VIC). Defaults to a generic format."),
    api_key: str = Depends(get_api_key)
):
    """
    Generates one or more test Australian-style driving licence numbers (generic 9-digit numeric).
    - **count**: Number of driving licence numbers to generate (1-100).
    - **state**: Optional. Specify Australian state/territory for a mock state-specific format.
    """
    state_code = state.value if state else None
    if count == 1:
        return {"driving_licence_number": generate_driving_licence_number(state=state_code)}
    numbers = [generate_driving_licence_number(state=state_code) for _ in range(count)]
    return {"driving_licence_numbers": numbers}

# --- Passport Endpoints ---

@app.get("/generate/passport",
         tags=["Passport"],
         response_model=Union[Dict[str, str], List[Dict[str, str]]],
         responses={
             200: {
                 "description": "Successfully generated passport number(s).",
                 "content": {
                     "application/json": {
                         "examples": {
                             "single_aus": {
                                 "summary": "Single AUS Passport Number",
                                 "value": {"passport_number": "N1234567"}
                             },
                                                          "single_usa": {
                                 "summary": "Single USA Passport Number",
                                 "value": {"passport_number": "123456789"}
                             },
                             "multiple_gbr": {
                                 "summary": "Multiple GBR Passport Numbers",
                                 "value": [{"passport_number": "123456789"}, {"passport_number": "0987654321"}]
                             }
                         }
                     }
                 }},
             400: {"description": "Invalid input, e.g., unsupported country code."}
                 })
async def get_passport_number(
    country_code: SupportedPassportCountry = Query(..., description="The 3-letter country code for which to generate passport numbers."),
    count: int = Query(1, ge=1, le=100, description="Number of passport numbers to generate (max 100)"),
    api_key: str = Depends(get_api_key)
):
    """Generate Passport number(s)."""
    try:
        return generate_passport_number(country_code.value, count)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

class CreditCardDetailsResponse(BaseModel):
    credit_card_number: str = Field(..., example="4242424242424242")
    cvv: str = Field(..., example="123")
    expiry_date: str = Field(..., example="12/28") # MM/YY
    network: str = Field(..., example="VISA")

@app.get("/generate/credit_card",
         tags=["Credit Card"],
         response_model=Union[CreditCardDetailsResponse, List[CreditCardDetailsResponse]],
         responses={
             200: {
                 "description": "Successfully generated credit card number(s).",
                 "content": {
                     "application/json": {
                         "examples": {
                             "single_visa": {
                                 "summary": "Single Visa Card",
                                 "value": {"credit_card_number": "4111111111111111", "cvv": "123", "expiry_date": "12/28", "network": "VISA"}
                             },
                             "multiple_mastercard": {
                                 "summary": "Multiple Mastercard",
                                 "value": [
                                     {"credit_card_number": "5100000000000000", "cvv": "456", "expiry_date": "10/27", "network": "MASTERCARD"},
                                     {"credit_card_number": "2221000000000000", "cvv": "789", "expiry_date": "03/29", "network": "MASTERCARD"}
                                 ]
                             }
                         }
                     }
                 }},
             400: {"description": "Invalid input, e.g., unsupported network."}
         })
async def get_credit_card_number(
    network: CreditCardNetwork = Query(..., description="The credit card network."),
    count: int = Query(1, ge=1, le=100, description="Number of credit card numbers to generate (max 100)."),
    api_key: str = Depends(get_api_key)
):
    """Generate Credit Card number(s) for a specified network."""
    try:
        return generate_credit_card_number(network.value, count)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/generate/au/bank_account",
         tags=["Australia"],
         response_model=Union[Dict[str, str], List[Dict[str, str]]],
         responses={
             200: {
                 "description": "Successfully generated bank account detail(s).",
                 "content": {
                     "application/json": {
                         "examples": {
                             "single": {
                                 "summary": "Single Bank Account",
                                 "value": {"bank_code": "CBA", "bsb": "062000", "account_number": "12345678"}
                             },
                             "multiple": {
                                 "summary": "Multiple Bank Accounts",
                                 "value": [
                                     {"bank_code": "CBA", "bsb": "062000", "account_number": "12345678"},
                                     {"bank_code": "NAB", "bsb": "082000", "account_number": "98765432"}
                                 ]
                             }
                         }
                     }
                 }}})
async def get_bank_account_number(
    count: int = Query(1, description="Number of bank account details to generate.", ge=1, le=100),
    bank: Optional[AUBank] = Query(None, description="Specify Australian bank for specific BSB prefix. Defaults to a generic BSB."),
    api_key: str = Depends(get_api_key)
):
    """
    Generates one or more test Australian Bank Account Numbers (BSB and Account Number).
    - **count**: Number of bank account details to generate (1-100).
    - **bank**: Optional. Specify an Australian bank.

    Disclaimer: These numbers are for testing and development purposes ONLY.
    They are not real bank account numbers and should not be used for actual transactions.
    If you face any issue or have any concern, please send an email to contact@globalsqa.com
    """
    bank_code_str = bank.value if bank else None
    if count == 1:
        return generate_bank_account_number(bank_code=bank_code_str)
    
    accounts = [generate_bank_account_number(bank_code=bank_code_str) for _ in range(count)]
    return accounts


# --- Validation Endpoints ---

@app.post("/validate/passport",
          tags=["Passport"],
          response_model=PassportValidationResponse,
          responses={
              200: {
                  "description": "Passport number validation result.",
                  "content": {
                      "application/json": {
                          "examples": {
                              "valid_aus": {
                                  "summary": "Valid AUS Passport",
                                  "value": {"valid": True, "message": "Passport number format is valid for AUS.", "formatted_value": "N1234567"}
                              },
                              "invalid_usa_format": {
                                  "summary": "Invalid USA Passport Format",
                                  "value": {"valid": False, "message": "Passport number does not match the expected format for USA.", "formatted_value": None}
                              },
                              "unsupported_country": {
                                  "summary": "Unsupported Country for Validation",
                                  "value": {"valid": False, "message": "Validation for country code 'XYZ' is not supported.", "formatted_value": None}
                              }
                          }
                      }
                  }
              },
              400: {"description": "Invalid input (e.g., missing fields in request body)."}
          })
async def post_validate_passport_number(
    request: PassportValidationRequest,
    api_key: str = Depends(get_api_key)
):
    """Validate a Passport number for a specified country (Supported: USA, GBR, IND, DEU, CAN, AUS, CHN)."""
    is_valid, message, formatted_value = validate_passport_number(request.passport_number, request.country_code.value)
    return {"valid": is_valid, "message": message, "formatted_value": formatted_value}


@app.post("/validate/au/abn",
          response_model=ValidationResponse,
          tags=["Australia - Validation"],
          responses={
              200: {
                  "description": "Validation result for ABN.",
                  "content": {
                      "application/json": {
                          "examples": {
                              "valid": {"summary": "Valid ABN", "value": {"input_value": "12345678901", "is_valid": True, "message": "Valid ABN."}},
                              "invalid": {"summary": "Invalid ABN", "value": {"input_value": "111", "is_valid": False, "message": "ABN must be 11 digits."}}
                          }
                      }
                  }}})
async def post_validate_abn(request: ABNValidationRequest, api_key: str = Depends(get_api_key)):
    is_valid, message = validate_abn(request.abn)
    return ValidationResponse(input_value=request.abn, is_valid=is_valid, message=message)


@app.post("/validate/au/acn",
          response_model=ValidationResponse,
          tags=["Australia - Validation"],
          responses={
              200: {
                  "description": "Validation result for ACN.",
                  "content": {
                      "application/json": {
                          "examples": {
                              "valid": {"summary": "Valid ACN", "value": {"input_value": "123456789", "is_valid": True, "message": "Valid ACN."}},
                              "invalid": {"summary": "Invalid ACN", "value": {"input_value": "111", "is_valid": False, "message": "ACN must be 9 digits."}}
                          }
                      }
                  }}})
async def post_validate_acn(request: ACNValidationRequest, api_key: str = Depends(get_api_key)):
    is_valid, message = validate_acn(request.acn)
    return ValidationResponse(input_value=request.acn, is_valid=is_valid, message=message)

@app.post("/validate/au/tfn",
          response_model=ValidationResponse,
          tags=["Australia - Validation"],
          responses={
              200: {
                  "description": "Validation result for TFN.",
                  "content": {
                      "application/json": {
                          "examples": {
                              "valid": {"summary": "Valid TFN", "value": {"input_value": "123456789", "is_valid": True, "message": "Valid TFN."}},
                              "invalid": {"summary": "Invalid TFN", "value": {"input_value": "111", "is_valid": False, "message": "TFN must be 9 digits for this validation."}}
                          }
                      }
                  }}})
async def post_validate_tfn(request: TFNValidationRequest, api_key: str = Depends(get_api_key)):
    is_valid, message = validate_tfn(request.tfn)
    return ValidationResponse(input_value=request.tfn, is_valid=is_valid, message=message)

@app.post("/validate/au/medicare",
          response_model=ValidationResponse,
          tags=["Australia - Validation"],
          responses={
              200: {
                  "description": "Validation result for Medicare number.",
                  "content": {
                      "application/json": {
                          "examples": {
                              "valid": {"summary": "Valid Medicare", "value": {"input_value": "12345678901", "is_valid": True, "message": "Valid Medicare number."}},
                              "invalid": {"summary": "Invalid Medicare", "value": {"input_value": "111", "is_valid": False, "message": "Medicare number must be 11 digits."}}
                          }
                      }
                  }}})
async def post_validate_medicare(request: MedicareValidationRequest, api_key: str = Depends(get_api_key)):
    is_valid, message = validate_medicare_number(request.medicare_number)
    return ValidationResponse(input_value=request.medicare_number, is_valid=is_valid, message=message)

@app.post("/validate/au/driving_licence",
          response_model=ValidationResponse,
          tags=["Australia - Validation"],
          responses={
              200: {
                  "description": "Validation result for Driving Licence.",
                  "content": {
                      "application/json": {
                          "examples": {
                              "valid_nsw": {"summary": "Valid NSW Licence", "value": {"input_value": {"driving_licence_number": "41234567", "state": "NSW"}, "is_valid": True, "message": "Valid test licence format for NSW."}},
                              "invalid_generic": {"summary": "Invalid Generic Licence", "value": {"input_value": {"driving_licence_number": "123"}, "is_valid": False, "message": "Invalid generic test licence format (must be 9 digits)."}}
                          }
                      }
                  }}})
async def post_validate_driving_licence(request: DrivingLicenceValidationRequest, api_key: str = Depends(get_api_key)):
    state_val = request.state.value if request.state else None
    is_valid, message = validate_driving_licence_number(request.driving_licence_number, state=state_val)
    input_data = {"driving_licence_number": request.driving_licence_number}
    if state_val:
        input_data["state"] = state_val
    return ValidationResponse(input_value=input_data, is_valid=is_valid, message=message)

@app.post("/validate/au/bank_account",
          response_model=ValidationResponse,
          tags=["Australia - Validation"],
          responses={
              200: {
                  "description": "Validation result for Bank Account.",
                  "content": {
                      "application/json": {
                          "examples": {
                              "valid_cba": {"summary": "Valid CBA Account", "value": {"input_value": {"bsb": "062000", "account_number": "12345678", "bank_code": "CBA"}, "is_valid": True, "message": "Valid test bank account format."}},
                              "invalid_bsb": {"summary": "Invalid BSB", "value": {"input_value": {"bsb": "123", "account_number": "12345678"}, "is_valid": False, "message": "BSB must be 6 digits."}}
                          }
                      }
                  }}})
async def post_validate_bank_account(request: BankAccountValidationRequest, api_key: str = Depends(get_api_key)):
    bank_code_val = request.bank_code.value if request.bank_code else None
    is_valid, message = validate_bank_account_number(
        request.bsb, 
        request.account_number, 
        bank_code=bank_code_val
    )
    input_data = {"bsb": request.bsb, "account_number": request.account_number}
    if bank_code_val:
        input_data["bank_code"] = bank_code_val
    return ValidationResponse(input_value=input_data, is_valid=is_valid, message=message)
# Run the application with: uvicorn app.main:app --reload