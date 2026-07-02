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

### read.py output
```
INFO: Invoice successfully sent to local server.
```

### server output
```
2026-07-03 00:20:05,493 INFO: Received invoice POST for invoice_number=INV-3337
2026-07-03 00:20:05,493 INFO: Payload: {"invoice_number": "INV-3337", "date": "January 25, 2016", "total_amount": 93.5, "customer_name": "Test Business"}
```

`read.py` reads `invoice.pdf`, extracts required fields, and sends a JSON POST request to the local server.
