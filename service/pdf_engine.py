""" """

import pymupdf
import logging
from typing import Dict, List, Union
from pymupdf import Document
import pytesseract
from PIL import Image
import io
from utils.string_factory import chunk_by_words, clean_text
from service.edge_tts import generate_speech_from_chunks


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)



async def extract_pdf_metadata(pdf_object: Document, file_name: str) -> Dict | None:
    """
    This function takes a PDF file as bytes and extracts metadata using PyMuPDF.
    It logs the metadata information for the PDF
    This is passed to an LLM as context.
    """
    logger.info(f"Pdf bytes received {len(pdf_object)}")

    print("The metadata for the pdf you provided this time is: ", pdf_object.metadata)
    if len(pdf_object.metadata.get("title")) < 1:
        return { "title": file_name }
    pdf_object.metadata["file_name"] = file_name
    return pdf_object.metadata



async def process_pdf(
    path_to_pdf: List[str], step_fun_instance, file_name: str
) -> None:
    for path in path_to_pdf:
        # Utilize 'with' as a context manager to ensure deterministic cleanup
        with pymupdf.open(path) as pdf_doc:
            book_meta = await extract_pdf_metadata(pdf_doc, file_name)
           

            classification = await classifier(pdf_doc)

            if classification.get("score") == 0:
                logger.info("Executing OCR-based extraction...")
                try:
                    content = await hybrid_text_extraction(pdf_doc)
                    # Generate chapter manifest
                    script = await step_fun_instance.generate_chapters_from_corpus(content, book_meta)
                   
            
                    await process_script(script)

                except Exception as e:
                    logger.error(
                        f"An error occured while processing document using OCR engine: {e}"
                    )
            else:
                try:
                    logger.info("Executing native text extraction...")
                    content = await text_extraction(pdf_doc)
                  
                    # Generate chapter manifest
                    script = await step_fun_instance.generate_chapters_from_corpus(content, book_meta)
                   
                    await process_script(script)
                except Exception as e:
                    logger.error(
                        f"An error occured while processing PDF as text only: {e}"
                    )


async def process_script(chapter_to_content: List[Dict]):
    chunks_to_chapter = []
    for content in chapter_to_content:
        title = content.get("title").strip("\n")
        
        script = await clean_text(content.get("text"))
        chunk = await chunk_by_words(script)

        chunks_to_chapter.append(
            {
                "chapter": title,
                "chunk": chunk,
            }
            )
    print("extracted chunk to chapter:", chunks_to_chapter[-1])
    await generate_speech_from_chunks(chunks_to_chapter)
    logger.info("Generating the audio for the passed in chapter.")
   



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
            largest_img_area = max(
                abs(pymupdf.Rect(img["bbox"]) & page.rect) for img in image_info
            )
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
                    if is_invisible_ocr:
                        break
            if is_invisible_ocr:
                break

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
        logger.info(
            f"Document classified as SCANNED ({scanned_ratio:.2%} non-textual pages)."
        )
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
        full_corpus.append(digital_text)

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
            full_corpus.append(ocr_text)
        else:
            full_corpus.append(digital_text)

    # print("FULL EXTRACTED STUFF")
    # print(full_corpus)
    return "\n\n".join(full_corpus)
