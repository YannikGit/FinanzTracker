import pdfplumber
import re
from core.parsers.base_parser import BaseParser

class ComdirectParser(BaseParser):
    def clean_payee(self, name):
        replacements = {
            "DMDROGERIEMARKTSAGT": "DM",
            "DANKE": "",
            "ALNATURADANKT": "ALNATURA",
            "STWNOKARTENZAHLUNG": "STWNO",
            "PayPalEuropeS.a.r.l.etCie": "PAYPAL",
            "DankeYormas": "YORMAS",
            "RSGGroupGmbH": "McFit",
            "REWEMarktGmbH": "Rewe",
            "TelekomDeutschlandGmbH": "Telekom",
            "Fraunhofer-Gesellschaftzur": "Fraunhofer",
            "UniversitaetRegensburg": "Uni Regensburg",
            "UniversitatRegensburg": "Uni Regensburg",
            "DIELINKELVBayern": "Die Linke",
            "DrillischOnlineGmbH": "Drillisch",
            "SCHUMEUROSHOPGMBH": "Schume Euroshop",
            "DEZREGENSBURG": "DEZ Regensburg",
            "InfinitymarketGmbH": "Infinity Market",
            "WorlHandelsGmbHCo.KG": "Worl Tabak",
            "eprimoGmbH": "Eprimo",
            "24SiebenShop": "24/7 Shop",
            "DBInfraGO": "DB",   
            "Regensburger": "RVV",     
            
        }
        return replacements.get(name,name)
    
    def parse(self, pdf_path):
        raw_text =""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                raw_text += page.extract_text()
        lines = raw_text.split("\n")
        
        transactions = []
        for i, line in enumerate(lines):
            date_match = re.match(r"(\d{2}\.\d{2}\.\d{4})", line)
            amount_match = re.search(r"([+-]\d+[\d.]*,\d{2})$", line)

            if date_match and amount_match:
                date = date_match.group(1)
                amount_str = amount_match.group(1)
                amount = round(float(amount_str.replace(".", "").replace(",", ".")), 2)

                payee_match = re.search(
                    r"(?:Lastschrift/|Übertrag/|Belastung)\s+(\S+)",
                    line
                )
                payee = payee_match.group(1) if payee_match else "Unbekannt"

                # Look at the next 3 lines for a reference number
                reference = "NOREF"
                for j in range(1, 4):
                    if i + j < len(lines):
                        ref_match = re.search(r"[A-Z0-9]{4,}/\d+", lines[i + j])
                        if ref_match:
                            reference = ref_match.group(0)
                            break

                transactions.append({
                    "store": self.clean_payee(payee),
                    "amount": amount,
                    "date": date,
                    "category": None,
                    "reference": reference,

                })

        return transactions