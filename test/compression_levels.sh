#!/bin/sh

TEST="../lib/png.py --test"
OUT=output/test

$TEST --compression 0 > $OUT-c0.png
$TEST --compression 1 > $OUT-c1.png
$TEST --compression 2 > $OUT-c2.png
$TEST --compression 3 > $OUT-c3.png
$TEST --compression 4 > $OUT-c4.png
$TEST --compression 5 > $OUT-c5.png
$TEST --compression 6 > $OUT-c6.png
$TEST --compression 7 > $OUT-c7.png
$TEST --compression 8 > $OUT-c8.png
$TEST --compression 9 > $OUT-c9.png
