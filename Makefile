CC = ghc

SRCDIR := src/surface_code_routing/gridsynth

SRCFILES := $(wildcard ${SRCDIR}/*.hs)
OBJFILES := $(patsubst ${SRCDIR}/%.hs, ${SRCDIR}/%.o, ${SRCFILES})
HIFILES := $(patsubst ${SRCDIR}/%.hs, ${SRCDIR}/%.hi, ${SRCFILES})
EXES := $(patsubst ${SRCDIR}/%.hs, ${SRCDIR}/%, ${SRCFILES})


all : ${OBJFILES}

build : ${OBJFILES}

${SRCDIR}/%.o : ${SRCDIR}/%.hs
	$(CC) $^

clean : 
	rm $(OBJFILES)
	rm $(EXES)
	rm $(HIFILES)
