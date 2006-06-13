BENCHMARK = test/pypng.png test/pypng9.png test/pypngi.png
REFERENCE = test/netpbm.png test/netpbm9.png test/netpbmi.png

benchmark :
	@make $(BENCHMARK) 2>&1 | grep user \
	| sed -e s/user./\\+/ | sed -e s/system.*// | xargs echo pypng

reference :
	@make $(REFERENCE) 2>&1 | grep user \
	| sed -e s/user./\\+/ | sed -e s/system.*// | xargs echo netpbm

test/pypng.png : test/large.ppm
	LC_ALL=POSIX time python lib/png.py < $< > $@

test/pypng9.png : test/large.ppm
	LC_ALL=POSIX time python lib/png.py --compression 9 < $< > $@

test/pypngi.png : test/large.ppm
	LC_ALL=POSIX time python lib/png.py --interlace < $< > $@

test/netpbm.png : test/large.ppm
	LC_ALL=POSIX time pnmtopng < $< > $@

test/netpbm9.png : test/large.ppm
	LC_ALL=POSIX time pnmtopng -compression 9 < $< > $@

test/netpbmi.png : test/large.ppm
	LC_ALL=POSIX time pnmtopng -interlace < $< > $@

test/%.ppm : test/%.png
	pngtopnm < $< > $@

install :
	python setup.py install

README :
	pydoc png > $@

.PHONY : README test/large.ppm
