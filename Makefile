VERSION=0.3-alpha1
BENCHMARK=test/pypng.png test/pypng9.png test/pypngi.png
REFERENCE=test/netpbm.png test/netpbm9.png test/netpbmi.png

# Run benchmark on png.py and print a one-line report
benchmark :
	@make $(BENCHMARK) 2>&1 | grep system \
	| sed -e s/user./\\+/ | sed -e s/system.*// \
	| xargs echo `date +%Y-%m-%d` $(VERSION)

# Run benchmark on pnmtopng from netpbm
reference :
	@make $(REFERENCE) 2>&1 | grep system \
	| sed -e s/user./\\+/ | sed -e s/system.*// \
	| xargs echo `date +%Y-%m-%d` pnmtopng

test/pypng.png : test/large.ppm
	LC_ALL=POSIX time python lib/png.py < $< > $@
	@ls --block-size=1 -s $@ | sed -e s/test.*/system/

test/pypng9.png : test/large.ppm
	LC_ALL=POSIX time python lib/png.py --compression 9 < $< > $@
	@ls --block-size=1 -s $@ | sed -e s/test.*/system/

test/pypngi.png : test/large.ppm
	LC_ALL=POSIX time python lib/png.py --interlace < $< > $@
	@ls --block-size=1 -s $@ | sed -e s/test.*/system/

test/netpbm.png : test/large.ppm
	LC_ALL=POSIX time pnmtopng < $< > $@
	@ls --block-size=1 -s $@ | sed -e s/test.*/system/

test/netpbm9.png : test/large.ppm
	LC_ALL=POSIX time pnmtopng -compression 9 < $< > $@
	@ls --block-size=1 -s $@ | sed -e s/test.*/system/

test/netpbmi.png : test/large.ppm
	LC_ALL=POSIX time pnmtopng -interlace < $< > $@
	@ls --block-size=1 -s $@ | sed -e s/test.*/system/

test/%.ppm : test/%.png
	pngtopnm < $< > $@

install :
	python setup.py install

README :
	pydoc png > $@

.PHONY : README test/large.ppm
