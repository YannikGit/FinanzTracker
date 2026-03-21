class BaseParser:
    def parse(self, pdf_path):
        raise NotImplementedError("Each bank parser must implement parse()")