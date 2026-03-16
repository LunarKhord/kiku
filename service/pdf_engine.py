"""
"""

import pymupdf
import logging


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)




class PDFEngine:
    pass



async def pdf_meta(pdf_as_bytes):
    """
    This function takes a PDF file as bytes and extracts metadata using PyMuPDF.
    It logs the metadata information for the PDF
    This is passed to an LLM as context.
    """
    logger.info(f"Pdf bytes received {len(pdf_as_bytes)}")
    doc = pymupdf.open(stream=pdf_as_bytes, filetype="pdf")
    logger.info(f"Pymupdf Doc object from bytes: {doc}")
    for page in doc:
       pass



async def classifier(pdf_as_bytes):
    """
    This function classifies a PDF as either text-based or scanned/image-based.
    It uses PyMuPDF to analyze the content of each page and determine the percentage of text coverage.
    If the text covers less than 2% of the page, it is classified as a scanned/image-based PDF (returns 0),
    otherwise it is classified as a text-based PDF (returns 1).
    The function returns a list of classifications for each page in the PDF.
    """
    results = []
    doc = pymupdf.open(stream=pdf_as_bytes, filetype="pdf")
    for page in doc:
        page_area = abs(page.rect)
        text_area = sum(abs(pymupdf.Rect(b[:4])) for b in page.get_text("blocks") if '<image:' not in b[4])
        
        # If text covers less than 2% of the page, treat it as a scan/image
        text_percent = (text_area / page_area) * 100
        is_text_based = text_percent > 2.0
        results.append(1 if is_text_based else 0)
    return results


async def text_extraction(pdf_as_bytes):
    """
    This function extracts text from a PDF using PyMuPDF. It iterates through each page of the PDF, extracts the text, and logs it.
    In a real implementation, you might want to store the extracted text for further processing.
    """
    doc = pymupdf.open(stream=pdf_as_bytes, filetype="pdf")
    for page in doc:
        text = page.get_text()
        logger.info("----------------------------PAGE START---------------------------")
        logger.info(f"Extracted text from page: {text}")
        logger.info("---------------------------PAGE END---------------------------")


async def ocr_extraction(pdf_as_bytes):
    """
    This function is a placeholder for OCR extraction logic. In a real implementation,
    it uses the OCR library Tesseract to extract text from scanned PDFs.
    """
    # Placeholder for OCR extraction logic
    pass