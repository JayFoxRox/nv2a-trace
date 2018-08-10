#!/usr/bin/env python3

import sys
import struct

from PIL import Image

import Texture

import nv_tiles

def load_out(path, suffix):
  return open(path + "_" + suffix, "rb").read()

#FIXME: Unswizzle texture in some forms..

#FIXME: Load PGRAPH state
#FIXME: Load pixel data

#FIXME: decode texture swizzled / unswizzled, rounded dimensions / clean dimensions

path = sys.argv[1]

mem = load_out(path, "mem.bin")
pgraph = load_out(path, "pgraph.bin")

bpp = int(sys.argv[2])
width = int(sys.argv[3])
height = int(sys.argv[4])
pitch = int(sys.argv[5])

if True:

  print(mem[1])

  print("SWI")
  swizzled = list(range(0, 640*480))

  def img_to_words(img):
    words = []
    for y in range(0, img.size[1]):
      for x in range(0, img.size[0]):
        r,g,b,a = img.getpixel((x,y))
        words += [(r << 0) | (g << 8) | (b << 16) | (a << 24)]
    return words

  swizzled_bytes = struct.pack("<" + "L" * len(swizzled), *swizzled)

  print("HCK")
  img = Texture.decodeTexture(swizzled_bytes, (640, 480), 2560, True, 32, (8,8,8,8), (0,8,16,24))
  hack = img_to_words(img)

  print("GEN")
  generated = []
  for v in range(0, 8):


    for u in range(0, 4):
      for z in range(0, 640 // 64):
        for y in range(0, 4):
          for x1 in range(0, 2):
            for x2 in range(0, 8):
              in_block = z * 1024 + y * 64 + (x1 * 8 + x2)

              generated += [v * 264 + u * 16 + in_block]


  def untile(data, lookup, bpp):
    bytes_per_pixel = bpp // 8
    new_data = bytearray(data)
    for i in lookup:
      for j in range(bytes_per_pixel):
        new_data[i * bytes_per_pixel + j] = data[lookup[i] * bytes_per_pixel + j]
    return new_data
    



  chipset = 0x2A
  pitch = 2560

  #FIXME: Where to get these from? - probably NV_PFB_CFG0 / NV_PFB_CFG1 ?
  mode = 1
  bankoff = 0
  mcc = nv_tiles.mc_config()
  mcc.mcbits = 2
  mcc.partbits = 2
  mcc.colbits_lo = 2
  mcc.burstbits = 0

  bytes_per_pixel = bpp // 8

  tile_lookup = []
  for i in range(pitch * height // bytes_per_pixel):
    tile_lookup += [nv_tiles.tile_translate_addr(chipset, pitch, i * bytes_per_pixel, mode, bankoff, mcc)[2] // bytes_per_pixel]


  mem_untiled = untile(mem, hack, 32)
  img = Texture.decodeTexture(mem_untiled, (640, 480), 2560, False, 32, (8,8,8), (16,8,0))
  img.save("untiled-hack.png")

  assert(height % 16 == 0)

  mem_untiled = untile(mem, tile_lookup, bpp)
  img = Texture.decodeTexture(mem_untiled, (width, height), pitch, False, bpp, (8,8,8), (16,8,0))
  img.save("untiled-tiles.png")

  print("---")

  print("SWI: \n%s\n" % str(swizzled[0:100]))
  print("HCK: \n%s\n" % str(hack[0:100]))
  print("GEN: \n%s\n" % str(generated[0:100]))

  try:
    for x in range(len(hack)):
      print("%d: %d == %d ?" % (x, hack[x], generated[x]))
      assert(hack[x] == generated[x])
  except:
    print("FAIL!")
    pass

if True:

  block_w = 64
  block_h = 16

  block_p = block_w*4

  block_l = block_p*block_h

  block_cx = 640 // block_w
  block_cy = 480 // block_h

  til = Image.new("RGB",(640,480))

  for y in range(0, block_cy):
    for x in range(0, block_cx):
      img = Texture.decodeTexture(mem[block_l*block_cx*y+block_l*x:], (block_w, block_h), 2560<<13, False, 32, (8,8,8), (16,8,0), disable_hack = True)
      til.paste(img, (x * block_w, y * block_h))

    til.save("test.png")






