import re
import pdfplumber
import warnings
warnings.filterwarnings("ignore")
from core.parsers.base_parser import BaseParser

class INGParser(BaseParser):

    TRANSACTION_TYPES = [
        "Echtzeitüberweisung",
        "Dauerauftrag/Terminueberw.",
        "Lastschrift",
        "Gutschrift/Dauerauftrag",
        "Gutschrift",
        "Entgelt",
        "Überweisung",
        "Gehalt/Rente",
        "Zinsen/Dividende",
    ]

    def clean_payee(self, name, reference=""):
        # Known replacements
        replacements = {
            "AMAZON PAYMENTS EUROPE S.C.A.": "Amazon",
            "VISA PAYPAL": "PayPal",
            "VISA KAUFLAND": "Kaufland",
            "VISA REWE": "Rewe",
            "VISA DM": "DM",
            "VISA ALDI": "Aldi",
            "VISA LIDL": "Lidl",
            "NETFLIX.COM": "Netflix",
            "Spotify": "Spotify",
        }
        for key, val in replacements.items():
            if key in name:
                return val

        # Clean up Girocard/bank fee entries
        if "GIROCARD" in reference.upper() or "ENTGELT" in reference.upper():
            return "ING Bankgebühr"

        return name.strip()

    def get_transaction_type(self, line):
        for t in self.TRANSACTION_TYPES:
            if t in line:
                return t
        return None

    def parse(self, pdf_path):
        raw_text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    raw_text += text + "\n"

        lines = raw_text.split("\n")
        transactions = []

        date_pattern = r"\d{2}\.\d{2}\.\d{4}"
        amount_pattern = r"([+-]?\d{1,3}(?:\.\d{3})*,\d{2})$"
        type_pattern = "(?:" + "|".join(
            re.escape(t) for t in self.TRANSACTION_TYPES
        ) + ")"

        transaction_line = re.compile(
            rf"^({date_pattern})\s+{type_pattern}\s+(.+?)\s+{amount_pattern}$"
        )

        reference_line = re.compile(rf"^({date_pattern})\s+(.+)$")

        for i, line in enumerate(lines):
            line = line.strip()
            match = transaction_line.match(line)
            if match:
                date = match.group(1)
                raw_payee = match.group(2).strip()
                amount_str = match.group(3)
                amount = round(float(
                    amount_str.replace(".", "").replace(",", ".")
                ), 2)

                # Try to get reference from next line
                reference = "NOREF"
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    ref_match = reference_line.match(next_line)
                    if ref_match:
                        ref_text = ref_match.group(2).strip()
                        # Extract Referenz: tag if present
                        ref_search = re.search(r"Referenz[:\s]*(\S+)", ref_text)
                        if ref_search:
                            reference = ref_search.group(1)
                        elif ref_text and not ref_text.startswith("ING"):
                            # Use first 30 chars of Verwendungszweck as reference
                            reference = ref_text[:30]

                payee = self.clean_payee(raw_payee, reference)

                transactions.append({
                    "store": payee,
                    "amount": amount,
                    "date": date,
                    "category": None,
                    "top_category": None,
                    "sub_category": None,
                    "reference": reference
                })

        return transactions