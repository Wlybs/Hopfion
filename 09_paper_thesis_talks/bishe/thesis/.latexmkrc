$pdf_mode = 5;  # xelatex
$xelatex = 'xelatex -synctex=1 -interaction=nonstopmode -file-line-error %O %S';
$biber = 'biber %O %S';
$clean_ext = 'synctex.gz run.xml bbl bcf fdb_latexmk fls aux log out toc lof lot';
