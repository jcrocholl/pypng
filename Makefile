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
	LC_ALL=POSIX time python lib/png.py $< > $@
	@du -b $@ | sed -e s/test.*/system/

test/pypng9.png : test/large.ppm
	LC_ALL=POSIX time python lib/png.py --compression 9 $< > $@
	@du -b $@ | sed -e s/test.*/system/

test/pypngi.png : test/large.ppm
	LC_ALL=POSIX time python lib/png.py --interlace $< > $@
	@du -b $@ | sed -e s/test.*/system/

test/pypnga.png : test/large.pgm test/large.ppm
	LC_ALL=POSIX time python lib/png.py -a $^ > $@
	@du -b $@ | sed -e s/test.*/system/

test/pypngai.png : test/large.pgm test/large.ppm
	LC_ALL=POSIX time python lib/png.py -i -a $^ > $@
	@du -b $@ | sed -e s/test.*/system/

test/netpbm.png : test/large.ppm
	LC_ALL=POSIX time pnmtopng $< > $@
	@du -b $@ | sed -e s/test.*/system/

test/netpbm9.png : test/large.ppm
	LC_ALL=POSIX time pnmtopng -compression 9 $< > $@
	@du -b $@ | sed -e s/test.*/system/

test/netpbmi.png : test/large.ppm
	LC_ALL=POSIX time pnmtopng -interlace $< > $@
	@du -b $@ | sed -e s/test.*/system/

test/%.ppm : test/%.png
	pngtopnm $< > $@

test/%.pgm : test/%.ppm
	ppmtopgm $< > $@

install :
	python setup.py install

pylint :
	pylint -iy --reports=no --good-names=x,y,r,g,b,a,i lib/png.py

testsuite :
	test/benchmark.py < test/testsuite.sh
	test/benchmark.py < test/compression_levels.sh

README :
	pydoc lib/png.py > $@

clean :
	rm -rf build dist test/test-*.png test/pypng*.png test/netpbm*.png

.PHONY : README clean
