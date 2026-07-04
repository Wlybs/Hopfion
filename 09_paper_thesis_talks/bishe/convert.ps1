$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $word.Documents.Open("D:\Research\Hopfion\bishe\2026届毕业设计模板及相关规定、要求\毕业设计(论文)材料模板\04-指导记录.doc")
$doc.SaveAs([ref]"D:\Research\Hopfion\bishe\2026届毕业设计模板及相关规定、要求\毕业设计(论文)材料模板\04-指导记录.docx", [ref]16)
$doc.Close()
$word.Quit()
Write-Host "Success"