class BaseReceiptParser:
    def parse(self, pdf_path):
        raise NotImplementedError("Each receipt parser must implement parse()")