# etl-invoice

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start the local server:

```bash
python3 server.py
```

The server listens on `http://127.0.0.1:8000/invoices`.

## Run read.py

Run the parser with the invoice PDF file:

```bash
python3 read.py invoice.pdf
```

`read.py` reads `invoice.pdf`, extracts required fields, and sends a JSON POST request to the local server.
