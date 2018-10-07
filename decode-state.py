#!/usr/bin/env python3

import sys
import struct

from PIL import Image, ImageDraw

import Texture
import VertexProgram

import helper

import nv_tiles

def load_out(path, suffix):
  full_path = path + "_" + suffix
  try:
    return open(full_path, "rb").read()
  except FileNotFoundError:
    print("Failed to load '%s'" % full_path)
    return None

def read_nv2a_mem_word(accessor, offset):
  assert((offset & 0xFF000000) == 0)
  section = (offset >> 16) & 0xFF
  offset &= 0xFFFF
  if section == 0x10:
    storage = accessor[1] # PFB
  elif section == 0x40:
    storage = accessor[2] # PGRAPH
  else:
    assert(False)
  return struct.unpack_from("<L", storage, offset)[0]

def read_nv2a_pgraph_rdi_word(accessor, offset):
  assert((offset & 0xFF000000) == 0)
  section = (offset >> 16) & 0xFF
  offset &= 0xFFFF
  if section == 0x10:
    storage = accessor[1] # vp-instructions
  elif section == 0x17:
    storage = accessor[2] # vp-constants0
  elif section == 0xCC:
    storage = accessor[3] # vp-constants1
  else:
    assert(False)
  return struct.unpack_from("<L", storage, offset)[0]

def read_word(accessor, offset):
  return accessor[0](accessor, offset)

def decode_float(word):
  return struct.unpack("<f", struct.pack("<L", word))[0]

path = sys.argv[1]

mem_color = load_out(path, "mem-2.bin")
mem_depth = load_out(path, "mem-3.bin")
pgraph = load_out(path, "pgraph.bin")
pfb = load_out(path, "pfb.bin")
pgraph_rdi_vp_instructions = load_out(path, "pgraph-rdi-vp-instructions.bin")
pgraph_rdi_vp_constants0 = load_out(path, "pgraph-rdi-vp-constants0.bin")
pgraph_rdi_vp_constants1 = load_out(path, "pgraph-rdi-vp-constants1.bin")

nv2a_mem = (read_nv2a_mem_word, pfb, pgraph)
nv2a_pgraph_rdi = (read_nv2a_pgraph_rdi_word, pgraph_rdi_vp_instructions, pgraph_rdi_vp_constants0, pgraph_rdi_vp_constants1)


def align_up(v, alignment):
  return v + (alignment - (v % alignment)) % alignment


print("\nSubchannels:")
for i in range(8):
  grclass = read_word(nv2a_mem, 0x400160 + i * 4) & 0xFF
  print("[%d] Graphics class: 0x%02X" % (i, grclass))
print("")

# Dump pipeline
if True:
  csv0_d = read_word(nv2a_mem, 0x400FB4)

  pipeline = (csv0_d >> 30) & 0x3
  pipelines_str = ("Fixed-Function", "<unknown:1>", "Program")
  print("\nVertex Pipeline: %s" % (pipelines_str[pipeline]))

  if pipeline == 0:
    print("<Fixed-Function configuration>")
  elif pipeline == 2:
    print("<Program>") # FIXME: Disassemble the program here

    print("Constants:")
    for i in range(0, 192):
      v = []
      for j in range(4):
        # Mirror at 0xCC0000 ?
        v += [read_word(nv2a_pgraph_rdi, 0x170000 + i * 16 + j * 4)]
      print("c[%d]: 0x%08X 0x%08X 0x%08X 0x%08X (%15f, %15f, %15f, %15f)" % (i - 96,
            v[0], v[1], v[2], v[3],
            decode_float(v[0]), decode_float(v[1]), decode_float(v[2]), decode_float(v[3])))

    print("Instructions:")
    csv0_c = read_word(nv2a_mem, 0x400FB8)
    program_start = (csv0_c >> 8) & 0xFF

    program_offset = program_start
    for program_offset in range(program_offset, 136):
      instruction = []
      for i in range(4):
        instruction += [read_word(nv2a_pgraph_rdi, 0x100000 + program_offset * 16 + i * 4)]
      


      instructions = VertexProgram.get_instruction(instruction)
      print("0x%02X: 0x%08X 0x%08X 0x%08X 0x%08X %s" % (program_offset,
            instruction[0], instruction[1], instruction[2], instruction[3],
            instructions[0]))
      for instruction_str in instructions[1:]:
        print("                                                  %s" % (instruction_str))

      # Break if this was the final instruction
      #FIXME: What if there is no marker at the last program word?
      #       We should be able to see such problems in the output
      if instruction[0] & 0x00000001:
        break

  else:
    assert(False)


  print("\nFog-gen:")

  fog_mode = (csv0_d >> 21) & 1
  fog_modes_str = ('LINEAR', 'EXP')
  print("Mode: %s" % (fog_modes_str[fog_mode]))

  fog_genmode = (csv0_d >> 22) & 0x7
  fog_genmodes_str = ('SPEC_ALPHA', 'RADIAL', 'PLANAR', 'ABS_PLANAR', 'FOG_X')
  print("Gen-Mode: %s" % (fog_genmodes_str[fog_genmode]))

  fog_enable = (csv0_d >> 19) & 1
  print("Fog-Enable: %s" % (str(fog_enable)))

  print("")


print("\nRegister combiners:")

#FIXME: PArse this completly
combinectl = read_word(nv2a_mem, 0x401940)
stage_count = combinectl & 0xF
mux_bit = (combinectl >> 8) & 1
unique_cf0 = (combinectl >> 12) & 1
unique_cf1 = (combinectl >> 16) & 1

mux_bit_str = "MSB" if mux_bit else "LSB"

regs = tuple('r%d' % x for x in range(16))

#FIXME: Possibly bad order!
input_regs = ('ZERO',
'CONSTANT_COLOR0_NV',
'CONSTANT_COLOR1_NV',
'FOG',
'PRIMARY_COLOR_NV',
'SECONDARY_COLOR_NV',
'<invalid:6>',
'<invalid:7>',
'TEXTURE0_ARB',
'TEXTURE1_ARB',
'TEXTURE2_ARB',
'TEXTURE3_ARB',
'SPARE0_NV',
'SPARE1_NV',
'<invalid:14>',
'<invalid:15>')

output_regs = ('DISCARD_NV',
'<invalid:1>'
'<invalid:2>'
'<invalid:3>'
'PRIMARY_COLOR_NV',
'SECONDARY_COLOR_NV',
'<invalid:6>',
'<invalid:7>',
'TEXTURE0_ARB',
'TEXTURE1_ARB',
'TEXTURE2_ARB',
'TEXTURE3_ARB',
'SPARE0_NV',
'SPARE1_NV',
'<invalid:14>',
'<invalid:15>')

mappings = ('UNSIGNED_IDENTITY',
            'UNSIGNED_INVERT',
            'EXPAND_NORMAL',
            'EXPAND_NEGATE',
            'HALFBIAS_NORMAL',
            'HALFBIAS_NEGATE',
            'SIGNED_IDENTITY',
            'SIGNED_NEGATE')

mappings_code = ('max(0, %s)',
                 '(1 - clamp(%s, 0, 1))',
                 '(2 * max(0, %s) - 1)',
                 '(-2 * max(0, %s) + 1)',
                 '(max(0, %s) - 0.5)',
                 '(-max(0, %s) + 0.5)',
                 '%s',
                 '-%s')

def decode_in_reg(word, shift, is_alpha = False):
  v = word >> shift
  mapping = (v >> 5) & 0x7
  alpha = (v >> 4) & 1
  source = (v >> 0) & 0xF

  #FIXME: Only allowed in final combiner!
  assert(source != 0xE) # SPARE0_PLUS_SECONDARY_COLOR_NV
  assert(source != 0xF) # E_TIMES_F_NV

  s = regs[source]

  #FIXME: This might be wrong?
  if not is_alpha:
    s += ".aaa" if alpha else ".rgb"
  else:
    assert(source != 3) # FIXME: This is supposed to look for FOG
    s += ".a" if alpha else ".b"
  return mappings_code[mapping] % s

def decode_register_combiner_stage(stage, is_alpha):


  if not is_alpha:
    combine_input = read_word(nv2a_mem, 0x401900 + stage * 4)
  else:
    combine_input = read_word(nv2a_mem, 0x4018C0 + stage * 4)

  a = decode_in_reg(combine_input, 24, is_alpha)
  b = decode_in_reg(combine_input, 16, is_alpha)
  c = decode_in_reg(combine_input, 8, is_alpha)
  d = decode_in_reg(combine_input, 0, is_alpha)

  if not is_alpha:
    combine_output = read_word(nv2a_mem, 0x401920 + stage * 4)

    #FIXME: Support these!
    b_to_a_ab = (combine_output >> 19) & 1
    b_to_a_cd = (combine_output >> 18) & 1
  else:
    combine_output = read_word(nv2a_mem, 0x4018E0 + stage * 4)
    b_to_a_ab = False
    b_to_a_cd = False

  op = (combine_output >> 15) & 7
  ops = ('NOSHIFT',
         'NOSHIFT_BIAS',
         'SHIFTLEFTBY1',
         'SHIFTLEFTBY1_BIAS',
         'SHIFTLEFTBY2',
         'SHIFTRIGHTBY1')
  ops_code = ('%s',
              '(%s - 0.5)',
              '(%s * 2)',
              '((%s - 0.5) * 2)',
              '(%s * 4)',
              '(%s / 2)')
  mux_enable = (combine_output >> 14) & 1
  ab_dot_enable = (combine_output >> 13) & 1
  cd_dot_enable = (combine_output >> 12) & 1
  sum_dst = (combine_output >> 8) & 0xF
  ab_dst = (combine_output >> 4) & 0xF
  cd_dst = (combine_output >> 0) & 0xF

  op_code = ops_code[op]

  def get_out(is_dot_product, gcc_x, gcc_y, gcc_z):

    if not is_alpha:

      if is_dot_product == False:
        res_str = op_code % gcc_x
      else:
        res_str = op_code % gcc_y

    else:

      if is_dot_product == False:
        res_str = op_code % gcc_z
      else:
        res_str = "<invalid>" # FIXME: Assert?
        assert(False)

    return res_str

  # "gcc" stands for general combiner computation.

  if not is_alpha:
    gcc1 = "%s * %s" % (a, b)
    gcc2 = "vec3(dot(%s, %s))" % (a, b)
    gcc3 = "%s * %s" % (c, d)
    gcc4 = "vec3(dot(%s, %s))" % (c, d)
    gcc5 = "%s + %s" % (gcc1, gcc3)
    gcc6 = "mix(%s, %s, SPARE0_NV.a & %s)" % (gcc3, gcc1, mux_bit_str)
  else:
    gcc1 = "%s * %s" % (a, b)
    gcc2 = "%s * %s" % (c, d)
    gcc3 = "%s + %s" % (gcc1, gcc2)
    gcc4 = "mix(%s, %s, SPARE0_NV.a & %s)" % (gcc2, gcc1, mux_bit_str)

  def get_sum_out(mux_enable):
    if not is_alpha:
      if mux_enable == False:
        rgb_str = op_code % gcc5
      else:
        rgb_str = op_code % gcc6
      return rgb_str
    else:
      if mux_enable == False:
        a_str = op_code % gcc3
      else:
        a_str = op_code % gcc4
      return a_str



  ab_out = regs[ab_dst]
  if not is_alpha:
    ab_out += ".rgb"
  else:
    ab_out += ".a  "
  ab_out += " = " + get_out(ab_dot_enable, gcc1, gcc2, gcc1)
  if b_to_a_ab:
    #FIXME: Will this still write RGB?
    ab_out += "; %s.a = %s.b" % (regs[ab_dst], regs[ab_dst])

  cd_out = regs[cd_dst]
  if not is_alpha:
    cd_out += ".rgb"
  else:
    cd_out += ".a  "
  cd_out += " = " + get_out(cd_dot_enable, gcc3, gcc4, gcc2)
  if b_to_a_cd:
    #FIXME: Will this still write RGB?
    cd_out += "; %s.a = %s.b" % (regs[cd_dst], regs[cd_dst])

  sum_out = regs[sum_dst]
  if not is_alpha:
    sum_out += ".rgb"
  else:
    sum_out += ".a  "
  sum_out += " = " + get_sum_out(mux_enable)

  return (ab_out, cd_out, sum_out) #FIXME

def decode_final_register_combiner():

  fc0 = read_word(nv2a_mem, 0x401944)
  a = decode_in_reg(fc0, 24)
  b = decode_in_reg(fc0, 16)
  c = decode_in_reg(fc0, 8)
  d = decode_in_reg(fc0, 0)
  fc1 = read_word(nv2a_mem, 0x401948)
  e = decode_in_reg(fc1, 24)
  f = decode_in_reg(fc1, 16)
  g = decode_in_reg(fc1, 8, is_alpha=True) # Alpha scalar

  #FIXME: add these to output!
  specular_clamp = (fc1 >> 7) & 1
  specular_add_invr5 = (fc1 >> 6) & 1
  specular_add_invr12 = (fc1 >> 5) & 1

  comment = "E: %s; F: %s; clamp: %d; invr5: %d; invr12: %d" % (e, f, specular_clamp, specular_add_invr5, specular_add_invr12)
  rgb_str = "mix(%s, %s, %s) + %s" % (c, b, a, d)
  a_str = "%s" % (g)

  return (comment, rgb_str, a_str)

print("- AB, CD and SUM run in parallel")
print("- Each result is clamped to [-1, +1]")

print("unique_cf0: %d" % unique_cf0) # FIXME: Integrate in code
print("unique_cf1: %d" % unique_cf1) # FIXME: Integrate in code
for i in range(8):
  if i >= stage_count:
    # FIXME: Still print it, but clearly mark it as disabled
    break
  rbg_str = decode_register_combiner_stage(i, is_alpha = False)
  a_str = decode_register_combiner_stage(i, is_alpha = True)

  def get_rgba(combinefactor):
    r = (combinefactor >> 16) & 0xFF
    g = (combinefactor >> 8) & 0xFF
    b = (combinefactor >> 0) & 0xFF
    a = (combinefactor >> 24) & 0xFF
    return (r, g, b, a)

  combinefactor0 = read_word(nv2a_mem, 0x401880 + 4 * i)
  combinefactor1 = read_word(nv2a_mem, 0x4018A0 + 4 * i)

  print("[%d] CF0.rgba = to_vec4(0x%02X, 0x%02X, 0x%02X, 0x%02X)" % (i, *get_rgba(combinefactor0)))
  print("    CF1.rgba = to_vec4(0x%02X, 0x%02X, 0x%02X, 0x%02X)" % (     get_rgba(combinefactor1)))
  print("    %s # AB" % (rbg_str[0]))
  print("    %s" %      (a_str[0]))
  print("    %s # CD" % (rbg_str[1]))
  print("    %s" %      (a_str[1]))
  print("    %s # SUM" % (rbg_str[2]))
  print("    %s" %       (a_str[2]))
final_combiner_str = decode_final_register_combiner()
print("[*] # %s" % (final_combiner_str[0]))
print("    CF0.rgba = to_vec4(...)") # FIXME: 0x004019AC
print("    CF1.rgba = to_vec4(...)") # FIXME: 0x004019B0
print("    output.rgb = %s" % (final_combiner_str[1]))
print("    output.a   = %s" % (final_combiner_str[2]))
print("")


if True:
  print("\nFog:")

  control_3 = read_word(nv2a_mem, 0x401958)

  fog_mode = (control_3 >> 16) & 0x7
  fog_modes_str = ('LINEAR', 'EXP', '<unknown:2>' 'EXP2', 'LINEAR_ABS', 'EXP_ABS', '<unknown:6>', 'EXP2_ABS')
  print("Mode: %s" % (fog_modes_str[fog_mode]))

  fog_enable = (control_3 >> 8) & 1
  print("Enable: %s" % str(fog_enable))

  fog_color = read_word(nv2a_mem, 0x401980)
  print("Color: 0x%08X" % (fog_color))

  fog_param0 = read_word(nv2a_mem, 0x401984)
  print("Parameter[0] (bias): 0x%08X (%f)" % (fog_param0, decode_float(fog_param0)))
  fog_param1 = read_word(nv2a_mem, 0x401988)
  print("Parameter[1] (scale): 0x%08X (%f)" % (fog_param1, decode_float(fog_param1)))

  print("")




print("\nTiles:")

# This configures how tiling works
cfg0 = read_word(nv2a_mem, 0x100200)
cfg1 = read_word(nv2a_mem, 0x100204)
mcc = nv_tiles.mc_config(cfg0, cfg1)

for i in range(8):

  # Also in PGRAPH 0x900?!
  tile = read_word(nv2a_mem, 0x100240 + 16 * i)
  valid = tile & 1
  bank_sense = tile & 2
  address = tile & 0xFFFFC000

  tlimit = read_word(nv2a_mem, 0x100244 + 16 * i)
  #FIXME: This is apparently 18+14 bits, much like address, but lower bits always set?
  assert((tlimit & 0x3FFF) == 0x3FFF)

  tsize = read_word(nv2a_mem, 0x100248 + 16 * i)
  pitch = tsize & 0xFFFF
  assert(pitch & 0xFF == 0x00)

  tstatus = read_word(nv2a_mem, 0x10024C + 16 * i)
  prime = (1, 3, 5, 7)[tstatus & 3]
  factor = 1 << ((tstatus >> 4) & 7)
  region_valid = tstatus & 0x80000000

  valid_str = "valid" if valid else "invalid"
  region_valid_str = "valid" if region_valid else "invalid"

  print("[%d] %s; bank sense %d; address 0x%08X, limit 0x%08X, pitch 0x%X, prime %d, factor %d, region %s" % (i, valid_str, bank_sense, address, tlimit, pitch, prime, factor, region_valid_str))

  fb_zcomp = read_word(nv2a_mem, 0x100300 + 4 * i)
  zcomp_enabled = fb_zcomp & 0x80000000

  pgraph_zcomp = read_word(nv2a_mem, 0x400980 + 4 * i)

  zcomp_enabled_str = "compressed" if zcomp_enabled else "uncompressed"

  print("    Z-compression: %s 0x%08X, 0x%08X" % (zcomp_enabled_str, fb_zcomp, pgraph_zcomp))

print("")


print("\nFramebuffers:")
for i in range(6):
  boffset = read_word(nv2a_mem, 0x400820 + 4 * i) & 0x3FFFFFFF
  bbase = read_word(nv2a_mem, 0x400838 + 4 * i) & 0x3FFFFFFF
  if i < 5:
    bpitch = read_word(nv2a_mem, 0x400850 + 4 * i) & 0xFFFF
    bpitch_str = "0x%08X" % bpitch
  else:
    bpitch_str = "----------"
  blimit = read_word(nv2a_mem, 0x400864 + 4 * i)
  blimit_addresss = blimit & 0x3FFFFFFF
  blimit_addressing = blimit & 0x40000000
  blimit_type = blimit & 0x80000000

  blimit_addressing_str = "tiled" if blimit_addressing else "linear"
  blimit_type_str = "in-memory" if blimit_type else "null"
  print("[%d] 0x%08X, 0x%08X, pitch: %s, blimit 0x%08X, %s, %s" % (i, boffset, bbase, bpitch_str, blimit_addresss, blimit_addressing_str, blimit_type_str))
print("")


bswizzle2 = read_word(nv2a_mem, 0x400818)
bswizzle2_ws = (bswizzle2 >> 16) & 0xF
bswizzle2_hs = (bswizzle2 >> 24) & 0xF
print("BSWIZZLE2: %d, %d" % (1 << bswizzle2_ws, 1 << bswizzle2_hs))

bswizzle5 = read_word(nv2a_mem, 0x40081c)
bswizzle5_ws = (bswizzle5 >> 16) & 0xF
bswizzle5_hs = (bswizzle5 >> 24) & 0xF
print("BSWIZZLE5: %d, %d" % (1 << bswizzle5_ws, 1 << bswizzle5_hs))


surface_type = read_word(nv2a_mem, 0x400710)
surface_addressing = surface_type & 3
surface_anti_aliasing = (surface_type >> 4) & 3

surface_type_str = ("invalid", "non-swizzled", "swizzled")[surface_addressing]
surface_anti_aliasing_str = ("center-1 [none]", "center-corner-2", "square-offset-4")[surface_anti_aliasing]

print("Surface type %s; anti-aliasing: %s" % (surface_type_str, surface_anti_aliasing_str))







surface_clip_x = read_word(nv2a_mem, 0x4019B4)
surface_clip_y = read_word(nv2a_mem, 0x4019B8)

clip_x = (surface_clip_x >> 0) & 0xFFFF
clip_y = (surface_clip_y >> 0) & 0xFFFF

clip_w = (surface_clip_x >> 16) & 0xFFFF
clip_h = (surface_clip_y >> 16) & 0xFFFF

clip_x, clip_y = helper.apply_anti_aliasing_factor(surface_anti_aliasing, clip_x, clip_y)
clip_w, clip_h = helper.apply_anti_aliasing_factor(surface_anti_aliasing, clip_w, clip_h)

width = clip_x + clip_w
height = clip_y + clip_h

color_pitch = read_word(nv2a_mem, 0x400858)
depth_pitch = read_word(nv2a_mem, 0x40085C)

draw_format = read_word(nv2a_mem, 0x400804)
format_color = (draw_format >> 12) & 0xF
format_depth = (draw_format >> 18) & 0x3
depth_float = (read_word(nv2a_mem, 0x401990) >> 29) & 1
depth_float_str = "float" if depth_float else "fixed"

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
