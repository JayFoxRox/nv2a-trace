import struct

def dump(state):
  print("\nFog:")

  def decode_float(word):
    return struct.unpack("<f", struct.pack("<L", word))[0]

  control_3 = state.read_nv2a_device_memory_word(0x401958)

  fog_mode = (control_3 >> 16) & 0x7
  fog_modes_str = ('LINEAR', 'EXP', '<unknown:2>' 'EXP2', 'LINEAR_ABS', 'EXP_ABS', '<unknown:6>', 'EXP2_ABS')
  print("Mode: %s" % (fog_modes_str[fog_mode]))

  fog_enable = (control_3 >> 8) & 1
  print("Enable: %s" % str(fog_enable))

  fog_color = state.read_nv2a_device_memory_word(0x401980)
  print("Color: 0x%08X" % (fog_color))

  fog_param0 = state.read_nv2a_device_memory_word(0x401984)
  print("Parameter[0] (bias): 0x%08X (%f)" % (fog_param0, decode_float(fog_param0)))
  fog_param1 = state.read_nv2a_device_memory_word(0x401988)
  print("Parameter[1] (scale): 0x%08X (%f)" % (fog_param1, decode_float(fog_param1)))

  print("")
