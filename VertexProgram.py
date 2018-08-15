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

output_registers = (
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
  if mask == 0xF: return "" # Same as .xyzw
  mask_str = "."
  for i in range(4):
    if (mask << (4 - i)) & 1: mask_str += 'x' + i
  return mask_str


def get_output_register(register, mask):
  if register & 0: # FIXME: check if this is in reg space
    register_str = output_registers[index]
  else:
    register_str = "c[%d]" % (index - 96)
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

def get_input_register(negate, mask):
  register_str = "-" if negate else ""
  if source == 1: # Register
    register_str += "r%d" % r_index
  elif source == 2: # Vertex attribute
    register_str += "v%d" % v_index
  elif source == 3: # Constant
    # FIXME: Do 'a0 - 40' instead of 'a0 + -40'?
    index = "a0 + " if is_relative else ""
    index +=  "%d" % (c_index - 96)
    register_str += "c[%s]" % index
  register_str += get_swizzle_mask(mask)
  return register_str

def get_instruction(instruction):

  mac = 0 # FIXME: Parse
  ilu = 0 # FIXME: Parse

  owm = False # FIXME: Parse

  operations = []

  # We also check for ILU, so at least one of them generates a nop
  if mac != 0x00 or ilu == 0x00:
    mac_operation = mac_operations[mac]

    mac_str = mac_operation[0]
    has_output = owm and not om

    #FIXME: Is this handled correctly for ARL?
    two_destinations = has_output and rwm

    if two_destinations:
      mac_str += "{ "

    if mac == 0xD: # Check for ARL output
      mac_str += "a0.x"
    elif has_output:
      mac_str += get_output_register()

    if two_destinations:
      mac_str += ", r%d%s }" % (rw, rwm)

    if mac_operation[1]:
      mac_str += ", " + get_input_register(a)
    if mac_operation[2]:
      mac_str += ", " + get_input_register(b)
    if mac_operation[3]:
      mac_str += ", " + get_input_register(c)

    operations += [mac_str]

  if ilu != 0x00:
    ilu_str = ilu_operations[ilu]

    has_output = owm and om

    #FIXME: Add output
    #FIXME: Parse arguments

    operations += [ilu_str]

  return operations
