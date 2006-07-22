#!/bin/sh

TEST="../lib/png.py --test"
OUT=output/test

# Plain RGB
$TEST -S 255 > $OUT-rgb-255.png
$TEST -S 256 > $OUT-rgb-256.png
$TEST -S 257 > $OUT-rgb-257.png

# Plain RGBA
$TEST -A GLR -S 255 > $OUT-rgba-256.png
$TEST -A GLR -S 256 > $OUT-rgba-255.png
$TEST -A GLR -S 257 > $OUT-rgba-257.png

# Interlaced RGB
$TEST -i -S 255 > $OUT-rgb-255-i.png
$TEST -i -S 256 > $OUT-rgb-256-i.png
$TEST -i -S 257 > $OUT-rgb-257-i.png

# Interlaced RGBA
$TEST -i -A GLR -S 255 > $OUT-rgba-255-i.png
$TEST -i -A GLR -S 256 > $OUT-rgba-256-i.png
$TEST -i -A GLR -S 257 > $OUT-rgba-257-i.png
