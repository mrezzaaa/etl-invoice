import argparse
import re
import logging
import warnings
from typing import List, Optional, Dict, Any

import requests
from PyPDF2 import PdfReader
from pydantic import BaseModel, ValidationError
from requests.adapters import HTTPAdapter
from urllib3.exceptions import NotOpenSSLWarning
from urllib3.util.retry import Retry

warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


# Validation Model
class Invoice(BaseModel):
    invoice_number: str
    date: str
    total_amount: float
    customer_name: str


def extract_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text = ""

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    return text


def normalize_text(text: str) -> str:
    text = text.replace("\r", "\n").replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def clean_value(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def split_lines(text: str) -> List[str]:
    return [clean_value(line) for line in text.splitlines() if clean_value(line)]


def search_patterns(text: str, patterns: List[str], field_name: str, required: bool = True) -> Optional[str]:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and match.group(1):
            return clean_value(match.group(1))

    if required:
        raise AttributeError(f"{field_name} not found in PDF.")
    return None


def find_invoice_number(text: str) -> str:
    patterns = [
        r"Invoice\s*Number\s*[:\-]?\s*(.+?)($|\n|\r)",
        r"Invoice\s*#?\s*[:\-]?\s*(.+?)($|\n|\r)",
        r"Invoice\s*No\s*[:\-]?\s*(.+?)($|\n|\r)",
        r"Receipt\s*#?\s*[:\-]?\s*(.+?)($|\n|\r)",
    ]
    return search_patterns(text, patterns, "invoice_number")


def find_date(text: str) -> str:
    patterns = [
        r"Invoice\s*Date\s*[:\-]?\s*(.+?)($|\n|\r)",
        r"Date\s*[:\-]?\s*(.+?)($|\n|\r)",
        r"Tanggal\s*[:\-]?\s*(.+?)($|\n|\r)",
    ]
    return search_patterns(text, patterns, "date")


def parse_amount(amount_text: str) -> float:
    raw = amount_text.strip()
    raw = raw.replace("Rp", "").replace("IDR", "").replace(" ", "")

    if raw.count(",") == 1 and raw.count(".") > 1:
        raw = raw.replace(".", "").replace(",", ".")
    elif raw.count(".") > 1 and raw.count(",") == 0:
        raw = raw.replace(".", "")
    else:
        raw = raw.replace(",", "")

    return float(raw)


def find_total_amount(text: str) -> float:
    patterns = [
        r"Total\s*Due\s*[:\-]?\s*\$?([\d.,]+)",
        r"Amount\s*Due\s*[:\-]?\s*\$?([\d.,]+)",
        r"Total\s*[:\-]?\s*\$?([\d.,]+)",
        r"Amount\s*[:\-]?\s*\$?([\d.,]+)",
    ]

    matches = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if match and match.group(1):
                matches.append(match.group(1))

    if matches:
        return parse_amount(matches[-1])

    raise AttributeError("total_amount not found in PDF.")


def find_customer_name(lines: list[str]) -> str:
    for idx, line in enumerate(lines):
        if re.match(r"^(?:To|Bill To|Ship To)\b\s*[:\-]?\s*$", line, re.IGNORECASE):
            if idx + 1 < len(lines):
                return lines[idx + 1]
        match = re.match(r"^(?:To|Bill To|Ship To)\b\s*[:\-]?\s*(.+)$", line, re.IGNORECASE)
        if match:
            return clean_value(match.group(1))

    raise AttributeError("customer_name not found in PDF.")


def parse_invoice(text: str) -> Dict[str, Any]:
    text = normalize_text(text)
    lines = split_lines(text)

    invoice_number = find_invoice_number(text)
    date = find_date(text)
    total_amount = find_total_amount(text)
    customer_name = find_customer_name(lines)

    return {
        "invoice_number": invoice_number,
        "date": date,
        "total_amount": total_amount,
        "customer_name": customer_name,
    }


# API client with retry
session = requests.Session()
retry = Retry(total=3, backoff_factor=1)
session.mount("https://", HTTPAdapter(max_retries=retry))
session.mount("http://", HTTPAdapter(max_retries=retry))


def send_to_api(invoice: Invoice) -> None:
    response = session.post(
        "http://127.0.0.1:8000/invoices",
        json=invoice.model_dump(),
        timeout=10,
    )
    response.raise_for_status()


def process_invoice(pdf_path: str):
    try:
        text = extract_text(pdf_path)
        data = parse_invoice(text)
        invoice = Invoice(**data)

        send_to_api(invoice)
        logging.info("Invoice successfully sent to local server.")

    except ValidationError as e:
        logging.error("Validation Error: %s", e)
    except requests.RequestException as e:
        logging.error("API Error: %s", e)
    except AttributeError as e:
        logging.error("Required field not found in PDF: %s", e)
    except Exception as e:
        logging.error("Unexpected Error: %s", e)




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process an invoice PDF into an API payload.")
    parser.add_argument("pdf_path", nargs="?", default="invoice.pdf", help="Path to the invoice PDF")
    args = parser.parse_args()

    process_invoice(args.pdf_path)