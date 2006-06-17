import sys, png

width, height, pixels = png.read(sys.stdin)
print 'P6 %s %s 255' % (width, height)
pixels.tofile(sys.stdout)
