from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from ebooklib import epub
from fpdf import FPDF
import html2text
import unicodedata
from urllib.parse import unquote
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from databases import Database
import os
from datetime import datetime

# Database setup
DATABASE_URL = "sqlite:///./sql_app.db"
database = Database(DATABASE_URL)
Base = declarative_base()
engine = create_engine(DATABASE_URL)

class Conversion(Base):
    __tablename__ = "conversions"

    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String, index=True)
    pdf_filename = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đảm bảo thư mục uploads tồn tại
os.makedirs("uploads", exist_ok=True)

# Thêm dòng này để phục vụ các file tĩnh từ thư mục 'uploads'
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

def convert_epub_to_pdf(epub_file_path):
    book = epub.read_epub(epub_file_path)
    pdf = FPDF()
    h = html2text.HTML2Text()
    h.ignore_links = True

    for item in book.get_items():
        if isinstance(item, epub.EpubHtml):
            content = item.get_body_content().decode('utf-8')
            text = h.handle(content)
            # Normalize Unicode characters
            text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, text)
    
    epub_filename = os.path.basename(epub_file_path)
    pdf_filename = os.path.splitext(epub_filename)[0] + '.pdf'
    pdf_file_path = os.path.join("uploads", pdf_filename)
    
    pdf.output(pdf_file_path)
    
    return pdf_file_path

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.post("/convert")
async def convert_file(epub_file: UploadFile = File(...)):
    epub_path = os.path.join("uploads", epub_file.filename)
    
    with open(epub_path, "wb") as f:
        f.write(await epub_file.read())
    
    pdf_file_path = convert_epub_to_pdf(epub_path)
    pdf_filename = os.path.basename(pdf_file_path)
    
    # Lưu thông tin chuyển đổi vào database
    query = Conversion.__table__.insert().values(
        original_filename=epub_file.filename,
        pdf_filename=pdf_filename
    )
    await database.execute(query)
    
    return {"pdf_file": pdf_filename}

@app.get("/download/{filename:path}")
async def download_file(filename: str):
    file_path = os.path.join("uploads", unquote(filename))
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=os.path.basename(file_path))
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/conversions")
async def list_conversions():
    query = Conversion.__table__.select()
    return await database.fetch_all(query)
