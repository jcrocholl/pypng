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
#
# Changelog (recent first):
# 2006-06-17 Alpha-channel, grey-scale, 16-bit/plane support and test
#     suite added by Nicko van Someren <nicko@nicko.org>
# 2006-06-15 Scanline iterator interface to avoid storing the whole
#     input data in memory
# 2006-06-09 Very simple prototype implementation


"""
PNG encoder in pure Python

This is an implementation of a subset of the PNG specification at
http://www.w3.org/TR/2003/REC-PNG-20031110 in pure Python.

It supports encoding of PPM files or raw data with 8/16/24/32/48/64
bits per pixel (greyscale, RGB or RGBA) into PNG, with a number of
options.

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


import sys, zlib, struct, math
from array import array


def write_chunk(outfile, tag, data):
    """
    Write a PNG chunk to the output file, including length and checksum.
    """
    # http://www.w3.org/TR/PNG/#5Chunk-layout
    outfile.write(struct.pack("!I", len(data)))
    outfile.write(tag)
    outfile.write(data)
    checksum = zlib.crc32(tag)
    checksum = zlib.crc32(data, checksum)
    outfile.write(struct.pack("!I", checksum))


def read_chunk(infile):
    """
    Read a PNG chunk from the input file, return tag name and data.
    """
    # http://www.w3.org/TR/PNG/#5Chunk-layout
    data_bytes, tag = struct.unpack('!I4s', infile.read(8))
    data = infile.read(data_bytes)
    checksum = struct.unpack('!i', infile.read(4))[0]
    verify = zlib.crc32(tag)
    verify = zlib.crc32(data, verify)
    if checksum != verify:
        raise ValueError('checksum error in %s chunk: %x != %x'
                         % (tag, checksum, verify))
    return tag, data


def write(outfile, scanlines, width, height,
          interlaced=False, transparent=None, background=None,
          gamma=None, greyscale=False, has_alpha=False,
          bytes_per_sample=1, compression=None, chunk_limit=2**20):
    """
    Create a PNG image from RGB data.

    Arguments:
    outfile - something with a write() method
    scanlines - iterator that returns scanlines from top to bottom
    width, height - size of the image in pixels
    interlaced - scanlines are interlaced with Adam7
    transparent - create a tRNS chunk
    background - create a bKGD chunk
    gamma - create a gAMA chunk
    greyscale - input data is greyscale, not RGB
    has_alpha - input data has alpha channel
    bytes_per_sample - 8-bit or 16-bit input data
    compression - zlib compression level (1-9)
    chunk_limit - write multiple IDAT chunks to preserve memory

    Each scanline must be an array of bytes containing the red, green,
    blue (or gray, and maybe alpha) values for each pixel.

    If the interlaced parameter is set to True, the scanlines are
    expected to be interlaced with the Adam7 scheme. This is good for
    incremental display over a slow network connection, but it
    increases encoding time and memory use by an order of magnitude
    and output file size by a factor of 1.2 or so.

    If specified, the transparent and background parameters must be a
    tuple with three integer values for red, green, blue.

    If specified, the gamma parameter must be a float value.
    """
    if transparent is not None:
        assert len(transparent) == 3
        assert type(transparent[0]) is int
        assert type(transparent[1]) is int
        assert type(transparent[2]) is int

    if bytes_per_sample < 1 or bytes_per_sample > 2:
        raise ValueError("bytes per sample must be 1 or 2")

    if has_alpha and transparent is not None:
        raise ValueError("transparent color not allowed with alpha channel")

    if gamma is not None:
        assert type(gamma) is float

    if compression is not None:
        assert type(compression) is int
        assert 1 <= compression <= 9

    if greyscale:
        if has_alpha:
            color_type = 4
            psize = bytes_per_sample * 2
        else:
            color_type = 0
            psize = bytes_per_sample
    else:
        if has_alpha:
            color_type = 6
            psize = bytes_per_sample * 4
        else:
            color_type = 2
            psize = bytes_per_sample * 3

    # http://www.w3.org/TR/PNG/#5PNG-file-signature
    outfile.write(struct.pack("8B", 137, 80, 78, 71, 13, 10, 26, 10))

    # http://www.w3.org/TR/PNG/#11IHDR
    if interlaced:
        interlaced = 1
    else:
        interlaced = 0
    write_chunk(outfile, 'IHDR',
        struct.pack("!2I5B", width, height, bytes_per_sample * 8,
                    color_type, 0, 0, interlaced))

    # http://www.w3.org/TR/PNG/#11tRNS
    if transparent is not None:
        write_chunk(outfile, 'tRNS', struct.pack("!3H", *transparent))

    # http://www.w3.org/TR/PNG/#11bKGD
    if background is not None:
        write_chunk(outfile, 'bKGD', struct.pack("!3H", *background))

    # http://www.w3.org/TR/PNG/#11gAMA
    if gamma is not None:
        write_chunk(outfile, 'gAMA', struct.pack("!L", int(gamma * 100000)))

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


def _reconstruct_sub(pixels, offset, row_bytes, psize):
    """Reverse sub filter."""
    for index in range(row_bytes):
        x = pixels[offset]
        if index < psize:
            a = 0
        else:
            a = pixels[offset-psize]
        pixels[offset] = (x + a) & 0xff
        offset += 1


def _reconstruct_up(pixels, offset, row_bytes, psize):
    """Reverse up filter."""
    above = offset - row_bytes
    for index in range(row_bytes):
        x = pixels[offset]
        if above < 0:
            b = 0
        else:
            b = pixels[above]
        pixels[offset] = (x + b) & 0xff
        offset += 1
        above += 1


def _reconstruct_average(pixels, offset, row_bytes, psize):
    """Reverse average filter."""
    above = offset - row_bytes
    for index in range(row_bytes):
        x = pixels[offset]
        if index < psize:
            a = 0
        else:
            a = pixels[offset-psize]
        if above < 0:
            b = 0
        else:
            b = pixels[above]
        pixels[offset] = (x + (a + b) / 2) & 0xff
        offset += 1
        above += 1


def _reconstruct_paeth(pixels, offset, row_bytes, psize):
    """Reverse Paeth filter."""
    offset_a = offset - psize
    offset_b = offset - row_bytes
    offset_c = offset_b - psize
    for index in range(row_bytes):
        x = pixels[offset]
        if index < psize:
            a = c = 0
            # if offset_b < 0:
            #     b = 0
            # else:
            b = pixels[offset_b]
        else:
            a = pixels[offset_a]
            # if offset_b < 0:
            #     b = c = 0
            # else:
            b = pixels[offset_b]
            c = pixels[offset_c]
        p = a + b - c
        pa = abs(p - a)
        pb = abs(p - b)
        pc = abs(p - c)
        if pa <= pb and pa <= pc:
            pr = a
        elif pb <= pc:
            pr = b
        else:
            pr = c
        pixels[offset] = (x + pr) & 0xff
        offset += 1
        offset_a += 1
        offset_b += 1
        offset_c += 1


def read(infile):
    """
    Read a simple PNG file, return width, height, pixels.

    This function is a very early prototype with limited flexibility
    and excessive use of memory.
    """
    signature = infile.read(8)
    assert signature == struct.pack("8B", 137, 80, 78, 71, 13, 10, 26, 10)
    compressed = []
    while True:
        tag, data = read_chunk(infile)
        # print tag, len(data)
        if tag == 'IHDR': # http://www.w3.org/TR/PNG/#11IHDR
            (width, height, bits_per_sample, color_type,
             compression_method, filter_method,
             interlaced) = struct.unpack("!2I5B", data)
            assert bits_per_sample == 8
            assert color_type == 2
            assert compression_method == 0
            assert filter_method == 0
            assert interlaced == 0
        if tag == 'IDAT': # http://www.w3.org/TR/PNG/#11IDAT
            compressed.append(data)
        if tag == 'IEND': # http://www.w3.org/TR/PNG/#11IEND
            break
    scanlines = zlib.decompress(''.join(compressed))
    pixels = array('B')
    offset = 0
    row_bytes = 3*width
    for y in range(height):
        filter_type = ord(scanlines[offset])
        # print >> sys.stderr, y, filter_type
        offset += 1
        pixels.fromstring(scanlines[offset:offset+row_bytes])
        if filter_type == 1:
            _reconstruct_sub(pixels, y*row_bytes, row_bytes, 3)
        elif filter_type == 2:
            _reconstruct_up(pixels, y*row_bytes, row_bytes, 3)
        elif filter_type == 3:
            _reconstruct_average(pixels, y*row_bytes, row_bytes, 3)
        elif filter_type == 4:
            _reconstruct_paeth(pixels, y*row_bytes, row_bytes, 3)
        offset += row_bytes
    return width, height, pixels

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


def file_scanlines(infile, width, height, psize):
    """
    Generator for scanlines from an input file.
    """
    row_bytes = psize*width
    for y in range(height):
        scanline = array('B')
        scanline.fromfile(infile, row_bytes)
        yield scanline


def array_scanlines(pixels, width, height, psize):
    """
    Generator for scanlines from an array.
    """
    width *= psize
    stop = 0
    for y in range(height):
        start = stop
        stop = start + width
        yield pixels[start:stop]


def array_scanlines_interlace(pixels, width, height, psize):
    """
    Generator for interlaced scanlines from an array.
    http://www.w3.org/TR/PNG/#8InterlaceMethods
    """
    adam7 = ((0, 0, 8, 8),
             (4, 0, 8, 8),
             (0, 4, 4, 8),
             (2, 0, 4, 4),
             (0, 2, 2, 4),
             (1, 0, 2, 2),
             (0, 1, 1, 2))
    row_bytes = psize * width
    for xstart, ystart, xstep, ystep in adam7:
        for y in range(ystart, height, ystep):
            if xstart < width:
                if xstep == 1:
                    offset = y*row_bytes
                    yield pixels[offset:offset+row_bytes]
                else:
                    row = array('B')
                    offset = y*row_bytes + xstart*psize
                    skip = psize*xstep
                    for x in range(xstart, width, xstep):
                        row.extend(pixels[offset:offset+psize])
                        offset += skip
                    yield row


def interleave_planes(ipixels, apixels, width, height, ipsize, apsize):
    """
    Interleave color planes, e.g. RGB + A = RGBA.
    """
    pixelcount = width * height
    newpsize = ipsize + apsize
    itotal = pixelcount * ipsize
    atotal = pixelcount * apsize
    newtotal = pixelcount * newpsize
    # Set up the output buffer
    out = array('B')
    # It's annoying that there is no cheap way to set the array size :-(
    out.extend(ipixels)
    out.extend(apixels)
    # Interleave in the pixel data
    for i in range(ipsize):
        out[i:newtotal:newpsize] = ipixels[i:itotal:ipsize]
    for i in range(apsize):
        out[i+ipsize:newtotal:newpsize] = apixels[i:atotal:apsize]
    return out


def pnmtopng(infile, outfile,
        interlace=None, transparent=None, background=None,
        alpha=None, gamma=None, compression=None):
    """
    Encode a PNM file into a PNG file.
    """
    width, height = read_pnm_header(infile)
    if alpha is None and not interlace:
        scanlines = file_scanlines(infile, width, height, 3)
    else:
        psize = 3
        pixels = array('B')
        pixels.fromfile(infile, 3*width*height)
        if alpha is not None:
            if read_pnm_header(alpha, 'P5') != (width, height):
                raise ValueError('alpha channel has different image size')
            alpha_pixels = array('B')
            alpha_pixels.fromfile(alpha, width*height)
            pixels = interleave_planes(pixels, alpha_pixels,
                                       width, height, psize, 1)
            psize = 4
        if interlace:
            scanlines = array_scanlines_interlace(pixels, width, height, psize)
        else:
            scanlines = array_scanlines(pixels, width, height, psize)
    write(outfile, scanlines, width, height,
          interlaced=interlace,
          transparent=transparent,
          background=background,
          gamma=gamma,
          compression=compression,
          has_alpha=alpha is not None)


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
    parser.add_option("--alpha",
                      action="store", type="string", metavar="pgmfile",
                      help="alpha channel transparency (RGBA)")
    parser.add_option("--gamma",
                      action="store", type="float", metavar="value",
                      help="store the specified gamma value")
    parser.add_option("--compression",
                      action="store", type="int", metavar="level",
                      help="zlib compression level (0-9)")
    parser.add_option("--test", default=False, action="store_true",
                      help="run regression tests")
    (options, args) = parser.parse_args()
    # Run regression tests
    if options.test:
        return test_suite()
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
             alpha=options.alpha,
             compression=options.compression)


# Below is a big stack of test image generators

def _test_gradient_horizontal_lr(x, y):
    return x

def _test_gradient_horizontal_rl(x, y):
    return 1-x

def _test_gradient_vertical_tb(x, y):
    return y

def _test_gradient_vertical_bt(x, y):
    return 1-y

def _test_radial_tl(x, y):
    return max(1-math.sqrt(x*x+y*y), 0.0)

def _test_radial_center(x, y):
    return _test_radial_tl(x-0.5, y-0.5)

def _test_radial_tr(x, y):
    return _test_radial_tl(1-x, y)

def _test_radial_bl(x, y):
    return _test_radial_tl(x, 1-y)

def _test_radial_br(x, y):
    return _test_radial_tl(1-x, 1-y)

def _test_stripe(x, n):
    return 1.0*(int(x*n) & 1)

def _test_stripe_h_2(x, y):
    return _test_stripe(x, 2)

def _test_stripe_h_4(x, y):
    return _test_stripe(x, 4)

def _test_stripe_h_10(x, y):
    return _test_stripe(x, 10)

def _test_stripe_v_2(x, y):
    return _test_stripe(y, 2)

def _test_stripe_v_4(x, y):
    return _test_stripe(y, 4)

def _test_stripe_v_10(x, y):
    return _test_stripe(y, 10)

def _test_stripe_lr_10(x, y):
    return _test_stripe(x+y, 10)

def _test_stripe_rl_10(x, y):
    return _test_stripe(x-y, 10)

def _test_checker(x, y, n):
    return 1.0*((int(x*n) & 1) ^ (int(y*n) & 1))

def _test_checker_8(x, y):
    return _test_checker(x, y, 8)

def _test_checker_15(x, y):
    return _test_checker(x, y, 15)


_test_patterns = {
    "GLR" : _test_gradient_horizontal_lr,
    "GRL" : _test_gradient_horizontal_rl,
    "GTB" : _test_gradient_vertical_tb,
    "GBT" : _test_gradient_vertical_bt,
    "RTL" : _test_radial_tl,
    "RTR" : _test_radial_tr,
    "RBL" : _test_radial_bl,
    "RBR" : _test_radial_br,
    "RCTR" : _test_radial_center,
    "HS2" : _test_stripe_h_2,
    "HS4" : _test_stripe_h_4,
    "HS10" : _test_stripe_h_10,
    "VS2" : _test_stripe_v_2,
    "VS4" : _test_stripe_v_4,
    "VS10" : _test_stripe_v_10,
    "LRS" : _test_stripe_lr_10,
    "RLS" : _test_stripe_rl_10,
    "CK8" : _test_checker_8,
    "CK15" : _test_checker_15,
}


def _test_pattern(width, height, depth, pattern):
    """
    Generate an image from a test pattern.
    """
    a = array('B')
    fw = float(width)
    fh = float(height)
    pfun = _test_patterns[pattern]
    if depth == 1:
        for y in range(height):
            for x in range(width):
                a.append(int(pfun(float(x)/fw, float(y)/fh) * 255))
    elif depth == 2:
        for y in range(height):
            for x in range(width):
                v = int(pfun(float(x)/fw, float(y)/fh) * 65535)
                a.append(v >> 8)
                a.append(v & 0xff)
    return a


def _write_test(fname):
    """
    Create a test image with alpha channel.
    """
    out = open(fname, "wb")
    r = _test_pattern(256, 256, 1, "GTB")
    g = _test_pattern(256, 256, 1, "RCTR")
    b = _test_pattern(256, 256, 1, "LRS")
    a = _test_pattern(256, 256, 1, "GLR")
    i = interleave_planes(r, g, 256, 256, 1, 1)
    i = interleave_planes(i, b, 256, 256, 2, 1)
    i = interleave_planes(i, a, 256, 256, 3, 1)
    scanlines = array_scanlines(i, 256, 256, 4)
    write(out, scanlines, 256, 256, has_alpha=True)


def test_suite():
    """
    Run regression tests and produce PNG files in current directory.
    """
    _write_test('mixed.png')
    return 0


if __name__ == '__main__':
    _main()
