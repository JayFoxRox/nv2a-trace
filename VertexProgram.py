# A very basic vertex program disassembler.

#FIXME: Code like: dp3 r3.x, r2.xyzz, c[-89].xyzz
#       should be: dp3 r3.x, r2, c[-89]
#       because dp3 only cares about 3 components, and those are unswizzled

#FIXME: Code like: mul r2.xyz, r2.xyzz, r1.x
#       should be: mul r2.xyz, r2, r1.x
#       because the writeback only cares about xyz, and those are unswizzled
#       Note that code like: mul r2.yzw, r2.xyzz, r1.x
#       must still be:       mul r2.yzw, r2.yzz, r1.x
#       Also code like:      mul r2.yzw, r2.xxyz, r1.x
#       should be:           mul r2.yzw, r2.xyz, r1.x
#       And code like:       mul r2.yzw, r2.xyzw, r1.x
#       should also be:      mul r2.yzw, r2.yzw, r1.x

mac_operations = (
  ('nop', False, False, False), # 0x0
  ('mov', True,  False, False), # 0x1
  ('mul', True,  True,  False), # 0x2
  ('add', True,  False, True),  # 0x3
  ('mad', True,  True,  True),  # 0x4
  ('dp3', True,  True,  False), # 0x5
  ('dph', True,  True,  False), # 0x6
  ('dp4', True,  True,  False), # 0x7
  ('dst', True,  True,  False), # 0x8
  ('min', True,  True,  False), # 0x9
  ('max', True,  True,  False), # 0xA
  ('slt', True,  True,  False), # 0xB
  ('sge', True,  True,  False), # 0xC
  ('arl', True,  False, False)  # 0xD
)

ilu_operations = (
  'nop', # 0x0
  'mov', # 0x1
  'rcp', # 0x2
  'rcc', # 0x3
  'rsq', # 0x4
  'exp', # 0x5
  'log', # 0x6
  'lit', # 0x7
)

output_o_registers = (
  'oPos', # 0x0
  None,   # 0x1
  None,   # 0x2
  'oD0',  # 0x3
  'oD1',  # 0x4
  'oFog', # 0x5
  'oPts', # 0x6
  'oB0',  # 0x7
  'oB1',  # 0x8
  'oT0',  # 0x9
  'oT1',  # 0xA
  'oT2',  # 0xB
  'oT3',  # 0xC
)

def get_write_mask(mask):
  c = "xyzw"
  assert(mask != 0x0)
  if mask == 0xF: return '' # Same as .xyzw
  mask_str = '.'
  for i in range(4):
    if (mask >> (3 - i)) & 1: mask_str += c[i]
  return mask_str

def get_output_o_register(index, mask):
  if index & 0x100:
    register_str = output_o_registers[index & 0xFF]
  else:
    register_str = "c[%d]" % ((index & 0xFF) - 96)
  register_str += get_write_mask(mask)
  return register_str 

def get_swizzle_mask(mask):
  c = "xyzw"
  x = (mask >> 6) & 0x3
  y = (mask >> 4) & 0x3
  z = (mask >> 2) & 0x3
  w = (mask >> 0) & 0x3
  if x == 0 and y == 1 and z == 2 and w == 3: # xyzw
    return ""
  if x == y and x == z and x == w: # xxxx, yyyy, zzzz, wwww
    return "." + c[x]
  return "." + c[x] + c[y] + c[z] + c[w]

def get_input_register(v, c_is_relative, c_index, v_index):

  source = (v >> 0) & 0x3
  r_index = (v >> 2) & 0xF
  mask = (v >> 6) & 0xFF
  negate = (v >> 14) & 1

  register_str = "-" if negate else ""
  if source == 1: # Register
    register_str += "r%d" % r_index
  elif source == 2: # Vertex attribute
    register_str += "v%d" % v_index
  elif source == 3: # Constant
    # FIXME: Do 'a0 - 40' instead of 'a0 + -40'?
    index = "a0 + " if c_is_relative else ""
    index +=  "%d" % (c_index - 96)
    register_str += "c[%s]" % index
  register_str += get_swizzle_mask(mask)
  return register_str

def get_instruction(instruction):

  c_is_relative = (instruction[0] >> 1) & 1
  output_o_from_ilu = (instruction[0] >> 2) & 1
  output_o_index = (instruction[0] >> 3) & 0x1FF
  output_o_mask = (instruction[0] >> 12) & 0xF
  output_r_mask_ilu = (instruction[0] >> 16) & 0xF
  output_r_index = (instruction[0] >> 20) & 0xF
  output_r_mask_mac = (instruction[0] >> 24) & 0xF
  clo = (instruction[0] >> 28) & 0xF

  chi = (instruction[1] >> 0) & 0x3FF
  b = (instruction[1] >> 11) & 0x7FFF
  alo = (instruction[1] >> 26) & 0x3F

  ahi = (instruction[2] >> 0) & 0x1FF
  v_index = (instruction[2] >> 9) & 0xF
  c_index = (instruction[2] >> 13) & 0xFF
  mac = (instruction[2] >> 21) & 0xF
  ilu = (instruction[2] >> 25) & 0x7F

  c = (chi << 4) | clo
  a = (ahi << 6) | alo

  operations = []

  # We also check for ILU, so at least one of them generates a nop
  if mac != 0x00 or ilu == 0x00:
    mac_operation = mac_operations[mac]

    mac_str = mac_operation[0] + ' '

    has_o_output = output_o_mask and not output_o_from_ilu
    two_destinations = has_o_output and output_r_mask_mac

    if two_destinations:
      mac_str += "{ "

    if mac == 0xD: # Check for ARL output
      assert(has_o_output == False) #FIXME: What would happen here?
      assert(output_r_mask_mac == 0x0) #FIXME: What would happen here?
      mac_str += "a0.x"
    elif has_o_output:
      mac_str += get_output_o_register(output_o_index, output_o_mask)

    if two_destinations:
      mac_str += ", "

    if output_r_mask_mac:
      mac_str += "r%d%s" % (output_r_index, get_write_mask(output_r_mask_mac))

    if two_destinations:
      mac_str += " }"

    if mac_operation[1]:
      mac_str += ", " + get_input_register(a, c_is_relative, c_index, v_index)
    if mac_operation[2]:
      mac_str += ", " + get_input_register(b, c_is_relative, c_index, v_index)
    if mac_operation[3]:
      mac_str += ", " + get_input_register(c, c_is_relative, c_index, v_index)

    operations += [mac_str]

  if ilu != 0x00:
    ilu_str = ilu_operations[ilu] + ' '

    has_o_output = output_o_mask and output_o_from_ilu
    two_destinations = has_o_output and output_r_mask_ilu

    if two_destinations:
      mac_str += "{ "

    if has_o_output:
      ilu_str += get_output_o_register(output_o_index, output_o_mask)

    if two_destinations:
      mac_str += ", "

    if output_r_mask_ilu:

      # If MAC and ILU are both active, this can only write to r1
      #FIXME: Does this also depend on output_r_mask_mac ?
      if mac != 0x00:
        output_r_index = 1

      ilu_str += 'r%d%s' % (output_r_index, get_write_mask(output_r_mask_ilu))

    if two_destinations:
      mac_str += " }"

    ilu_str += ", " + get_input_register(c, c_is_relative, c_index, v_index)

    operations += [ilu_str]

  return operations
