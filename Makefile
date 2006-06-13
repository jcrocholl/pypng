.PHONY : test/large.ppm

benchmarks : \
test/benchmark.png \
test/benchmark-interlace.png \
test/benchmark-netpbm.png \
test/benchmark-netpbm-interlace.png \

test/benchmark.png : test/large.ppm
	LC_ALL=POSIX time python lib/png.py < $< > $@

test/benchmark-interlace.png : test/large.ppm
	LC_ALL=POSIX time python lib/png.py --interlace < $< > $@

test/benchmark-netpbm.png : test/large.ppm
	LC_ALL=POSIX time pnmtopng < $< > $@

test/benchmark-netpbm-interlace.png : test/large.ppm
	LC_ALL=POSIX time pnmtopng -interlace < $< > $@

test/%.ppm : test/%.png
	pngtopnm < $< > $@
