import sys

from PIL import Image, ImageDraw

import helper
import Texture

def dump(state):
  print("\nFramebuffers:")

  def align_up(v, alignment):
    return v + (alignment - (v % alignment)) % alignment

  for i in range(6):
    boffset = state.read_nv2a_device_memory_word(0x400820 + 4 * i) & 0x3FFFFFFF
    bbase = state.read_nv2a_device_memory_word(0x400838 + 4 * i) & 0x3FFFFFFF
    if i < 5:
      bpitch = state.read_nv2a_device_memory_word(0x400850 + 4 * i) & 0xFFFF
      bpitch_str = "0x%08X" % bpitch
    else:
      bpitch_str = "----------"
    blimit = state.read_nv2a_device_memory_word(0x400864 + 4 * i)
    blimit_addresss = blimit & 0x3FFFFFFF
    blimit_addressing = blimit & 0x40000000
    blimit_type = blimit & 0x80000000

    blimit_addressing_str = "tiled" if blimit_addressing else "linear"
    blimit_type_str = "in-memory" if blimit_type else "null"
    print("[%d] 0x%08X; 0x%08X; pitch: %s; blimit: 0x%08X, %s; %s" % (i, boffset, bbase, bpitch_str, blimit_addresss, blimit_addressing_str, blimit_type_str))
  print("")


  bswizzle2 = state.read_nv2a_device_memory_word(0x400818)
  bswizzle2_ws = (bswizzle2 >> 16) & 0xF
  bswizzle2_hs = (bswizzle2 >> 24) & 0xF
  print("BSWIZZLE2: %d, %d" % (1 << bswizzle2_ws, 1 << bswizzle2_hs))

  bswizzle5 = state.read_nv2a_device_memory_word(0x40081c)
  bswizzle5_ws = (bswizzle5 >> 16) & 0xF
  bswizzle5_hs = (bswizzle5 >> 24) & 0xF
  print("BSWIZZLE5: %d, %d" % (1 << bswizzle5_ws, 1 << bswizzle5_hs))


  surface_type = state.read_nv2a_device_memory_word(0x400710)
  surface_addressing = surface_type & 3
  surface_anti_aliasing = (surface_type >> 4) & 3

  surface_type_str = ("invalid", "non-swizzled", "swizzled")[surface_addressing]
  surface_anti_aliasing_str = ("center-1 [none]", "center-corner-2", "square-offset-4")[surface_anti_aliasing]

  print("Surface type %s; anti-aliasing: %s" % (surface_type_str, surface_anti_aliasing_str))







  surface_clip_x = state.read_nv2a_device_memory_word(0x4019B4)
  surface_clip_y = state.read_nv2a_device_memory_word(0x4019B8)

  clip_x = (surface_clip_x >> 0) & 0xFFFF
  clip_y = (surface_clip_y >> 0) & 0xFFFF

  clip_w = (surface_clip_x >> 16) & 0xFFFF
  clip_h = (surface_clip_y >> 16) & 0xFFFF

  clip_x, clip_y = helper.apply_anti_aliasing_factor(surface_anti_aliasing, clip_x, clip_y)
  clip_w, clip_h = helper.apply_anti_aliasing_factor(surface_anti_aliasing, clip_w, clip_h)

  width = clip_x + clip_w
  height = clip_y + clip_h

  color_pitch = state.read_nv2a_device_memory_word(0x400858)
  depth_pitch = state.read_nv2a_device_memory_word(0x40085C)

  draw_format = state.read_nv2a_device_memory_word(0x400804)
  format_color = (draw_format >> 12) & 0xF
  format_depth = (draw_format >> 18) & 0x3
  depth_float = (state.read_nv2a_device_memory_word(0x401990) >> 29) & 1
  depth_float_str = "float" if depth_float else "fixed"

  #FIXME: Load from texture formats instead?
  #       surface_color_format_to_texture_format
  #       surface_zeta_format_to_texture_format
  color_formats = ('invalid',
                   'Y8',
                   'X1R5G5B5_Z1R5G5B5',
                   'X1R5G5B5_O1R5G5B5',
                   'A1R5G5B5',
                   'R5G6B5',
                   'Y16',
                   'X8R8G8B8_Z8R8G8B8',
                   'X8R8G8B8_O1Z7R8G8B8',
                   'X1A7R8G8B8_Z1A7R8G8B8',
                   'X1A7R8G8B8_O1A7R8G8B8',
                   'X8R8G8B8_O8R8G8B8',
                   'A8R8G8B8',
                   'Y32',
                   'V8YB8U8YA8',
                   'YB8V8YA8U8')
  depth_formats = ('invalid','Z16','Z24S8')

  print("Clip is at %d x %d + %d, %d" % (clip_w, clip_h, clip_x, clip_y))
  print("Assuming surface size is %d x %d (color pitch %d; depth pitch %d)" % (width, height, color_pitch, depth_pitch))
  print("Surface format color: 0x%X (%s), depth: 0x%X (%s) %s" % (format_color, color_formats[format_color], format_depth, depth_formats[format_depth], depth_float_str))

  # Requirement for the tiling stuff?
  #FIXME: Why tho?
  height = align_up(height, 16)

  bpp = int(sys.argv[2])




  def untile(data, lookup, bpp):
    bytes_per_pixel = bpp // 8
    new_data = bytearray(data)
    for i in lookup:
      for j in range(bytes_per_pixel):
        new_data[i * bytes_per_pixel + j] = data[lookup[i] * bytes_per_pixel + j]
    return new_data





  # These are assumptions, need to look at envytools to confirm
  chipset = 0x2A
  bankoff = 0

  # This does not matter
  mode = 0


  bytes_per_pixel = bpp // 8

  if False:
    color_tile_lookup = []
    for i in range(pitch * height // bytes_per_pixel):
      color_tile_lookup += [nv_tiles.tile_translate_addr(chipset, color_pitch, i * bytes_per_pixel, mode, bankoff, mcc)[2] // bytes_per_pixel]

    depth_tile_lookup = []
    for i in range(pitch * height // bytes_per_pixel):
      depth_tile_lookup += [nv_tiles.tile_translate_addr(chipset, depth_pitch, i * bytes_per_pixel, mode, bankoff, mcc)[2] // bytes_per_pixel]



  assert(height % 16 == 0)



  color_offset = state.read_nv2a_device_memory_word(0x400828)
  depth_offset = state.read_nv2a_device_memory_word(0x40082C)
  color_base = state.read_nv2a_device_memory_word(0x400840)
  depth_base = state.read_nv2a_device_memory_word(0x400844)
  mem_color = state.read_memory(color_base + color_offset, color_pitch * height)
  mem_depth = state.read_memory(depth_base + depth_offset, depth_pitch * height)

  if mem_color:
    mem_untiled = mem_color #untile(mem_color, color_tile_lookup, bpp)
    img = Texture.decodeTexture(mem_untiled, (width, height), color_pitch, False, bpp, (8,8,8), (16,8,0))
    img.save("untiled-tiles-color.png")

    ImageDraw.Draw(img).rectangle([clip_x - 1, clip_y - 1, clip_x + clip_w + 1, clip_y + clip_h + 1], fill=None, outline=(255, 0, 0))
    img.save("untiled-tiles-color-surface_clip.png")


  if mem_depth:
    mem_untiled = mem_depth #untile(mem_depth, depth_tile_lookup, bpp)
    img = Texture.decodeTexture(mem_untiled, (width, height), depth_pitch, False, bpp, (8,8,8), (24,24,24))
    img.save("untiled-tiles-depth.png")

    mem_untiled = mem_depth #untile(mem_depth, depth_tile_lookup, bpp)
    img = Texture.decodeTexture(mem_untiled, (width, height), depth_pitch, False, bpp, (8,8,8), (0,0,0))
    img.save("untiled-tiles-stencil.png")
