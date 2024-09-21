import os
from ebooklib import epub
from fpdf import FPDF

def convert_epub_to_pdf(epub_file_path):
    # Mở file EPUB
    book = epub.read_epub(epub_file_path)
    
    # Tạo file PDF
    pdf = FPDF()
    pdf.add_page()

    # Lấy nội dung EPUB và thêm vào PDF
    for item in book.get_items():
        if item.get_type() == epub.EpubHtml:
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, item.get_body_content().decode('utf-8'))

    # Tạo tên file PDF trong thư mục Downloads
    epub_filename = os.path.basename(epub_file_path)
    pdf_filename = os.path.splitext(epub_filename)[0] + '.pdf'
    pdf_file_path = os.path.join(r"C:\Users\judyh\Downloads", pdf_filename)

    # Lưu file PDF
    pdf.output(pdf_file_path)

    return pdf_file_path
