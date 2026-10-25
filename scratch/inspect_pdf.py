import pypdfium2 as pdfium
import sys

doc = pdfium.PdfDocument("test_samples/test_out.pdf")
print("Page count:", len(doc))
for i in range(len(doc)):
    page = doc[i]
    text = page.get_textpage().get_text_range()
    print(f"Page {i+1} character count:", len(text))
    print(f"Page {i+1} preview:", repr(text[:120]))
    # Render first page to PNG
    bitmap = page.render(scale=2.0)
    img = bitmap.to_pil()
    img.save(f"test_samples/test_out_page_{i+1}.png")
    print(f"Saved test_samples/test_out_page_{i+1}.png ({img.size})")
