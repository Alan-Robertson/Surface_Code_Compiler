# Requires pygmentize for syntax highlighting to be installed
PDFLATEX = TEXINPUTS=.:../../tex: pdflatex --shell-escape -interaction nonstopmode
SOURCES = $(shell find . -name "*.tex")
PDFS = $(SOURCES:.tex=.pdf)

.PHONY: all clean

all: $(PDFS)

clean:
	rm -f $(PDFS)
	rm -f *.aux *.log *.out *.pyg *.fls *.fdb* *.synctex*
	rm -rf _minted-*

%.pdf: %.tex
	$(PDFLATEX) $<
	$(PDFLATEX) $<

