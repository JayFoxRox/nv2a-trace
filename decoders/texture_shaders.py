def dump(state):
  #FIXME: Untested
  print("\nTexture shaders:")

  ops = [
    "PROGRAM_NONE", #   0x00
    "2D_PROJECTIVE", #  0x01
    "3D_PROJECTIVE", #  0x02
    "CUBE_MAP", #       0x03
    "PASS_THROUGH", #   0x04
    "CLIP_PLANE", #     0x05
    "BUMPENVMAP", #     0x06
    "BUMPENVMAP_LUMINANCE", # 0x07
    "BRDF", #           0x08
    "DOT_ST", #         0x09
    "DOT_ZW", #        0x0A
    "PS_TEXTUREMODES_DOT_RFLCT_DIFF", # 0x0B DOT_PRODUCT_DIFFUSE_CUBE_MAP_NV
    "PS_TEXTUREMODES_DOT_RFLCT_SPEC", # 0x0C DOT_PRODUCT_CONST_EYE_REFLECT_CUBE_MAP_NV?
    "DOT_STR_3D", #     0x0D
    "PS_TEXTUREMODES_DOT_STR_CUBE", #   0x0E
    "DEPENDENT_AR", #   0x0F
    "DEPENDENT_GB", #   0x10
    "PS_TEXTUREMODES_DOTPRODUCT", #0x11
    "PS_TEXTUREMODES_DOT_RFLCT_SPEC_CONST" # 0x12
  ]

  assert(len(ops) == 0x13)

  print("!!TS1.0")

  # Read stage configurations
  shaderclipmode = state.read_nv2a_device_memory_word(0x401994)
  #shaderctl = state.read_nv2a_device_memory_word(0x401998) #FIXME
  shaderprog = state.read_nv2a_device_memory_word(0x40199C)

  # Parse stage configurations
  stage = [""] * 4
  for i in range(4):
    stage[i] = ops[(shaderprog >> (5 * i)) & 0x1F]

  # Iterate over all stages backwards
  results = ["nop(); //FIXME: Unset"] * 4
  i = 4
  while i >= 1:

    i -= 1

    print("// Decoding %d; Type %s; FIXME: dependency + expansion + dot-type + clipmode" % (i, stage[i]))
    print("// Matrix:")
    print("// 0.0   0.0  // FIXME")
    print("// 0.0   0.0  // FIXME")

    if stage[i] == "PROGRAM_NONE":
      results[i] = "nop();"
    elif stage[i] == "2D_PROJECTIVE":
      results[i] = "texture_2d(); // or texture_1d or texture_rectangle"
    elif stage[i] == "3D_PROJECTIVE":
      results[i] = "texture_3d();"
    elif stage[i] == "CUBE_MAP":
      results[i] = "texture_cube();"
    elif stage[i] == "PASS_THROUGH":
      results[i] = "pass_through();"
    elif stage[i] == "CLIP_PLANE":
      def _get(i, j):
        state = (shaderclipmode >> (4 * i + j)) & 1 
        "GEQUAL_TO_ZERO" if state else "LESS_THAN_ZERO"
      results[i] = "cull_fragment(%s, %s, %s, %s);" % (_get(i, 0), _get(i, 1), _get(i, 2), _get(i, 3))
    elif stage[i] == "BUMPENVMAP":
      results[i] = "offset_2d(); // or offset_rectangle"
    elif stage[i] == "BUMPENVMAP_LUMINANCE":
      results[i] = "offset_2d_scale(); // or offset_rectangle_scale"
    elif stage[i] == "BRDF":
      assert(False)
    elif stage[i] == "DOT_ST":
      assert(False)
    elif stage[i] == "DOT_ZW":
      if stage[i-1] == "PS_TEXTUREMODES_DOTPRODUCT":
        i -= 1
        results[i+0] = "dot_product_depth_replace_1of2();"
        results[i+1] = "dot_product_depth_replace_2of2();"
      else:
        assert(False)
    elif stage[i] == "PS_TEXTUREMODES_DOT_RFLCT_DIFF":
      assert(False)
    elif stage[i] == "PS_TEXTUREMODES_DOT_RFLCT_SPEC":
      if stage[i-1] == "PS_TEXTUREMODES_DOTPRODUCT":
        if stage[i-2] == "PS_TEXTUREMODES_DOTPRODUCT":
          i -= 2
          results[i+0] = "dot_product_reflect_cube_map_const_eye_1_of_3();"
          results[i+1] = "dot_product_reflect_cube_map_const_eye_2_of_3();"
          results[i+2] = "dot_product_reflect_cube_map_const_eye_3_of_3();"
        else:
          assert(False)
      elif stage[i-1] == "PS_TEXTUREMODES_DOT_RFLCT_DIFF":
        if stage[i-2] == "PS_TEXTUREMODES_DOTPRODUCT":
          i -= 2
          results[i+0] = "dot_product_cube_map_and_reflect_cube_map_const_eye_1_of_3();"
          results[i+1] = "dot_product_cube_map_and_reflect_cube_map_const_eye_2_of_3();"
          results[i+2] = "dot_product_cube_map_and_reflect_cube_map_const_eye_3_of_3();"
        else:
          assert(False)
      else:
        assert(False)
    elif stage[i] == "DOT_STR_3D":
      assert(False)
    elif stage[i] == "PS_TEXTUREMODES_DOT_STR_CUBE":
      if stage[i-1] == "PS_TEXTUREMODES_DOTPRODUCT":
        if stage[i-2] == "PS_TEXTUREMODES_DOTPRODUCT":
          i -= 2
          results[i+0] = "dot_product_reflect_cube_map_eye_from_qs_1_of_3();"
          results[i+1] = "dot_product_reflect_cube_map_eye_from_qs_2_of_3();"
          results[i+2] = "dot_product_reflect_cube_map_eye_from_qs_3_of_3();"
        else:
          assert(False)
      elif stage[i-1] == "PS_TEXTUREMODES_DOT_RFLCT_DIFF":
        if stage[i-2] == "PS_TEXTUREMODES_DOTPRODUCT":
          i -= 2
          results[i+0] = "dot_product_cube_map_and_reflect_cube_map_eye_from_qs_1_of_3();"
          results[i+1] = "dot_product_cube_map_and_reflect_cube_map_eye_from_qs_2_of_3();"
          results[i+2] = "dot_product_cube_map_and_reflect_cube_map_eye_from_qs_3_of_3();"
        else:
          assert(False)
      else:
        assert(False)
    elif stage[i] == "DEPENDENT_AR":
      results[i] = "dependent_ar();"
    elif stage[i] == "DEPENDENT_GB":
      results[i] = "dependent_gb();"
    elif stage[i] == "PS_TEXTUREMODES_DOTPRODUCT":
      assert(False)
    elif stage[i] == "PS_TEXTUREMODES_DOT_RFLCT_SPEC_CONST":
      assert(False)
    else:
      assert(False)

  assert(i == 0)

  # Output stages
  results[::-1]
  for result in results:
    print(result)

  print("")
