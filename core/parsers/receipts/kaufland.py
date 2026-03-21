import re
import pdfplumber
from datetime import datetime
from core.parsers.receipts.base_receipt_parser import BaseReceiptParser
import warnings
warnings.filterwarnings("ignore")

class KauflandReceiptParser(BaseReceiptParser):
    def parse(self, pdf_path):
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text()
        
        lines = text.split("\n")
        items = []

        for i, line in enumerate(lines):
            item_match = re.match(
                r"^(.+?)\s+(\d+,\d{2})\s+([AB])$",
                line.strip()
            )
            qty_match = re.match(
                r"^(.+?)\s+(\d+)\s+\*\s+\d+,\d{2}\s+(\d+,\d{2})\s+([AB])$",
                line.strip()
            )
            # Multi-line quantity: name on previous line, qty on this line
            multiline_qty_match = re.match(
                r"^\s*(\d+)\s+\*\s+\d+,\d{2}\s+(\d+,\d{2})\s+([AB])$",
                line
            )

            if qty_match:
                name = qty_match.group(1).strip()
                quantity = int(qty_match.group(2))
                amount = round(float(qty_match.group(3).replace(",", ".")), 2)
                tax = qty_match.group(4)
                items.append({
                    "name": name,
                    "amount": amount,
                    "quantity": quantity,
                    "tax": tax
                })
            elif multiline_qty_match:
                # Grab name from previous non-empty line
                name = "Unbekannt"
                for j in range(i - 1, -1, -1):
                    prev = lines[j].strip()
                    if prev:
                        name = prev
                        break
                quantity = int(multiline_qty_match.group(1))
                amount = round(float(multiline_qty_match.group(2).replace(",", ".")), 2)
                tax = multiline_qty_match.group(3)
                items.append({
                    "name": name,
                    "amount": amount,
                    "quantity": quantity,
                    "tax": tax
                })
            elif item_match:
                name = item_match.group(1).strip()
                amount = round(float(item_match.group(2).replace(",", ".")), 2)
                tax = item_match.group(3)
                items.append({
                    "name": name,
                    "amount": amount,
                    "quantity": 1,
                    "tax": tax
                })
        # Extract total and date
        total = self.extract_total(lines)
        date = self.extract_date(lines)
        
        return {
            "store": "KAUFLAND",
            "date": date,
            "total": total,
            "receipt_id": f"KAUFLAND_{date}_{total}",
            "items": items
        }

    def extract_total(self, lines):
        for line in lines:
            match = re.match(r"^Summe\s+(\d+,\d{2})$", line.strip())
            if match:
                return round(float(match.group(1).replace(",", ".")), 2)
        return None

    def extract_date(self, lines):
        for line in lines:
            match = re.search(r"Datum[:\s]+(\d{2}\.\d{2}\.\d{2})", line)
            if match:
                date_str = match.group(1)
                # Convert 28.02.26 → 28.02.2026
                day, month, year = date_str.split(".")
                return f"{day}.{month}.20{year}"
        return None