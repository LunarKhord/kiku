from fastapi import FastAPI, File, UploadFile, status, Depends
import shutil
from lifespan import lifespan, get_step_fun, get_kokoro
from pathlib import Path
import aiofiles
from typing import Annotated, List
from service.pdf_engine import process_pdf

app = FastAPI(lifespan=lifespan)


# Make sure the uploads dir already exists before coninue, else it creates it.
# Ensure the upload directory exists
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@app.get("/health")
async def health():
    return {"message": "All Systems are green."}


@app.post("/api/v1/kiku/uploads")
async def upload_file(files: List[UploadFile] = File(...), step_fun_instance = Depends(get_step_fun), kokoro_instance = Depends(get_kokoro)):
    saved_file_paths = []
    # Sanatize the filename to prevent path traversal attacks
    for file in files:
        print(f"File object {file.headers.get("content-type")}")
        if file.headers.get("content-type") != "application/pdf":
            return {"message": "Document must be a type PDF."}
        safe_filename = Path(file.filename).name
        file_path = UPLOAD_DIR / safe_filename

        async with aiofiles.open(file_path, 'wb') as out_file:
            # Read the upload file in chunks and write to the destination
            while chunk := await file.read(1024):
                await out_file.write(chunk)
        saved_file_paths.append(str(file_path))
    await file.close()
    await process_pdf(saved_file_paths, step_fun_instance, kokoro_instance)