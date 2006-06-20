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
# Contributors (alphabetical):
# Nicko van Someren <nicko@nicko.org>
#
# Changelog (recent first):
# 2006-06-17 Nicko: Reworked into a class, faster interlacing.
# 2006-06-17 Johann: Very simple prototype PNG decoder.
# 2006-06-17 Nicko: Test suite with various image generators.
# 2006-06-17 Nicko: Alpha-channel, grey-scale, 16-bit/plane support.
# 2006-06-15 Johann: Scanline iterator interface for large input files.
# 2006-06-09 Johann: Very simple prototype PNG encoder.


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


def interleave_planes(ipixels, apixels, width, height, ipsize, apsize):
    """
    Interleave color planes, e.g. RGB + A = RGBA.

    Return an array of pixels consisting of the ipsize bytes of data
    from each pixel in ipixels followed by the apsize bytes of data
    from each pixel in apixels, for an image of size width x height.
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


class Writer:
    """
    PNG encoder in pure Python.
    """

    def __init__(self, width, height,
                 transparent=None,
                 background=None,
                 gamma=None,
                 greyscale=False,
                 has_alpha=False,
                 bytes_per_sample=1,
                 compression=None,
                 chunk_limit=2**20):
        """
        Create a PNG encoder object.

        Arguments:
        width, height - size of the image in pixels
        transparent - create a tRNS chunk
        background - create a bKGD chunk
        gamma - create a gAMA chunk
        greyscale - input data is greyscale, not RGB
        has_alpha - input data has alpha channel
        bytes_per_sample - 8-bit or 16-bit input data
        compression - zlib compression level (1-9)
        chunk_limit - write multiple IDAT chunks to preserve memory

        If specified, the transparent and background parameters must
        be a tuple with three integer values for red, green, blue.

        If specified, the gamma parameter must be a float value.

        """
        if width <= 0 or height <= 0:
            raise ValueError("Width and height must be greater than zero")

        if has_alpha and transparent is not None:
            raise ValueError(
                "Transparent color not allowed with alpha channel")

        if bytes_per_sample < 1 or bytes_per_sample > 2:
            raise ValueError("Bytes per sample must be 1 or 2")

        if transparent is not None:
            if greyscale:
                if type(transparent) is not int:
                    raise ValueError(
                        "Transparent color for greyscale must be integer")
            else:
                if not (len(transparent) == 3 and
                        type(transparent[0]) is int and
                        type(transparent[1]) is int and
                        type(transparent[2]) is int):
                    raise ValueError(
                        "Transparent color must be a triple of integers")

        if background is not None:
            if greyscale:
                if type(background) is not int:
                    raise ValueError(
                        "Background color for greyscale must be integer")
            else:
                if not (len(background) == 3 and
                        type(background[0]) is int and
                        type(background[1]) is int and
                        type(background[2]) is int):
                    raise ValueError(
                        "Background color must be a triple of integers")

        self.width = width
        self.height = height
        self.transparent = transparent
        self.background = background
        self.gamma = gamma
        self.greyscale = greyscale
        self.has_alpha = has_alpha
        self.bytes_per_sample = bytes_per_sample
        self.compression = compression
        self.chunk_limit = chunk_limit

        if self.greyscale:
            self.color_depth = 1
            if self.has_alpha:
                self.color_type = 4
                self.psize = self.bytes_per_sample * 2
            else:
                self.color_type = 0
                self.psize = self.bytes_per_sample
        else:
            self.color_depth = 3
            if self.has_alpha:
                self.color_type = 6
                self.psize = self.bytes_per_sample * 4
            else:
                self.color_type = 2
                self.psize = self.bytes_per_sample * 3

    def write_chunk(self, outfile, tag, data):
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

    def write(self, outfile, scanlines, interlaced=False):
        """
        Write a PNG image to the output file.
        """
        # http://www.w3.org/TR/PNG/#5PNG-file-signature
        outfile.write(struct.pack("8B", 137, 80, 78, 71, 13, 10, 26, 10))

        # http://www.w3.org/TR/PNG/#11IHDR
        if interlaced:
            interlaced = 1
        else:
            interlaced = 0
        self.write_chunk(outfile, 'IHDR',
                         struct.pack("!2I5B", self.width, self.height,
                                     self.bytes_per_sample * 8,
                                     self.color_type, 0, 0, interlaced))

        # http://www.w3.org/TR/PNG/#11tRNS
        if self.transparent is not None:
            if self.greyscale:
                self.write_chunk(outfile, 'tRNS',
                                 struct.pack("!1H", *self.transparent))
            else:
                self.write_chunk(outfile, 'tRNS',
                                 struct.pack("!3H", *self.transparent))

        # http://www.w3.org/TR/PNG/#11bKGD
        if self.background is not None:
            if self.greyscale:
                self.write_chunk(outfile, 'bKGD',
                                 struct.pack("!1H", *self.background))
            else:
                self.write_chunk(outfile, 'bKGD',
                                 struct.pack("!3H", *self.background))

        # http://www.w3.org/TR/PNG/#11gAMA
        if self.gamma is not None:
            self.write_chunk(outfile, 'gAMA',
                             struct.pack("!L", int(self.gamma * 100000)))

        # http://www.w3.org/TR/PNG/#11IDAT
        if self.compression is not None:
            compressor = zlib.compressobj(self.compression)
        else:
            compressor = zlib.compressobj()

        data = array('B')
        for scanline in scanlines:
            data.append(0)
            data.extend(scanline)
            if len(data) > self.chunk_limit:
                compressed = compressor.compress(data.tostring())
                if len(compressed):
                    # print >> sys.stderr, len(data), len(compressed)
                    self.write_chunk(outfile, 'IDAT', compressed)
                data = array('B')
        if len(data):
            compressed = compressor.compress(data.tostring())
        else:
            compressed = ''
        flushed = compressor.flush()
        if len(compressed) or len(flushed):
            # print >> sys.stderr, len(data), len(compressed), len(flushed)
            self.write_chunk(outfile, 'IDAT', compressed + flushed)

        # http://www.w3.org/TR/PNG/#11IEND
        self.write_chunk(outfile, 'IEND', '')

    def write_array(self, outfile, pixels, interlace=False):
        """
        Encode a pixel array to PNG and write output file.
        """
        if interlace:
            self.write(outfile, self.array_scanlines_interlace(pixels),
                       interlaced=True)
        else:
            self.write(outfile, self.array_scanlines(pixels))

    def convert_ppm(self, ppmfile, outfile, interlace=False):
        """
        Convert a PPM file containing raw pixel data into a PNG file
        with the parameters set in the writer object.
        """
        if interlace:
            pixels = array('B')
            pixels.fromfile(ppmfile,
                            self.bytes_per_sample * self.color_depth *
                            self.width * self.height)
            self.write(outfile, self.array_scanlines_interlace(pixels),
                       interlaced=True)
        else:
            self.write(outfile, self.file_scanlines(ppmfile))

    def convert_ppm_and_pgm(self, ppmfile, pgmfile, outfile, interlace=False):
        """
        Convert a PPM and PGM file containing raw pixel data into a
        PNG outfile with the parameters set in the writer object.
        """
        pixels = array('B')
        pixels.fromfile(ppmfile,
                        self.bytes_per_sample * self.color_depth *
                        self.width * self.height)
        apixels = array('B')
        apixels.fromfile(pgmfile,
                         self.bytes_per_sample *
                         self.width * self.height)
        pixels = interleave_planes(pixels, apixels, self.width, self.height,
                                   self.bytes_per_sample * self.color_depth,
                                   self.bytes_per_sample)
        if interlace:
            self.write(outfile, self.array_scanlines_interlace(pixels),
                       interlaced=True)
        else:
            self.write(outfile, self.array_scanlines(pixels))

    def file_scanlines(self, infile):
        """
        Generator for scanlines from an input file.
        """
        row_bytes = self.psize * self.width
        for y in range(self.height):
            scanline = array('B')
            scanline.fromfile(infile, row_bytes)
            yield scanline

    def array_scanlines(self, pixels):
        """
        Generator for scanlines from an array.
        """
        row_bytes = self.width * self.psize
        stop = 0
        for y in range(self.height):
            start = stop
            stop = start + row_bytes
            yield pixels[start:stop]

    def old_array_scanlines_interlace(self, pixels):
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
        row_bytes = self.psize * self.width
        for xstart, ystart, xstep, ystep in adam7:
            for y in range(ystart, self.height, ystep):
                if xstart < self.width:
                    if xstep == 1:
                        offset = y*row_bytes
                        yield pixels[offset:offset+row_bytes]
                    else:
                        row = array('B')
                        offset = y*row_bytes + xstart* self.psize
                        skip = self.psize * xstep
                        for x in range(xstart, self.width, xstep):
                            row.extend(pixels[offset:offset + self.psize])
                            offset += skip
                        yield row

    def array_scanlines_interlace(self, pixels):
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
        row_bytes = self.psize * self.width
        for xstart, ystart, xstep, ystep in adam7:
            for y in range(ystart, self.height, ystep):
                if xstart >= self.width:
                    continue
                if xstep == 1:
                    offset = y * row_bytes
                    yield pixels[offset:offset+row_bytes]
                else:
                    row = array('B')
                    # Note we want the ceiling of (self.width - xstart) / xtep
                    row_len = self.psize * (
                        (self.width - xstart + xstep - 1) / xstep)
                    # There's no easier way to set the length of an array
                    row.extend(pixels[0:row_len])
                    offset = y * row_bytes + xstart * self.psize
                    end_offset = (y+1) * row_bytes
                    skip = self.psize * xstep
                    for i in range(self.psize):
                        row[i:row_len:self.psize] = \
                            pixels[offset+i:end_offset:skip]
                    yield row


class Reader:
    """
    PNG decoder in pure Python.
    """

    def read_chunk(self, infile):
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

    def _reconstruct_sub(self, pixels, offset, row_bytes, psize):
        """Reverse sub filter."""
        a_offset = offset
        offset += psize
        for index in range(psize, row_bytes):
            x = pixels[offset]
            a = pixels[a_offset]
            pixels[offset] = (x + a) & 0xff
            offset += 1
            a_offset += 1

    def _reconstruct_up(self, pixels, offset, row_bytes, psize):
        """Reverse up filter."""
        b_offset = offset - row_bytes
        for index in range(row_bytes):
            x = pixels[offset]
            b = pixels[b_offset]
            pixels[offset] = (x + b) & 0xff
            offset += 1
            b_offset += 1

    def _reconstruct_average(self, pixels, offset, row_bytes, psize):
        """Reverse average filter."""
        a_offset = offset - psize
        b_offset = offset - row_bytes
        for index in range(row_bytes):
            x = pixels[offset]
            if index < psize:
                a = 0
            else:
                a = pixels[offset-psize]
            if b_offset < 0:
                b = 0
            else:
                b = pixels[b_offset]
            pixels[offset] = (x + (a + b) / 2) & 0xff
            offset += 1
            a_offset += 1
            b_offset += 1

    def _reconstruct_paeth(self, pixels, offset, row_bytes, psize):
        """Reverse Paeth filter."""
        a_offset = offset - psize
        b_offset = offset - row_bytes
        c_offset = b_offset - psize
        for index in range(row_bytes):
            x = pixels[offset]
            if index < psize:
                a = c = 0
                # if offset_b < 0:
                #     b = 0
                # else:
                b = pixels[b_offset]
            else:
                a = pixels[a_offset]
                # if offset_b < 0:
                #     b = c = 0
                # else:
                b = pixels[b_offset]
                c = pixels[c_offset]
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
            a_offset += 1
            b_offset += 1
            c_offset += 1

    def read(self, infile):
        """
        Read a simple PNG file, return width, height, pixels.

        This function is a very early prototype with limited flexibility
        and excessive use of memory.
        """
        signature = infile.read(8)
        assert signature == struct.pack("8B", 137, 80, 78, 71, 13, 10, 26, 10)
        compressed = []
        while True:
            tag, data = self.read_chunk(infile)
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
                # print >> sys.stderr, 'IDAT', len(compressed)
            if tag == 'IEND': # http://www.w3.org/TR/PNG/#11IEND
                break
        scanlines = zlib.decompress(''.join(compressed))
        pixels = array('B')
        offset = 0
        row_bytes = 3*width
        print >> sys.stderr, 'scanlines', len(scanlines), \
              len(scanlines) / (row_bytes + 1)
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


def test_suite(options):
    """
    Run regression test and write PNG file to stdout.
    """

    # Below is a big stack of test image generators

    def test_gradient_horizontal_lr(x, y):
        return x

    def test_gradient_horizontal_rl(x, y):
        return 1-x

    def test_gradient_vertical_tb(x, y):
        return y

    def test_gradient_vertical_bt(x, y):
        return 1-y

    def test_radial_tl(x, y):
        return max(1-math.sqrt(x*x+y*y), 0.0)

    def test_radial_center(x, y):
        return test_radial_tl(x-0.5, y-0.5)

    def test_radial_tr(x, y):
        return test_radial_tl(1-x, y)

    def test_radial_bl(x, y):
        return test_radial_tl(x, 1-y)

    def test_radial_br(x, y):
        return test_radial_tl(1-x, 1-y)

    def test_stripe(x, n):
        return 1.0*(int(x*n) & 1)

    def test_stripe_h_2(x, y):
        return test_stripe(x, 2)

    def test_stripe_h_4(x, y):
        return test_stripe(x, 4)

    def test_stripe_h_10(x, y):
        return test_stripe(x, 10)

    def test_stripe_v_2(x, y):
        return test_stripe(y, 2)

    def test_stripe_v_4(x, y):
        return test_stripe(y, 4)

    def test_stripe_v_10(x, y):
        return test_stripe(y, 10)

    def test_stripe_lr_10(x, y):
        return test_stripe(x+y, 10)

    def test_stripe_rl_10(x, y):
        return test_stripe(x-y, 10)

    def test_checker(x, y, n):
        return 1.0*((int(x*n) & 1) ^ (int(y*n) & 1))

    def test_checker_8(x, y):
        return test_checker(x, y, 8)

    def test_checker_15(x, y):
        return test_checker(x, y, 15)

    test_patterns = {
        "GLR" : test_gradient_horizontal_lr,
        "GRL" : test_gradient_horizontal_rl,
        "GTB" : test_gradient_vertical_tb,
        "GBT" : test_gradient_vertical_bt,
        "RTL" : test_radial_tl,
        "RTR" : test_radial_tr,
        "RBL" : test_radial_bl,
        "RBR" : test_radial_br,
        "RCTR" : test_radial_center,
        "HS2" : test_stripe_h_2,
        "HS4" : test_stripe_h_4,
        "HS10" : test_stripe_h_10,
        "VS2" : test_stripe_v_2,
        "VS4" : test_stripe_v_4,
        "VS10" : test_stripe_v_10,
        "LRS" : test_stripe_lr_10,
        "RLS" : test_stripe_rl_10,
        "CK8" : test_checker_8,
        "CK15" : test_checker_15,
        }

    def test_pattern(width, height, depth, pattern):
        a = array('B')
        fw = float(width)
        fh = float(height)
        pfun = test_patterns[pattern]
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

    def test_rgba(size=256, depth=1,
                    red="GTB", green="RCTR", blue="LRS", alpha=None):
        r = test_pattern(size, size, depth, red)
        g = test_pattern(size, size, depth, green)
        b = test_pattern(size, size, depth, blue)
        if alpha:
            a = test_pattern(size, size, depth, alpha)
        i = interleave_planes(r, g, size, size, depth, depth)
        i = interleave_planes(i, b, size, size, 2 * depth, depth)
        if alpha:
            i = interleave_planes(i, a, size, size, 3 * depth, depth)
        return i

    # The body of test_suite()
    size = 256
    if options.test_size:
        size = options.test_size
    depth = 1
    if options.test_deep:
        depth = 2

    kwargs = {}
    if options.test_red:
        kwargs["red"] = options.test_red
    if options.test_green:
        kwargs["green"] = options.test_green
    if options.test_blue:
        kwargs["blue"] = options.test_blue
    if options.test_alpha:
        kwargs["alpha"] = options.test_alpha
    pixels = test_rgba(size, depth, **kwargs)

    writer = Writer(size, size,
                    bytes_per_sample=depth,
                    transparent=options.transparent,
                    background=options.background,
                    gamma=options.gamma,
                    has_alpha=options.test_alpha,
                    compression=options.compression)
    writer.write_array(sys.stdout, pixels,
                       interlace=options.interlace)
    return 0


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


# FIXME: Somewhere we need support for greyscale backgrounds etc.
def color_triple(color):
    """
    Convert a command line color value to a RGB triple of integers.
    """
    if color.startswith('#') and len(color) == 4:
        return (int(color[1], 16),
                int(color[2], 16),
                int(color[3], 16))
    if color.startswith('#') and len(color) == 7:
        return (int(color[1:3], 16),
                int(color[3:5], 16),
                int(color[5:7], 16))
    elif color.startswith('#') and len(color) == 13:
        return (int(color[1:5], 16),
                int(color[5:9], 16),
                int(color[9:13], 16))


def _main():
    """
    Run the PNG encoder with options from the command line.
    """
    # Parse command line arguments
    from optparse import OptionParser
    version = '%prog ' + __revision__.strip('$').replace('Rev: ', 'r')
    parser = OptionParser(version=version)
    parser.set_usage("%prog [options] [pnmfile]")
    parser.add_option("-i", "--interlace",
                      default=False, action="store_true",
                      help="create an interlaced PNG file (Adam7)")
    parser.add_option("-t", "--transparent",
                      action="store", type="string", metavar="color",
                      help="mark the specified color as transparent")
    parser.add_option("-b", "--background",
                      action="store", type="string", metavar="color",
                      help="store the specified background color")
    parser.add_option("-a", "--alpha",
                      action="store", type="string", metavar="pgmfile",
                      help="alpha channel transparency (RGBA)")
    parser.add_option("-g", "--gamma",
                      action="store", type="float", metavar="value",
                      help="store the specified gamma value")
    parser.add_option("-c", "--compression",
                      action="store", type="int", metavar="level",
                      help="zlib compression level (0-9)")
    parser.add_option("-d", "--decode",
                      default=False, action="store_true",
                      help="decode a simple PNG file, write a PPM file")
    parser.add_option("-T", "--test",
                      default=False, action="store_true",
                      help="run regression tests")
    parser.add_option("-R", "--test-red",
                      action="store", type="string", metavar="pattern",
                      help="test pattern for the red image layer")
    parser.add_option("-G", "--test-green",
                      action="store", type="string", metavar="pattern",
                      help="test pattern for the green image layer")
    parser.add_option("-B", "--test-blue",
                      action="store", type="string", metavar="pattern",
                      help="test pattern for the blue image layer")
    parser.add_option("-A", "--test-alpha",
                      action="store", type="string", metavar="pattern",
                      help="test pattern for the alpha image layer")
    parser.add_option("-D", "--test-deep",
                      default=False, action="store_true",
                      help="make test pattern 16 bit per layer deep")
    parser.add_option("-S", "--test-size",
                      action="store", type="int", metavar="size",
                      help="linear size of the test image")
    (options, args) = parser.parse_args()

    # Convert options
    if options.transparent is not None:
        options.transparent = color_triple(options.transparent)
    if options.background is not None:
        options.background = color_triple(options.background)

    # Run regression tests
    if options.test:
        test_suite(options)
        return 0

    # Prepare input and output files
    if len(args) == 0:
        infile = sys.stdin
    elif len(args) == 1:
        infile = open(args[0], 'rb')
    else:
        parser.error("more than one input file")
    outfile = sys.stdout

    # Decode PNG to PPM
    if options.decode:
        reader = Reader()
        width, height, pixels = reader.read(infile)
        outfile.write('P6 %s %s 255\n' % (width, height))
        pixels.tofile(outfile)
        return 0

    # Encode PNM to PNG
    width, height = read_pnm_header(infile)
    writer = Writer(width, height,
                    transparent=options.transparent,
                    background=options.background,
                    has_alpha=options.alpha is not None,
                    gamma=options.gamma,
                    compression=options.compression)
    if options.alpha is not None:
        pgmfile = open(options.alpha, 'rb')
        if (width, height) != read_pnm_header(pgmfile, 'P5'):
            raise ValueError("alpha channel file has different size")
        writer.convert_ppm_and_pgm(infile, pgmfile, outfile,
                           interlace=options.interlace)
    else:
        writer.convert_ppm(infile, outfile,
                           interlace=options.interlace)


if __name__ == '__main__':
    _main()
