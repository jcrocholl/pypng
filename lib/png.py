#!/usr/bin/env python
# Copyright (C) 2006 Johann C. Rocholl <johann@browsershots.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Write PNG files in pure Python.
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

# http://www.w3.org/TR/PNG/#8InterlaceMethods
adam7 = ((0, 0, 8, 8),
         (4, 0, 8, 8),
         (0, 4, 4, 8),
         (2, 0, 4, 4),
         (0, 2, 2, 4),
         (1, 0, 2, 2),
         (0, 1, 1, 2))

def scanlines_interlace(width, height, pixels, scheme = adam7):
    """
    Interlace and insert a filter type marker byte before every scanline.
    """
    result = []
    scanline = 3*width
    for xstart, ystart, xstep, ystep in scheme:
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

def write(outfile, width, height, pixels, interlace = False, transparent = None):
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
    write_chunk(outfile, 'IHDR', struct.pack("!2I5B", width, height, 8, 2, 0, 0, interlace))
    # http://www.w3.org/TR/PNG/#11tRNS
    if transparent is not None:
        transparent = struct.pack("!3H", ord(transparent[0]), ord(transparent[1]), ord(transparent[2]))
        write_chunk(outfile, 'tRNS', transparent)
    # http://www.w3.org/TR/PNG/#11IDAT
    write_chunk(outfile, 'IDAT', zlib.compress(data))
    # http://www.w3.org/TR/PNG/#11IEND
    write_chunk(outfile, 'IEND', '')

if __name__ == '__main__':
    import os
    from optparse import OptionParser
    parser = OptionParser()
    parser.set_usage("%prog [options] [ppmfile]")
    parser.set_defaults(interlace=False, transparent=None)
    parser.add_option("--interlace", action="store_true",
                      help="create an interlaced PNG file (Adam7)")
    parser.add_option("--transparent", action="store", type="string",
                      metavar="color",
                      help="mark the specified color as transparent")
    parser.add_option("--background", action="store", type="string",
                      metavar="color",
                      help="store the specified background color")
    parser.add_option("--gamma", action="store", type="float",
                      metavar="value",
                      help="store the specified gamma value")
    parser.add_option("--alpha", action="store", type="string",
                      metavar="pgmfile",
                      help="alpha channel transparency (RGBA)")
    (options, args) = parser.parse_args()
    print options
    print args
