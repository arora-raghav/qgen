import pytest
from fastapi.testclient import TestClient
from app.main import app
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("API_KEY")

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_generate_uuid():
    response = client.get("/generate/uuid", params={"version": 4, "count": 1}, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert "uuid" in response.json() or isinstance(response.json(), list)

def test_decode_uuid():
    uuid_resp = client.get("/generate/uuid", params={"version": 4, "count": 1}, headers={"X-API-Key": API_KEY})
    uuid_val = uuid_resp.json()["uuid"] if "uuid" in uuid_resp.json() else uuid_resp.json()[0]["uuid"]
    response = client.post("/decode/uuid", json={"uuid_string": uuid_val}, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert response.json()["uuid_string"] == uuid_val

def test_generate_iban():
    response = client.get("/generate/iban", params={"country_code": "DE", "count": 1}, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert "iban" in response.json() or isinstance(response.json(), list)

def test_validate_iban():
    iban_resp = client.get("/generate/iban", params={"country_code": "DE", "count": 1}, headers={"X-API-Key": API_KEY})
    iban_val = iban_resp.json()["iban"] if "iban" in iban_resp.json() else iban_resp.json()[0]["iban"]
    response = client.post("/validate/iban", json={"iban": iban_val}, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert "valid" in response.json()

def test_generate_abn():
    response = client.get("/generate/au/abn", params={"count": 1}, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert "abn" in response.json() or "abns" in response.json()

def test_generate_acn():
    response = client.get("/generate/au/acn", params={"count": 1}, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert "acn" in response.json() or "acns" in response.json()

def test_generate_tfn():
    response = client.get("/generate/au/tfn", params={"count": 1}, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert "tfn" in response.json() or "tfns" in response.json()

def test_generate_all_au():
    response = client.get("/generate/au/all", params={"count": 1}, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert "abns" in response.json()

def test_generate_medicare():
    response = client.get("/generate/au/medicare", params={"count": 1}, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert "medicare_number" in response.json() or "medicare_numbers" in response.json()

def test_generate_driving_licence():
    response = client.get("/generate/au/driving_licence", params={"count": 1, "state": "NSW"}, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert "driving_licence_number" in response.json() or "driving_licence_numbers" in response.json()

def test_generate_bank_account():
    response = client.get("/generate/au/bank_account", params={"count": 1, "bank": "CBA"}, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert "bsb" in response.json() or isinstance(response.json(), list)

def test_generate_passport():
    response = client.get("/generate/passport", params={"country_code": "AUS", "count": 1}, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert "passport_number" in response.json() or isinstance(response.json(), list)

def test_generate_credit_card():
    response = client.get("/generate/credit_card", params={"network": "VISA", "count": 1}, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert "credit_card_number" in response.json() or isinstance(response.json(), list)

def test_validate_passport():
    passport_resp = client.get("/generate/passport", params={"country_code": "AUS", "count": 1}, headers={"X-API-Key": API_KEY})
    passport_val = passport_resp.json()["passport_number"] if "passport_number" in passport_resp.json() else passport_resp.json()[0]["passport_number"]
    response = client.post("/validate/passport", json={"country_code": "AUS", "passport_number": passport_val}, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert "valid" in response.json()

def test_validate_abn():
    abn_resp = client.get("/generate/au/abn", params={"count": 1}, headers={"X-API-Key": API_KEY})
    abn_val = abn_resp.json()["abn"] if "abn" in abn_resp.json() else abn_resp.json()["abns"][0]
    response = client.post("/validate/au/abn", json={"abn": abn_val}, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert "is_valid" in response.json()

def test_validate_acn():
    acn_resp = client.get("/generate/au/acn", params={"count": 1}, headers={"X-API-Key": API_KEY})
    acn_val = acn_resp.json()["acn"] if "acn" in acn_resp.json() else acn_resp.json()["acns"][0]
    response = client.post("/validate/au/acn", json={"acn": acn_val}, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert "is_valid" in response.json()

def test_validate_tfn():
    tfn_resp = client.get("/generate/au/tfn", params={"count": 1}, headers={"X-API-Key": API_KEY})
    tfn_val = tfn_resp.json()["tfn"] if "tfn" in tfn_resp.json() else tfn_resp.json()["tfns"][0]
    response = client.post("/validate/au/tfn", json={"tfn": tfn_val}, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert "is_valid" in response.json()

def test_validate_medicare():
    medicare_resp = client.get("/generate/au/medicare", params={"count": 1}, headers={"X-API-Key": API_KEY})
    medicare_val = medicare_resp.json()["medicare_number"] if "medicare_number" in medicare_resp.json() else medicare_resp.json()["medicare_numbers"][0]
    response = client.post("/validate/au/medicare", json={"medicare_number": medicare_val}, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert "is_valid" in response.json()

def test_validate_driving_licence():
    licence_resp = client.get("/generate/au/driving_licence", params={"count": 1, "state": "NSW"}, headers={"X-API-Key": API_KEY})
    licence_val = licence_resp.json()["driving_licence_number"] if "driving_licence_number" in licence_resp.json() else licence_resp.json()["driving_licence_numbers"][0]
    response = client.post("/validate/au/driving_licence", json={"driving_licence_number": licence_val, "state": "NSW"}, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert "is_valid" in response.json()

def test_validate_bank_account():
    bank_resp = client.get("/generate/au/bank_account", params={"count": 1, "bank": "CBA"}, headers={"X-API-Key": API_KEY})
    if isinstance(bank_resp.json(), dict):
        bsb = bank_resp.json()["bsb"]
        account_number = bank_resp.json()["account_number"]
        bank_code = bank_resp.json().get("bank_code", "CBA")
    else:
        bsb = bank_resp.json()[0]["bsb"]
        account_number = bank_resp.json()[0]["account_number"]
        bank_code = bank_resp.json()[0].get("bank_code", "CBA")
    response = client.post("/validate/au/bank_account", json={"bsb": bsb, "account_number": account_number, "bank_code": bank_code}, headers={"X-API-Key": API_KEY})
    assert response.status_code == 200
    assert "is_valid" in response.json()
