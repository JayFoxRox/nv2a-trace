def dump(state):
  print("\nRegister combiners:")

  #FIXME: PArse this completly
  combinectl = state.read_nv2a_device_memory_word(0x401940)
  stage_count = combinectl & 0xF
  mux_bit = (combinectl >> 8) & 1
  unique_cf0 = (combinectl >> 12) & 1
  unique_cf1 = (combinectl >> 16) & 1

  mux_bit_str = "MSB" if mux_bit else "LSB"

  #FIXME: Possibly bad order!
  input_regs = (
    'zero',
    'color0',
    'color1',
    'fog',
    'PRIMARY_COLOR',
    'SECONDARY_COLOR',
    '<invalid:6>',
    '<invalid:7>',
    'tex0',
    'tex1',
    'tex2',
    'tex3',
    'spare0',
    'spare1',
    'SPARE0_PLUS_SECONDARY_COLOR', # Only for final combiner (B, C, D)
    'E_TIMES_F' # Only for final combiner (A, B, C, D)
  )

  output_regs = (
    'discard',
    '<invalid:1>',
    '<invalid:2>',
    '<invalid:3>',
    'PRIMARY_COLOR',
    'SECONDARY_COLOR',
    '<invalid:6>',
    '<invalid:7>',
    'tex0',
    'tex1',
    'tex2',
    'tex3',
    'spare0',
    'spare1',
    '<invalid:14>',
    '<invalid:15>'
  )

  mappings_code = ('unsigned(%s)',
                   'unsigned_invert(%s)',
                   'expand(%s)',
                   '-expand(%s)',
                   'half_bias(%s)',
                   '-half_bias(%s)',
                   '%s',
                   '-%s')

  def decode_in_reg(word, shift, is_alpha = False, is_final_combiner_a = False, is_final_combiner_bcd = False):
    v = word >> shift
    mapping = (v >> 5) & 0x7
    alpha = (v >> 4) & 1
    source = (v >> 0) & 0xF

    is_final_combiner_abcd = is_final_combiner_a or is_final_combiner_bcd
    assert(is_final_combiner_bcd or source != 0xE) # SPARE0_PLUS_SECONDARY_COLOR_NV
    assert(is_final_combiner_abcd or source != 0xF) # E_TIMES_F_NV

    s = input_regs[source]

    #FIXME: This might be wrong?
    if not is_alpha:
      s += ".a" if alpha else ".rgb"
    else:
      assert(source != 3) # FIXME: This is supposed to look for FOG
      s += ".a" if alpha else ".b"
    return mappings_code[mapping] % s

  def decode_register_combiner_stage(stage, is_alpha):

    if not is_alpha:
      combine_input = state.read_nv2a_device_memory_word(0x401900 + stage * 4)
    else:
      combine_input = state.read_nv2a_device_memory_word(0x4018C0 + stage * 4)

    a = decode_in_reg(combine_input, 24, is_alpha)
    b = decode_in_reg(combine_input, 16, is_alpha)
    c = decode_in_reg(combine_input, 8, is_alpha)
    d = decode_in_reg(combine_input, 0, is_alpha)

    if not is_alpha:
      combine_output = state.read_nv2a_device_memory_word(0x401920 + stage * 4)

      #FIXME: Support these!
      b_to_a_ab = (combine_output >> 19) & 1
      b_to_a_cd = (combine_output >> 18) & 1
    else:
      combine_output = state.read_nv2a_device_memory_word(0x4018E0 + stage * 4)
      b_to_a_ab = False
      b_to_a_cd = False

    op = (combine_output >> 15) & 7
    ops_code = ('',
                'bias_by_negative_one_half();',
                'scale_by_two();',
                'bias_by_negative_one_half_scale_by_two();',
                'scale_by_four();',
                'scale_by_one_half();',
                '/* <invalid-modifier:6> */', #FIXME: Used in disabled code!
                '/* <invalid-modifier:7> */') #FIXME: Used in disabled code!
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
          res_str = gcc_x
        else:
          res_str = gcc_y

      else:

        if is_dot_product == False:
          res_str = gcc_z
        else:
          res_str = "<invalid>" # FIXME: Assert?
          assert(False)

      return res_str

    # "gcc" stands for general combiner computation.

    if not is_alpha:
      gcc1 = "%s * %s" % (a, b)
      gcc2 = "%s . %s" % (a, b)
      gcc3 = "%s * %s" % (c, d)
      gcc4 = "%s . %s" % (c, d)
      gcc5 = "sum();"
      gcc6 = "mux(); // SPARE0_NV.a & %s" % (mux_bit_str)
    else:
      gcc1 = "%s * %s" % (a, b)
      gcc2 = "%s * %s" % (c, d)
      gcc3 = "sum();"
      gcc4 = "mux(); // SPARE0_NV.a & %s" % (mux_bit_str)

    def get_sum_out(mux_enable):
      if not is_alpha:
        if mux_enable == False:
          rgb_str = gcc5
        else:
          rgb_str = gcc6
        return rgb_str
      else:
        if mux_enable == False:
          a_str = gcc3
        else:
          a_str = gcc4
        return a_str



    ab_out = output_regs[ab_dst]
    if not is_alpha:
      ab_out += ".rgb"
    else:
      ab_out += ".a"
    ab_out += " = " + get_out(ab_dot_enable, gcc1, gcc2, gcc1)
    if b_to_a_ab:
      #FIXME: Will this still write RGB?
      ab_out += "; %s.a = %s.b" % (input_regs[ab_dst], input_regs[ab_dst])

    cd_out = output_regs[cd_dst]
    if not is_alpha:
      cd_out += ".rgb"
    else:
      cd_out += ".a"
    cd_out += " = " + get_out(cd_dot_enable, gcc3, gcc4, gcc2)
    if b_to_a_cd:
      #FIXME: Will this still write RGB?
      cd_out += "; %s.a = %s.b" % (input_regs[cd_dst], input_regs[cd_dst])

    sum_out = output_regs[sum_dst]
    if not is_alpha:
      sum_out += ".rgb"
    else:
      sum_out += ".a"
    sum_out += " = " + get_sum_out(mux_enable)

    return (ab_out, cd_out, sum_out, op_code)

  def decode_final_register_combiner():

    fc0 = state.read_nv2a_device_memory_word(0x401944)
    a = decode_in_reg(fc0, 24, is_final_combiner_a=True)
    b = decode_in_reg(fc0, 16, is_final_combiner_bcd=True)
    c = decode_in_reg(fc0, 8, is_final_combiner_bcd=True)
    d = decode_in_reg(fc0, 0, is_final_combiner_bcd=True)
    fc1 = state.read_nv2a_device_memory_word(0x401948)
    e = decode_in_reg(fc1, 24)
    f = decode_in_reg(fc1, 16)
    g = decode_in_reg(fc1, 8, is_alpha=True) # Alpha scalar

    #FIXME: add these to output!
    specular_clamp = (fc1 >> 7) & 1
    specular_add_invr5 = (fc1 >> 6) & 1
    specular_add_invr12 = (fc1 >> 5) & 1

    comment = "invr5: %d; invr12: %d" % (specular_add_invr5, specular_add_invr12)

    final_product = "final_product = %s * %s;" % (e, f)

    if specular_clamp:
      clamp_color_sum = "clamp_color_sum();"
    else:
      clamp_color_sum = ""

    rgb_str = "lerp(%s, %s, %s) + %s" % (c, b, a, d)
    a_str = "%s" % (g)

    return (comment, clamp_color_sum, final_product, rgb_str, a_str)

  def get_rgba(combinefactor):
    r = (combinefactor >> 16) & 0xFF
    g = (combinefactor >> 8) & 0xFF
    b = (combinefactor >> 0) & 0xFF
    a = (combinefactor >> 24) & 0xFF
    return (r, g, b, a)

  def get_rgba_string(combinerfactor):
    r, g, b, a = get_rgba(combinerfactor)
    return "(%s, %s, %s, %s); // (0x%02X, 0x%02X, 0x%02X, 0x%02X)" % \
            (r/255.0, g/255.0, b/255.0, a/255.0, r, g, b, a)

  print("!!RC1.0")
  print("")
  print("//Note: AB, CD and SUM run in parallel")
  print("//      Each result is clamped to [-1, +1]")
  print("")
  if not unique_cf0:
    combinefactor0 = state.read_nv2a_device_memory_word(0x401880 + 4 * 0)
    print("const color0 = %s" % get_rgba_string(unique_cf0)) # FIXME: Integrate in code
    color0_format = "// const color0 = %s"
  else:
    print("// Unique color0 per-stage")
    color0_format = "const color0 = %s"
  if not unique_cf1:
    combinefactor1 = state.read_nv2a_device_memory_word(0x4018A0 + 4 * 0)
    print("const color1 = %s" % get_rgba_string(unique_cf1)) # FIXME: Integrate in code
    color1_format = "// const color1 = %s"
  else:
    print("// Unique color1 per-stage")
    color1_format = "const color1 = %s"
  for i in range(8):
    print("")
    if i == stage_count:
      print("")
      print("// End of enabled general register combiners")
      print("")

    print("// Stage %d" % i)
    if i >= stage_count:
      print("/* (Disabled)")
    print("{")

    rgb_str = decode_register_combiner_stage(i, is_alpha = False)
    a_str = decode_register_combiner_stage(i, is_alpha = True)

    combinefactor0 = state.read_nv2a_device_memory_word(0x401880 + 4 * i)
    combinefactor1 = state.read_nv2a_device_memory_word(0x4018A0 + 4 * i)

    print("  " + color0_format % (get_rgba_string(combinefactor0)))  
    print("  " + color1_format % (get_rgba_string(combinefactor1)))
    print("  rgb {")
    print("    %s;" % (rgb_str[0]))
    print("    %s;" % (rgb_str[1]))
    print("    %s" % (rgb_str[2]))
    if (rgb_str[3]):
      print("    %s" % (rgb_str[3]))
    print("  }")
    print("  alpha {")
    print("    %s;" % (a_str[0]))
    print("    %s;" % (a_str[1]))
    print("    %s" % (a_str[2]))
    if (a_str[3]):
      print("    %s" % (a_str[3]))
    print("  }")

    print("}")
    if i >= stage_count:
      print("*/")

  print("")
  final_combiner_str = decode_final_register_combiner()
  print("// %s" % (final_combiner_str[0]))
  combinefactor0 = state.read_nv2a_device_memory_word(0x4019AC)
  combinefactor1 = state.read_nv2a_device_memory_word(0x4019B0)
  print("const color0 = %s" % get_rgba_string(combinefactor0))
  print("const color1 = %s" % get_rgba_string(combinefactor1))
  if final_combiner_str[1]:
    print(final_combiner_str[1]) # color_clamp_sum
  print("%s" % (final_combiner_str[2])) # final_product

  #fragment_rgb = lerp(FinalMappedRegister, FinalMappedRegister, FinalMappedRegister) + FinalMappedRegister;
  #fragment_rgb = FinalMappedRegister + lerp(FinalMappedRegister, FinalMappedRegister, FinalMappedRegister);
  #fragment_rgb = lerp(FinalMappedRegister, FinalMappedRegister, FinalMappedRegister);
  #fragment_rgb = FinalMappedRegister * FinalMappedRegister;
  #fragment_rgb = FinalMappedRegister * FinalMappedRegister + FinalMappedRegister;
  #fragment_rgb = FinalMappedRegister;
  #fragment_rgb = FinalMappedRegister + FinalMappedRegister;

  print("out.rgb = %s;" % (final_combiner_str[3]))
  print("out.a = %s;" % (final_combiner_str[4]))
  print("")

