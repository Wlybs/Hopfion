Set objWord = CreateObject("Word.Application")
objWord.Visible = False
objWord.DisplayAlerts = 0
Set objDoc = objWord.Documents.Open("D:\Research\Hopfion\bishe\2026届毕业设计模板及相关规定、要求\毕业设计(论文)材料模板\04-指导记录.doc", False, True)
objDoc.SaveAs "D:\Research\Hopfion\bishe\2026届毕业设计模板及相关规定、要求\毕业设计(论文)材料模板\04-指导记录_vbs.docx", 16
objDoc.Close False
objWord.Quit
WScript.Echo "Done"
