import json
import logging
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "127.0.0.1"
PORT = 8000
DB_PATH = "invoices.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


def init_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS invoices (id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_number TEXT UNIQUE, date TEXT, total_amount REAL, customer_name TEXT, payload TEXT, created_at TEXT)"
    )
    conn.commit()
    return conn


class InvoiceRequestHandler(BaseHTTPRequestHandler):
    db_conn: sqlite3.Connection = init_db(DB_PATH)

    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

    def do_POST(self):
        if self.path != "/invoices":
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            invoice = json.loads(body)
        except json.JSONDecodeError:
            self._set_headers(400)
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
            return

        invoice_number = invoice.get("invoice_number")
        if not invoice_number:
            self._set_headers(400)
            self.wfile.write(json.dumps({"error": "Missing invoice_number"}).encode())
            logging.warning("Missing invoice_number in payload: %s", body)
            return

        logging.info("Received invoice POST for invoice_number=%s", invoice_number)
        logging.info("Payload: %s", json.dumps(invoice, ensure_ascii=False))

        cursor = self.db_conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO invoices (invoice_number, date, total_amount, customer_name, payload, created_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
                (
                    invoice_number,
                    invoice.get("date"),
                    invoice.get("total_amount"),
                    invoice.get("customer_name"),
                    json.dumps(invoice, ensure_ascii=False),
                ),
            )
            self.db_conn.commit()
            response = {"status": "received", "duplicate": False}
            self._set_headers(201)
            self.wfile.write(json.dumps(response).encode())
            logging.info("Stored invoice %s in database.", invoice_number)
        except sqlite3.IntegrityError:
            response = {"status": "duplicate", "duplicate": True}
            self._set_headers(200)
            self.wfile.write(json.dumps(response).encode())
            logging.warning("Duplicate invoice ignored: %s", invoice_number)

    def log_message(self, format, *args):
        return


def run_server(host=HOST, port=PORT):
    server = HTTPServer((host, port), InvoiceRequestHandler)
    print(f"Server listening on http://{host}:{port}/invoices")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        InvoiceRequestHandler.db_conn.close()
        server.server_close()


if __name__ == "__main__":
    run_server()
