import os
from spire.doc import *
from spire.doc.common import *

doc = Document()
doc.LoadFromFile("/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/2026届毕业设计模板及相关规定、要求/毕业设计(论文)材料模板/04-指导记录.doc")
doc.SaveToFile("/mnt/d/Research/Hopfion/09_paper_thesis_talks/bishe/2026届毕业设计模板及相关规定、要求/毕业设计(论文)材料模板/04-指导记录_converted.docx", FileFormat.Docx2016)
doc.Close()
print("Conversion successful.")
