#!/bin/sh
lib/png.py --test > test/test-rgb-256.png
lib/png.py --test -A GLR > test/test-rgba-256.png
lib/png.py --test -S 255 > test/test-rgb-255.png
lib/png.py --test -S 255 -A GLR > test/test-rgba-255.png
lib/png.py --test -S 257 > test/test-rgb-257.png
lib/png.py --test -S 257 -A GLR > test/test-rgba-257.png
lib/png.py --test -i > test/test-rgb-256i.png
lib/png.py --test -i -A GLR > test/test-rgba-256i.png
lib/png.py --test -i -S 255 > test/test-rgb-255i.png
lib/png.py --test -i -S 255 -A GLR > test/test-rgba-255i.png
lib/png.py --test -i -S 257 > test/test-rgb-257i.png
lib/png.py --test -i -S 257 -A GLR > test/test-rgba-257i.png
