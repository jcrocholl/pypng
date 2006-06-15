#!/usr/bin/env python
# png.py - PNG encoder in pure Python
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
from array import array


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


def write(outfile,
          scanlines, width, height,
          interlaced=False, transparent=None, background=None,
          compression=None, chunk_limit=2**20):
    """
    Create a PNG image from RGB data.

    Arguments:
    outfile - something with a write() method
    scanlines - iterator that returns scanlines from top to bottom
    width, height - size of the image in pixels
    interlaced - scanlines are interlaced with Adam7
    transparent - create a tRNS chunk
    compression - zlib compression level (0-9)

    Each scanline must be an array of bytes of length 3*width,
    containing the red, green, blue values for each pixel.

    If the interlaced parameter is set to True, the scanlines are
    expected to be interlaced with the Adam7 scheme. This is good for
    incremental display over a slow network connection, but it
    increases encoding time and memory use by an order of magnitude
    and output file size by a factor of 1.2 or so.

    The transparent parameter can be used to mark a color as
    transparent in the resulting image file. If specified, it must be
    a tuple with three integer values for red, green, blue.
    """
    if transparent is not None:
        assert len(transparent) == 3
        assert type(transparent[0]) is int
        assert type(transparent[1]) is int
        assert type(transparent[2]) is int

    # http://www.w3.org/TR/PNG/#5PNG-file-signature
    outfile.write(struct.pack("8B", 137, 80, 78, 71, 13, 10, 26, 10))

    # http://www.w3.org/TR/PNG/#11IHDR
    if interlaced:
        interlaced = 1
    else:
        interlaced = 0
    write_chunk(outfile, 'IHDR',
        struct.pack("!2I5B", width, height, 8, 2, 0, 0, interlaced))

    # http://www.w3.org/TR/PNG/#11tRNS
    if transparent is not None:
        write_chunk(outfile, 'tRNS', struct.pack("!3H", *transparent))

    # http://www.w3.org/TR/PNG/#11bKGD
    if background is not None:
        write_chunk(outfile, 'bKGD', struct.pack("!3H", *background))


    # http://www.w3.org/TR/PNG/#11IDAT
    if compression is not None:
        compressor = zlib.compressobj(compression)
    else:
        compressor = zlib.compressobj()
    data = array('B')
    for scanline in scanlines:
        data.append(0)
        data.extend(scanline)
        if len(data) > chunk_limit:
            compressed = compressor.compress(data.tostring())
            if len(compressed):
                # print >> sys.stderr, len(data), len(compressed)
                write_chunk(outfile, 'IDAT', compressed)
            data = array('B')
    if len(data):
        compressed = compressor.compress(data.tostring())
        flushed = compressor.flush()
        if len(compressed) or len(flushed):
            # print >> sys.stderr, len(data), len(compressed), len(flushed)
            write_chunk(outfile, 'IDAT', compressed + flushed)

    # http://www.w3.org/TR/PNG/#11IEND
    write_chunk(outfile, 'IEND', '')


def read_pnm_header(infile, supported='P6'):
    """
    Read a PNM header, return width and height of the image in pixels.
    """
    header = []
    while len(header) < 4:
        line = infile.readline()
        sharp = line.find('#')
        if sharp > -1:
            line = line[:sharp]
        header.extend(line.split())
        if len(header) == 3 and header[0] == 'P4':
            break # PBM doesn't have maxval
    if header[0] not in supported:
        raise NotImplementedError('file format %s not supported' % header[0])
    if header[0] != 'P4' and header[3] != '255':
        raise NotImplementedError('maxval %s not supported' % header[3])
    return int(header[1]), int(header[2])


def file_scanlines(infile, width, height):
    """
    Generator for scanlines.
    """
    for y in range(height):
        scanline = array('B')
        scanline.fromfile(infile, 3 * width)
        yield scanline


def array_scanlines(pixels, width, height):
    """
    Generator for scanlines.
    """
    width *= 3
    stop = 0
    for y in range(height):
        start = stop
        stop = start + width
        yield pixels[start:stop]


def array_scanlines_interlace(pixels, width, height):
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
    row_skip = 3 * width
    for xstart, ystart, xstep, ystep in adam7:
        for y in range(ystart, height, ystep):
            if xstart < width:
                if xstep == 1:
                    offset = y*row_skip
                    yield pixels[offset:offset+row_skip]
                else:
                    row = array('B')
                    offset = y*row_skip + xstart*3
                    skip = 3*xstep
                    for x in range(xstart, width, xstep):
                        row.extend(pixels[offset:offset+3])
                        offset += skip
                    yield row


def pnmtopng(infile, outfile,
        interlace=None, transparent=None, background=None,
        gamma=None, compression=None):
    """
    Encode a PNM file into a PNG file.
    """
    width, height = read_pnm_header(infile)
    if interlace:
        pixels = array('B')
        pixels.fromfile(infile, 3*width*height)
        scanlines = array_scanlines_interlace(pixels, width, height)
    else:
        scanlines = file_scanlines(infile, width, height)
    write(outfile, scanlines, width, height,
          interlaced=interlace,
          transparent=transparent,
          background=background,
          compression=compression)


def color_triple(color):
    """
    Convert a command line color value to a RGB triple of integers.
    """
    if color.startswith('#') and len(color) == 7:
        return (int(color[1:3], 16),
                int(color[3:5], 16),
                int(color[5:7], 16))

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
    outfile = sys.stdout
    # Convert options
    if options.transparent is not None:
        options.transparent = color_triple(options.transparent)
    if options.background is not None:
        options.background = color_triple(options.background)
    # Encode PNM to PNG
    pnmtopng(infile, outfile,
             interlace=options.interlace,
             transparent=options.transparent,
             background=options.background,
             gamma=options.gamma,
             compression=options.compression)


if __name__ == '__main__':
    _main()
