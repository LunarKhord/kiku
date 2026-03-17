"""
"""

import pymupdf
import logging
from typing import Dict, List


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)




class PDFEngine:
    pass



async def extract_table_of_content(pdf_as_bytes: bytes) -> List | None:
    doc = pymupdf.open(stream=pdf_as_bytes, filetype="pdf")

    # Get the table of contents a list of lists
    toc = doc.get_toc()
    logger.info(f"Table of content: {toc}")
    doc.close()
    if len(toc) > 0 or toc is not None:
        return toc
    else:
        return None



async def pdf_meta(pdf_as_bytes: bytes) -> Dict | None:
    """
    This function takes a PDF file as bytes and extracts metadata using PyMuPDF.
    It logs the metadata information for the PDF
    This is passed to an LLM as context.
    """
    logger.info(f"Pdf bytes received {len(pdf_as_bytes)}")
    doc = pymupdf.open(stream=pdf_as_bytes, filetype="pdf")
    if doc.metadata.get("title") is None or len( doc.metadata.get("title")) == 0:
        return None
    return doc.metadata
    

async def classifier(pdf_as_bytes: bytes) -> List[Dict]:
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


        # Check for massive  images
        image_info = page.get_image_info()
        largest_img_ratio = 0

        if image_info:
            largest_img_area = max(abs(pymupdf.Rect(img["bbox"]) & page.rect) for img in image_info)
            largest_img_ratio = largest_img_area / page_area
        
        # 2. Check for Invisible OCR Text (The "Smoking Gun")
        # Render mode 3 = invisible. In PyMuPDF dicts, this is in the 'flags' or 'wmode'.
        # A more direct way is checking the 'flags' in the span.
        is_invisible_ocr = False
        page_dict = page.get_text("dict")
        for block in page_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        if span.get("flags") == 6 or span.get("render") == 3:
                            is_invisible_ocr = True
                            break
        
        if largest_img_ratio > 0.8:
            results.append({
                "page": page.number + 1,
                "type": "scanned/image-based",
                "score": 0,
                
            })  # Scanned/Image-based PDF


        elif is_invisible_ocr:
            results.append({
                "page": page.number + 1,
                "type": "scanned/image-based with invisible OCR",
                "score": 0,
                
            })  # Scanned/Image-based PDF with invisible OCR text


        elif len(page.get_text("words")) > 5:
            results.append(
                {
                    "page": page.number + 1,
                    "type": "text-based",
                    "score": 1,
                    
                    })  # Text-based PDF
        else:
            results.append({
                "page": page.number + 1,
                "type": "scanned/image-based",
                "score": 0,
                
            })  # Default to scanned/image-based PDF if no text is found
    doc.close()

    # Log the classification results, by checking if 10% of the document is flagged as 0,
    # it's usually safe to treat the entire document as a scan.

    total_pages = len(results)
    scanned_count = sum(1 for page in results if page["score"] == 0)

    if (scanned_count / total_pages) > 0.10:
        logger.info("More than 10% of pages are scanned/image-based. Classifying entire document as scanned/image-based.")
        return {"type": "scanned/image-based", "score": 0}
    else:
        return {"type": "text-based", "score": 1}


async def text_extraction(pdf_as_bytes: bytes):
    """
    This function extracts text from a PDF using PyMuPDF. It iterates through each page of the PDF, extracts the text, and logs it.
    In a real implementation, you might want to store the extracted text for further processing.
    """
    doc = pymupdf.open(stream=pdf_as_bytes, filetype="pdf")
    for page in doc:
        text = page.get_text()
        logger.info(f"Type is {type(text)}")
        logger.info("----------------------------PAGE START---------------------------")
        logger.info(f"Extracted text from page: {text}")
        logger.info("---------------------------PAGE END---------------------------")


async def ocr_extraction(pdf_as_bytes: bytes):
    """
    This function is a placeholder for OCR extraction logic. In a real implementation,
    it uses the OCR library Tesseract to extract text from scanned PDFs.
    """
    # Placeholder for OCR extraction logic
    pass


async def ocr_text_extraction(pdf_as_bytes: bytes):
    """
    This function is a placeholder for OCR text extraction logic. In a real implementation,
    it would combine OCR extraction with text extraction to handle PDFs that contain both scanned images and embedded text.
    """
    # Placeholder for combined OCR and text extraction logic
    pass
