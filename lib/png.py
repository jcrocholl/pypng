#!/usr/bin/env python
# png.py - PNG encoder in pure Python
# Copyright (C) 2006 Johann C. Rocholl <johann@browsershots.org>
#
# This file is licensed alternatively under one of the following:
# 1. GNU Lesser General Public License (LGPL), Version 2.1 or newer
# 2. GNU General Public License (GPL), Version 2 or newer
# 3. Apache License, Version 2.0 or newer
# 4. The following license (aka MIT License)
#
# --------------------- start of license -----------------------------
# Copyright (C) 2006 Johann C. Rocholl <johann@browsershots.org>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ----------------------- end of license -----------------------------
#
# You may not use this file except in compliance with at least one of
# the above four licenses.


"""
PNG encoder in pure Python

This is an implementation of a subset of the PNG specification at
http://www.w3.org/TR/2003/REC-PNG-20031110 in pure Python.

It currently supports encoding of PPM files or raw data with 24 bits
per pixel (RGB) into PNG, with a number of options.

This file can be used in two ways:

1. As a command-line utility to convert PNM files to PNG. The
   interface is similar to that of the pnmtopng program from the
   netpbm package. Try "python png.py --help" for usage information.

2. As a module that can be imported and that offers methods to write
   PNG files directly from your Python program. For help, try the
   following in your python interpreter:
   >>> import png
   >>> help(png)
"""


__revision__ = '$Rev$'
__date__ = '$Date$'
__author__ = '$Author$'


import sys, zlib, struct


def scanlines(width, height, pixels):
    """
    Insert a filter type marker byte before every scanline.
    """
    result = []
    scanline = 3*width
    for y in range(height):
        result.append(chr(0))
        offset = y*scanline
        result.append(pixels[offset:offset+scanline])
    return ''.join(result)




def scanlines_interlace(width, height, pixels):
    """
    Interlace and insert a filter type marker byte before every scanline.
    http://www.w3.org/TR/PNG/#8InterlaceMethods
    """
    adam7 = ((0, 0, 8, 8),
             (4, 0, 8, 8),
             (0, 4, 4, 8),
             (2, 0, 4, 4),
             (0, 2, 2, 4),
             (1, 0, 2, 2),
             (0, 1, 1, 2))
    result = []
    scanline = 3*width
    for xstart, ystart, xstep, ystep in adam7:
        for y in range(ystart, height, ystep):
            if xstart < width:
                result.append(chr(0))
                if xstep == 1:
                    offset = scanline*y
                    result.append(pixels[offset:offset+scanline])
                else:
                    row = []
                    for x in range(xstart, width, xstep):
                        offset = scanline*y + 3*x
                        row.append(pixels[offset:offset+3])
                    result.append(''.join(row))
    return ''.join(result)


def write_chunk(outfile, tag, data):
    """
    Write a PNG chunk to the output file, including length and checksum.
    http://www.w3.org/TR/PNG/#5Chunk-layout
    """
    outfile.write(struct.pack("!I", len(data)))
    outfile.write(tag)
    outfile.write(data)
    checksum = zlib.crc32(tag)
    checksum = zlib.crc32(data, checksum)
    outfile.write(struct.pack("!I", checksum))


def write(outfile, width, height, pixels,
          interlace = False, transparent = None):
    """
    Write a 24bpp RGB opaque PNG to the output file.
    http://www.w3.org/TR/PNG/

    The pixels parameter must be a string of length 3*width*height,
    containing the red, green, blue values for each pixel in rows from
    left to right, top to bottom (the same format that you get when
    reading a PPM file with maxval <= 255).

    If the interlace parameter is set to True, the pixels will be
    re-arranged with the Adam7 scheme. This is good for incremental
    display over a slow network connection, but it increases encoding
    time by a factor of 5 and file size by a factor of 1.2 or so.

    The transparent parameter can be used to mark a color as
    transparent in the resulting image file. If specified, it must be
    a string of length 3 with the red, green, blue values.
    """
    assert type(pixels) is str
    assert len(pixels) == 3*width*height
    if transparent is not None:
        assert type(transparent) is str
        assert len(transparent) == 3
    if interlace:
        interlace = 1
        data = scanlines_interlace(width, height, pixels)
    else:
        interlace = 0
        data = scanlines(width, height, pixels)
    # http://www.w3.org/TR/PNG/#5PNG-file-signature
    outfile.write(struct.pack("8B", 137, 80, 78, 71, 13, 10, 26, 10))
    # http://www.w3.org/TR/PNG/#11IHDR
    write_chunk(outfile, 'IHDR', struct.pack("!2I5B",
                                             width, height,
                                             8, 2, 0, 0, interlace))
    # http://www.w3.org/TR/PNG/#11tRNS
    if transparent is not None:
        transparent = struct.pack("!3H",
                                  ord(transparent[0]),
                                  ord(transparent[1]),
                                  ord(transparent[2]))
        write_chunk(outfile, 'tRNS', transparent)
    # http://www.w3.org/TR/PNG/#11IDAT
    write_chunk(outfile, 'IDAT', zlib.compress(data))
    # http://www.w3.org/TR/PNG/#11IEND
    write_chunk(outfile, 'IEND', '')


def read_header(infile, supported_magic=('P6')):
    """
    Read a PNM header and check if the format is supported.
    Return width and height of the image in pixels.
    """
    magic, width, height, maxval = todo()
    if magic not in supported_magic:
        raise NotImplementedError('file format not supported')
    if maxval != 255:
        raise NotImplementedError('only maxval 255 is supported')
    return width, height


def pnmtopng(infile, outfile,
        interlace=None, transparent=None, background=None,
        alpha=None, gamma=None, compression=None):
    """
    Encode a PNM file into a PNG file.
    """
    width, height = read_header(infile)
    if alpha:
        if read_header(alpha, 'P4') != (width, height):
            raise ValueError('alpha channel has different image size')


def _main():
    """
    Run the PNG encoder with options from the command line.
    """
    # Parse command line arguments
    from optparse import OptionParser
    version = '%prog ' + __revision__.strip('$').replace('Rev: ', 'r')
    parser = OptionParser(version=version)
    parser.set_usage("%prog [options] [pnmfile]")
    parser.add_option("--interlace", default=False, action="store_true",
                      help="create an interlaced PNG file (Adam7)")
    parser.add_option("--transparent",
                      action="store", type="string", metavar="color",
                      help="mark the specified color as transparent")
    parser.add_option("--background",
                      action="store", type="string", metavar="color",
                      help="store the specified background color")
    parser.add_option("--alpha",
                      action="store", type="string", metavar="pgmfile",
                      help="alpha channel transparency (RGBA)")
    parser.add_option("--gamma",
                      action="store", type="float", metavar="value",
                      help="store the specified gamma value")
    parser.add_option("--compression",
                      action="store", type="int", metavar="level",
                      help="zlib compression level (0-9)")
    (options, args) = parser.parse_args()
    # Prepare input and output files
    if len(args) == 0:
        infile = sys.stdin
    elif len(args) == 1:
        infile = open(args[0], 'rb')
    else:
        parser.error("more than one input file")
    if options.alpha:
        options.alpha = open(options.alpha, 'rb')
    outfile = sys.stdout
    # Encode PNM to PNG
    pnmtopng(infile, outfile,
             interlace=options.interlace,
             transparent=options.transparent,
             background=options.background,
             gamma=options.gamma,
             alpha=options.alpha,
             compression=options.compression)


if __name__ == '__main__':
    _main()
