import sys
import os

try:
    import win32com.client
except ImportError:
    print("win32com not installed on Windows Python.")
    sys.exit(1)

doc_path = r"D:\Research\Hopfion\bishe\2026届毕业设计模板及相关规定、要求\毕业设计(论文)材料模板\04-指导记录.doc"
docx_path = r"D:\Research\Hopfion\bishe\2026届毕业设计模板及相关规定、要求\毕业设计(论文)材料模板\04-指导记录.docx"

word = win32com.client.Dispatch("Word.Application")
word.visible = False
try:
    doc = word.Documents.Open(doc_path)
    doc.SaveAs(docx_path, FileFormat=16)
    doc.Close()
    print("Success")
except Exception as e:
    print(f"Error: {e}")
finally:
    word.Quit()