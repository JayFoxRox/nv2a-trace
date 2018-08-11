#!/usr/bin/env python3

import sys
import struct

from PIL import Image, ImageDraw

import Texture

import nv_tiles

def load_out(path, suffix):
  return open(path + "_" + suffix, "rb").read()

def read_word(storage, offset):
  return struct.unpack_from("<L", storage, offset)[0]

path = sys.argv[1]

mem_color = load_out(path, "mem-2.bin")
mem_depth = load_out(path, "mem-3.bin")
pgraph = load_out(path, "pgraph.bin")
pfb = load_out(path, "pfb.bin")


def align_up(v, alignment):
  return v + (alignment - (v % alignment)) % alignment

# This configures how tiling works
cfg0 = read_word(pfb, 0x200)
cfg1 = read_word(pfb, 0x204)
mcc = nv_tiles.mc_config(cfg0, cfg1)

print("\nTiles:")
for i in range(8):

  # Also in PGRAPH 0x900?!
  tile = read_word(pfb, 0x240 + 16 * i)
  valid = tile & 1
  bank_sense = tile & 2
  address = tile & 0xFFFFC000

  tlimit = read_word(pfb, 0x244 + 16 * i)
  #FIXME: This is apparently 18+14 bits, much like address, but lower bits always set?
  assert((tlimit & 0x3FFF) == 0x3FFF)

  tsize = read_word(pfb, 0x248 + 16 * i)
  pitch = tsize & 0xFFFF
  assert(pitch & 0xFF == 0x00)

  tstatus = read_word(pfb, 0x24C + 16 * i)
  prime = (1, 3, 5, 7)[tstatus & 3]
  factor = 1 << ((tstatus >> 4) & 7)
  region_valid = tstatus & 0x80000000

  valid_str = "valid" if valid else "invalid"
  region_valid_str = "valid" if region_valid else "invalid"

  print("[%d] %s; bank sense %d; address 0x%08X, limit 0x%08X, pitch 0x%X, prime %d, factor %d, region %s" % (i, valid_str, bank_sense, address, tlimit, pitch, prime, factor, region_valid_str))

  fb_zcomp = read_word(pfb, 0x300 + 4 * i)
  zcomp_enabled = fb_zcomp & 0x80000000

  pgraph_zcomp = read_word(pgraph, 0x980 + 4 * i)

  zcomp_enabled_str = "compressed" if zcomp_enabled else "uncompressed"
  
  print("     Z-compression: %s 0x%08X, 0x%08X" % (zcomp_enabled_str, fb_zcomp, pgraph_zcomp))

print("")


print("\nFramebuffers:")
for i in range(6):
  boffset = read_word(pgraph, 0x820 + 4 * i) & 0x3FFFFFFF
  bbase = read_word(pgraph, 0x838 + 4 * i) & 0x3FFFFFFF
  if i < 5:
    bpitch = read_word(pgraph, 0x850 + 4 * i) & 0xFFFF
    bpitch_str = "0x%08X" % bpitch
  else:
    bpitch_str = "----------"
  blimit = read_word(pgraph, 0x864 + 4 * i)
  blimit_addresss = blimit & 0x3FFFFFFF
  blimit_addressing = blimit & 0x40000000
  blimit_type = blimit & 0x80000000

  blimit_addressing_str = "tiled" if blimit_addressing else "linear"
  blimit_type_str = "in-memory" if blimit_type else "null"
  print("[%d] 0x%08X; 0x%08X; pitch: %s; blimit: 0x%08X, %s; %s" % (i, boffset, bbase, bpitch_str, blimit_addresss, blimit_addressing_str, blimit_type_str))
print("")


bswizzle2 = read_word(pgraph, 0x818)
bswizzle2_ws = (bswizzle2 >> 16) & 0xF
bswizzle2_hs = (bswizzle2 >> 24) & 0xF
print("BSWIZZLE2: %d, %d" % (1 << bswizzle2_ws, 1 << bswizzle2_hs))

bswizzle5 = read_word(pgraph, 0x81c)
bswizzle5_ws = (bswizzle5 >> 16) & 0xF
bswizzle5_hs = (bswizzle5 >> 24) & 0xF
print("BSWIZZLE5: %d, %d" % (1 << bswizzle5_ws, 1 << bswizzle5_hs))


surface = read_word(pgraph, 0x710)
surface_type = surface & 3
surface_anti_aliasing = (surface >> 4) & 3

surface_type_str = ("invalid", "non-swizzled", "swizzled")[surface_type]
surface_anti_aliasing_str = ("center-1 [none]", "center-corner-2", "square-offset-4")[surface_anti_aliasing]

print("Surface type %s; anti-aliasing: %s" % (surface_type_str, surface_anti_aliasing_str))







surface_clip_x = read_word(pgraph, 0x19B4)
surface_clip_y = read_word(pgraph, 0x19B8)

clip_x = (surface_clip_x >> 0) & 0xFFFF
clip_y = (surface_clip_y >> 0) & 0xFFFF

clip_w = (surface_clip_x >> 16) & 0xFFFF
clip_h = (surface_clip_y >> 16) & 0xFFFF

width = clip_x + clip_w
height = clip_y + clip_h

pitch = read_word(pgraph, 0x858)

surface_format = read_word(pgraph, 0x804)
format_color = (surface_format >> 12) & 0xF
format_depth = (surface_format >> 18) & 0x3
depth_float = (read_word(pgraph, 0x1990) >> 29) & 1
depth_float_str = "float" if depth_float else "fixed"

print("Clip is at %d x %d + %d, %d" % (clip_w, clip_h, clip_x, clip_y))
print("Assuming surface size is %d x %d (pitch %d)" % (width, height, pitch))
print("Surface format color: 0x%X depth: 0x%X (%s) %s" % (format_color, format_depth, ('invalid','Z16','Z24S8')[format_depth], depth_float_str))

# Requirement for the tiling stuff?
#FIXME: Why tho?
height = align_up(height, 16)

bpp = int(sys.argv[2])


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


def untile(data, lookup, bpp):
  bytes_per_pixel = bpp // 8
  new_data = bytearray(data)
  for i in lookup:
    for j in range(bytes_per_pixel):
      new_data[i * bytes_per_pixel + j] = data[lookup[i] * bytes_per_pixel + j]
  return new_data




if False:
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

  mem_untiled = untile(mem_color, hack, 32)
  img = Texture.decodeTexture(mem_untiled, (640, 480), 2560, False, 32, (8,8,8), (16,8,0))
  img.save("untiled-hack.png")

  


# These are assumptions, need to look at envytools to confirm
chipset = 0x2A
bankoff = 0

# This does not matter
mode = 0


bytes_per_pixel = bpp // 8

tile_lookup = []
for i in range(pitch * height // bytes_per_pixel):
  tile_lookup += [nv_tiles.tile_translate_addr(chipset, pitch, i * bytes_per_pixel, mode, bankoff, mcc)[2] // bytes_per_pixel]




assert(height % 16 == 0)

mem_untiled = untile(mem_color, tile_lookup, bpp)
img = Texture.decodeTexture(mem_untiled, (width, height), pitch, False, bpp, (8,8,8), (16,8,0))
img.save("untiled-tiles-color.png")

ImageDraw.Draw(img).rectangle([clip_x - 1, clip_y - 1, clip_x + clip_w + 1, clip_y + clip_h + 1], fill=None, outline=(255, 0, 0))
img.save("untiled-tiles-color-surface_clip.png")



mem_untiled = untile(mem_depth, tile_lookup, bpp)
img = Texture.decodeTexture(mem_untiled, (width, height), pitch, False, bpp, (8,0,0), (8,16,24))
img.save("untiled-tiles-depth.png")



if False:
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
