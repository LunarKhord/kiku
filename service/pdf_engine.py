"""
"""

import pymupdf
import logging
from typing import Dict, List, Union
from pymupdf import Document
import pytesseract
from PIL import Image
import io


# from service.stepfun import StepFun



logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

# StepFun model instance
# step_fun = StepFun()
# logger.info("Instance was created for", step_fun)





class PDFEngine:
    pass

# The need to support the following has arises by ME
"""
 -- PDF
 -- EPUB
 -- EPUB3
 -- TXT

"""


async def process_pdf(path_to_pdf: List[str], step_fun_instance, kokoro_instance) -> None:
    for path in path_to_pdf:
        # Utilize 'with' as a context manager to ensure deterministic cleanup
        with pymupdf.open(path) as pdf_doc:
            await pdf_meta(pdf_doc)
            
            classification = await classifier(pdf_doc)
            
            if classification.get("score") == 0:
                logger.info("Executing OCR-based extraction...")
                content = await hybrid_text_extraction(pdf_doc)
                #print("I am the returned content", content)
                #cleaned_content = await step_fun.clean_corpus(book_corpus=content)
                #print("I GOT THE CLEANED TEXT BABAY:", cleaned_content)
                cleaned_content = await step_fun_instance.clean_corpus(content)
                #print("end of returned content not clean though")
            else:
                logger.info("Executing native text extraction...")
                content = await text_extraction(pdf_doc)
                await step_fun_instance.clean_corpus(content)



async def pdf_meta(pdf_object: Document) -> Dict | None:
    """
    This function takes a PDF file as bytes and extracts metadata using PyMuPDF.
    It logs the metadata information for the PDF
    This is passed to an LLM as context.
    """
    logger.info(f"Pdf bytes received {len(pdf_object)}")
    
    print("The metadata for the pdf you provided this time is: ",pdf_object.metadata)
    




async def classifier(pdf_object: pymupdf.Document) -> Dict[str, Union[str, int]]:
    """
    Performs a heuristic analysis of the PDF to discern its primary composition:
    digital text versus rasterized imagery (scans).
    
    Returns a dictionary summarizing the dominant document characteristic.
    """
    results = []
    
    # Ensure the document possesses pages to avoid ZeroDivisionError
    total_pages = len(pdf_object)
    if total_pages == 0:
        logger.warning("Attempted to classify an empty document.")
        return {"type": "empty", "score": -1}

    for page in pdf_object:
        page_area = abs(page.rect)
        
        # 1. Evaluate Image Dominance
        image_info = page.get_image_info()
        largest_img_ratio = 0
        if image_info:
            # Calculate the area of the largest image relative to the page area
            largest_img_area = max(abs(pymupdf.Rect(img["bbox"]) & page.rect) for img in image_info)
            largest_img_ratio = largest_img_area / page_area
        
        # 2. Detect Surreptitious OCR Layers (Invisible Text)
        # Render mode 3 denotes "Invisible" text, a hallmark of OCR overlays.
        is_invisible_ocr = False
        page_dict = page.get_text("dict")
        for block in page_dict.get("blocks", []):
            if "lines" in block:
                for line in block["lines"]:
                    for span in line.get("spans", []):
                        # PDF Render Mode 3 = Neither fill nor stroke (invisible)
                        if span.get("render") == 3 or span.get("flags", 0) & 1 << 0:
                            is_invisible_ocr = True
                            break
                    if is_invisible_ocr: break
            if is_invisible_ocr: break
        
        # 3. Decision Matrix for the Current Page
        if largest_img_ratio > 0.8:
            results.append({"score": 0, "type": "image-dominant"})
        elif is_invisible_ocr:
            results.append({"score": 0, "type": "invisible-ocr"})
        elif len(page.get_text("words")) > 5:
            results.append({"score": 1, "type": "text-based"})
        else:
            # Default to scanned if the page is devoid of significant text
            results.append({"score": 0, "type": "scanned"})

    # Aggregate results: If > 10% of pages are flagged, treat the whole as a scan.
    scanned_count = sum(1 for res in results if res["score"] == 0)
    scanned_ratio = scanned_count / total_pages

    if scanned_ratio > 0.10:
        logger.info(f"Document classified as SCANNED ({scanned_ratio:.2%} non-textual pages).")
        return {"type": "scanned/image-based", "score": 0}
    
    logger.info("Document classified as TEXT-BASED.")
    return {"type": "text-based", "score": 1}




async def text_extraction(pdf_object: Document) -> str | None:
    """
    This function extracts text from a PDF using PyMuPDF. It iterates through each page of the PDF, extracts the text, and logs it.
    In a real implementation, you might want to store the extracted text for further processing.
    """
    full_corpus = []

    for page_index, page in enumerate(pdf_object):
        digital_text = page.get_text("text").strip()
        full_corpus.append(f"--- Page {page_index + 1} (TEXT) ---\n{digital_text}")
   
    return "\n\n".join(full_corpus)
    

async def hybrid_text_extraction(pdf_object: pymupdf.Document) -> str | None:
    full_corpus = []
    # Use enumerate to provide the index for labeling
    for page_index, page in enumerate(pdf_object):
        digital_text = page.get_text("text").strip()
        
        if len(digital_text) < 50:
            zoom = 2.0 
            mat = pymupdf.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            
            ocr_text = pytesseract.image_to_string(img)
            full_corpus.append(f"--- Page {page_index + 1} (OCR) ---\n{ocr_text}")
        else:
            full_corpus.append(f"--- Page {page_index + 1} (Digital) ---\n{digital_text}")

    #print("FULL EXTRACTED STUFF")
    #print(full_corpus)
    return "\n\n".join(full_corpus)