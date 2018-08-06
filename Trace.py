import os
import struct

import Texture

from helper import *

PixelDumping = False
DebugPrint = False

commandCount = 0
flipStallCount = 0


debugLog = os.path.join("out", "debug.html")
def addHTML(xx):
  f = open(debugLog,"a")
  f.write("<tr>")
  for x in xx:
    f.write("<td>%s</td>" % x)
  f.write("</tr>\n")
  f.close()
f = open(debugLog,"w")
f.write("<html><head><style>body { font-family: sans-serif; background:#333; color: #ccc } img { border: 1px solid #FFF; } td, tr, table { background: #444; padding: 10px; border:1px solid #888; border-collapse: collapse; }</style></head><body><table>\n")
#FIXME: atexit close tags.. but yolo!
f.close()
addHTML(["<b>#</b>", "<b>Opcode / Method</b>", "..."])



pgraph_dump = None

def dumpPGRAPH(xbox):
  buffer = bytearray([])
  buffer.extend(xbox.read(0xFD400000, 0x200))

  # 0xFD400200 hangs Xbox, I just skipped to 0x400.
  # Needs further testing which regions work.
  buffer.extend(bytes([0] * 0x200))

  buffer.extend(xbox.read(0xFD400400, 0x2000 - 0x400))

  # Return the PGRAPH dump
  assert(len(buffer) == 0x2000)
  return bytes(buffer)












#FIXME: Maybe take a list of vertices?
def DumpVertexAttributes():
  pass

def DumpTextures(xbox, data, *args):
  global PixelDumping
  if not PixelDumping:
    return []
    
  extraHTML = []

  for i in range(4):
    path = "command%d--tex_%d.png" % (commandCount, i)
    img = Texture.dumpTextureUnit(xbox, i)
    if img != None:
      img.save(os.path.join("out", path))
    extraHTML += ['<img height="128px" src="%s" alt="%s"/>' % (path, path)]

  return extraHTML

def DumpSurfaces(xbox, data, *args):
  global PixelDumping
  if not PixelDumping:
    return []
  
#  offset = color_offset
  pitch = xbox.read_u32(0xFD400858) # FIXME: Read from PGRAPH
  #FIXME: Poor var names

  surface_color_offset = xbox.read_u32(0xFD400828)
  surface_clip_x = xbox.read_u32(0xFD4019B4)
  surface_clip_y = xbox.read_u32(0xFD4019B8)

  offset = surface_color_offset

  draw_format = xbox.read_u32(0xFD400804)
  surface_type = xbox.read_u32(0xFD400710)
  swizzle_unk = xbox.read_u32(0xFD400818)

  #FIXME: This does not seem to be a good field for this
  #FIXME: Patched to give 50% of coolness
  swizzled = commandCount & 1 #((surface_type & 3) == 1)
  #FIXME: if surface_type is 0, we probably can't even draw..

  color_fmt = (draw_format >> 12) & 0xF
  if color_fmt == 0x3: # ARGB1555
    fmt_color = 0x3 if swizzled else 0x1C
  elif color_fmt == 0x5: # RGB565
    fmt_color = 0x5 if swizzled else 0x11
  elif color_fmt == 0x7 or color_fmt == 0x8: # XRGB8888
    fmt_color = 0x7 if swizzled else 0x1E
  elif color_fmt == 0xC: # ARGB8888
    fmt_color = 0x6 if swizzled else 0x12
  else:
    raise Exception("Oops! Unknown color fmt %d (0x%X)" % (color_fmt, color_fmt))

  width = (surface_clip_x >> 16) & 0xFFFF
  height = (surface_clip_y >> 16) & 0xFFFF

  #FIXME: Respect anti-aliasing

  path = "command%d--color.png" % (commandCount)
  extraHTML = []
  extraHTML += ['<img height="128px" src="%s" alt="%s"/>' % (path, path)]
  extraHTML += ['%d x %d [pitch = %d (0x%X)], at 0x%08X [PGRAPH: 0x%08X?], format 0x%X, type: 0x%X, swizzle: 0x%X [used %d]' % (width, height, pitch, pitch, offset, surface_color_offset, color_fmt, surface_type, swizzle_unk, swizzled)]
  print(extraHTML[-1])

  img = Texture.dumpTexture(xbox, offset, pitch, fmt_color, width, height)
  if img != None:

    # Hack to remove alpha channel
    if True:
      img = img.convert('RGB')

    img.save(os.path.join("out", path))

  return extraHTML

def HandleBegin(xbox, data, *args):

  # Avoid handling End
  if data == 0:
    return []

  extraHTML = []
  extraHTML += DumpTextures(xbox, data, *args)
  return extraHTML

def HandleEnd(xbox, data, *args):

  # Avoid handling Begin
  if data != 0:
    return []

  extraHTML = []
  extraHTML += DumpSurfaces(xbox, data, *args)
  return extraHTML

def beginPGRAPHRecord(xbox, data, *args):
  global pgraph_dump
  pgraph_dump = dumpPGRAPH(xbox)
  addHTML(["", "", "", "", "Dumped PGRAPH for later"])
  return []

def endPGRAPHRecord(xbox, data, *args):
  global pgraph_dump

  # Debug feature to understand PGRAPH
  if pgraph_dump != None:
    new_pgraph_dump = dumpPGRAPH(xbox)

    # This blacklist was created from a CLEAR_COLOR, CLEAR
    blacklist = []
    blacklist += [0x0040000C] # 0xF3DF0479 → 0xF3DE04F9
    blacklist += [0x0040002C] # 0xF3DF37FF → 0xF3DE37FF
    blacklist += [0x0040010C] # 0x03DF0000 → 0x020000F1
    blacklist += [0x0040012C] # 0x13DF379F → 0x131A37FF
    blacklist += [0x00400704] # 0x00001D9C → 0x00001D94
    blacklist += [0x00400708] # 0x01DF0000 → 0x000000F1
    blacklist += [0x0040070C] # 0x01DF0000 → 0x000000F1
    blacklist += [0x0040072C] # 0x01DF2700 → 0x000027F1
    blacklist += [0x00400740] # 0x01DF37DD → 0x01DF37FF
    blacklist += [0x00400744] # 0x18111D9C → 0x18111D94
    blacklist += [0x00400748] # 0x01DF0011 → 0x000000F1
    blacklist += [0x0040074C] # 0x01DF0097 → 0x000000F7
    blacklist += [0x00400750] # 0x00DF005C → 0x00DF0064
    blacklist += [0x00400760] # 0x000000CC → 0x000000FF
    blacklist += [0x00400764] # 0x08001D9C → 0x08001D94
    blacklist += [0x00400768] # 0x01DF0000 → 0x000000F1
    blacklist += [0x0040076C] # 0x01DF0000 → 0x000000F1
    blacklist += [0x00400788] # 0x01DF110A → 0x000011FB
    blacklist += [0x004007A0] # 0x00200100 → 0x00201D70
    blacklist += [0x004007A4] # 0x00200100 → 0x00201D70
    blacklist += [0x004007A8] # 0x00200100 → 0x00201D70
    blacklist += [0x004007AC] # 0x00200100 → 0x00201D70
    blacklist += [0x004007B0] # 0x00200100 → 0x00201D70
    blacklist += [0x004007B4] # 0x00200100 → 0x00201D70
    blacklist += [0x004007B8] # 0x00200100 → 0x00201D70
    blacklist += [0x004007BC] # 0x00200100 → 0x00201D70
    blacklist += [0x004007C0] # 0x00000000 → 0x000006C9
    blacklist += [0x004007C4] # 0x00000000 → 0x000006C9
    blacklist += [0x004007C8] # 0x00000000 → 0x000006C9
    blacklist += [0x004007CC] # 0x00000000 → 0x000006C9
    blacklist += [0x004007D0] # 0x00000000 → 0x000006C9
    blacklist += [0x004007D4] # 0x00000000 → 0x000006C9
    blacklist += [0x004007D8] # 0x00000000 → 0x000006C9
    blacklist += [0x004007DC] # 0x00000000 → 0x000006C9
    blacklist += [0x004007E0] # 0x00000000 → 0x000006C9
    blacklist += [0x004007E4] # 0x00000000 → 0x000006C9
    blacklist += [0x004007E8] # 0x00000000 → 0x000006C9
    blacklist += [0x004007EC] # 0x00000000 → 0x000006C9
    blacklist += [0x004007F0] # 0x00000000 → 0x000006C9
    blacklist += [0x004007F4] # 0x00000000 → 0x000006C9
    blacklist += [0x004007F8] # 0x00000000 → 0x000006C9
    blacklist += [0x004007FC] # 0x00000000 → 0x000006C9
    blacklist += [0x00400D6C] # 0x00000000 → 0xFF000000
    blacklist += [0x0040110C] # 0x03DF0000 → 0x020000F1
    blacklist += [0x0040112C] # 0x13DF379F → 0x131A37FF
    blacklist += [0x00401704] # 0x00001D9C → 0x00001D94
    blacklist += [0x00401708] # 0x01DF0000 → 0x000000F1
    blacklist += [0x0040170C] # 0x01DF0000 → 0x000000F1
    blacklist += [0x0040172C] # 0x01DF2700 → 0x000027F1
    blacklist += [0x00401740] # 0x01DF37FD → 0x01DF37FF
    blacklist += [0x00401744] # 0x18111D9C → 0x18111D94
    blacklist += [0x00401748] # 0x01DF0011 → 0x000000F1
    blacklist += [0x0040174C] # 0x01DF0097 → 0x000000F7
    blacklist += [0x00401750] # 0x00DF0064 → 0x00DF006C
    blacklist += [0x00401760] # 0x000000CC → 0x000000FF
    blacklist += [0x00401764] # 0x08001D9C → 0x08001D94
    blacklist += [0x00401768] # 0x01DF0000 → 0x000000F1
    blacklist += [0x0040176C] # 0x01DF0000 → 0x000000F1
    blacklist += [0x00401788] # 0x01DF110A → 0x000011FB
    blacklist += [0x004017A0] # 0x00200100 → 0x00201D70
    blacklist += [0x004017A4] # 0x00200100 → 0x00201D70
    blacklist += [0x004017A8] # 0x00200100 → 0x00201D70
    blacklist += [0x004017AC] # 0x00200100 → 0x00201D70
    blacklist += [0x004017B0] # 0x00200100 → 0x00201D70
    blacklist += [0x004017B4] # 0x00200100 → 0x00201D70
    blacklist += [0x004017B8] # 0x00200100 → 0x00201D70
    blacklist += [0x004017BC] # 0x00200100 → 0x00201D70
    blacklist += [0x004017C0] # 0x00000000 → 0x000006C9
    blacklist += [0x004017C4] # 0x00000000 → 0x000006C9
    blacklist += [0x004017C8] # 0x00000000 → 0x000006C9
    blacklist += [0x004017CC] # 0x00000000 → 0x000006C9
    blacklist += [0x004017D0] # 0x00000000 → 0x000006C9
    blacklist += [0x004017D4] # 0x00000000 → 0x000006C9
    blacklist += [0x004017D8] # 0x00000000 → 0x000006C9
    blacklist += [0x004017DC] # 0x00000000 → 0x000006C9
    blacklist += [0x004017E0] # 0x00000000 → 0x000006C9
    blacklist += [0x004017E4] # 0x00000000 → 0x000006C9
    blacklist += [0x004017E8] # 0x00000000 → 0x000006C9
    blacklist += [0x004017EC] # 0x00000000 → 0x000006C9
    blacklist += [0x004017F0] # 0x00000000 → 0x000006C9
    blacklist += [0x004017F4] # 0x00000000 → 0x000006C9
    blacklist += [0x004017F8] # 0x00000000 → 0x000006C9
    blacklist += [0x004017FC] # 0x00000000 → 0x000006C9
    #blacklist += [0x0040186C] # 0x00000000 → 0xFF000000 # CLEAR COLOR
    blacklist += [0x0040196C] # 0x00000000 → 0xFF000000
    blacklist += [0x00401C6C] # 0x00000000 → 0xFF000000
    blacklist += [0x00401D6C] # 0x00000000 → 0xFF000000

    for i in range(len(pgraph_dump) // 4):
      off = 0x00400000 + i * 4
      if off in blacklist:
        continue
      word = struct.unpack_from("<L", pgraph_dump, i * 4)[0]
      new_word = struct.unpack_from("<L", new_pgraph_dump, i * 4)[0]
      if new_word != word:
        addHTML(["", "", "", "", "Modified 0x%08X in PGRAPH: 0x%08X &rarr; 0x%08X" % (off, word, new_word)])
    pgraph_dump = None
    addHTML(["", "", "", "", "Finished PGRAPH comparison"])

  return []





def updateSurfaceClipX(data):
  global surface_clip_x
  surface_clip_x = data

def updateSurfaceClipY(data):
  global surface_clip_y
  surface_clip_y = data

def updateSurfaceFormat(data):
  print("Changing surface format")
  # Anti-aliasing in 0x00400710

def updateSurfacePitch(data):
  print("Changing surface pitch")
  # 0x00400858 and 0x0040085C in pgraph

def updateSurfaceAddress(data):
  global color_offset
  print("Changing color surface address")
  #FIXME: Mabye in PGRAPH: 0x00400828 ? [modified by command]
  color_offset = data

def HandleFlipStall(xbox, data, *args):
  global flipStallCount
  print("Flip (Stall)")
  flipStallCount += 1
  return []

def HandleSetTexture(data, index):
  pass
  #FIXME: Dump texture here?

def CheckTarget(xbox, data, *args):
  pass
  #FIXME: Check if the CPU has modified and fixup if necessary
  return []













method_callbacks = {}

def filterPGRAPHMethod(xbox, method):
  # Do callback for pre-method
  if method in method_callbacks:
    return method_callbacks[method]
  return [], []
  

def recordPGRAPHMethod(xbox, method_info, data, pre_info, post_info):
  global method_callbacks
  global commandCount
  global flipStallCount

  dataf = struct.unpack("<f", struct.pack("<I", data))[0]

  addHTML(["", "0x%08X" % method_info['address'], "0x%04X" % method_info['method'], "0x%08X / %f" % (data, dataf)] + pre_info + post_info)


def parseCommand(addr, word, display=False):

  s = "Opcode: 0x%08X" % (word)

  if ((word & 0xe0000003) == 0x20000000):
    print("old jump")
    #state->get_jmp_shadow = control->dma_get;
    #NV2A_DPRINTF("pb OLD_JMP 0x%" HWADDR_PRIx "\n", control->dma_get);
    addr = word & 0x1fffffff
  elif ((word & 3) == 1):
    addr = word & 0xfffffffc
    print("jump 0x%08X" % addr)
    #state->get_jmp_shadow = control->dma_get;
  elif ((word & 3) == 2):
    print("unhandled opcode type: call")
    #if (state->subroutine_active) {
    #  state->error = NV_PFIFO_CACHE1_DMA_STATE_ERROR_CALL;
    #  break;
    #}
    #state->subroutine_return = control->dma_get;
    #state->subroutine_active = true;
    #control->dma_get = word & 0xfffffffc;
    addr = 0
  elif (word == 0x00020000):
    # return
    print("unhandled opcode type: return")
    addr = 0
  elif ((word & 0xe0030003) == 0) or ((word & 0xe0030003) == 0x40000000):
    # methods
    method = word & 0x1fff;
    subchannel = (word >> 13) & 7;
    method_count = (word >> 18) & 0x7ff;
    method_nonincreasing = word & 0x40000000;
    #state->dcount = 0;

    s += "; Method: 0x%04X (%d times)" % (method, method_count)
    addr += 4 + method_count * 4

  else:
    print("unknown opcode type")

  if display:
    print(s)

  return addr











def run_fifo(xbox, put_addr, v_dma_put_addr_real):
  global DebugPrint


  v_dma_put_addr_target = put_addr

  # Queue the commands
  xbox.write_u32(dma_put_addr, v_dma_put_addr_target)



  def JumpCheck(v_dma_put_addr_real):
    # See if the PB target was modified.
    # If necessary, we recover the current target to keep the GPU stuck on our
    # current command.
    v_dma_put_addr_new_real = xbox.read_u32(dma_put_addr)
    if (v_dma_put_addr_new_real != v_dma_put_addr_target):
      warning = "PB was modified! Got 0x%08X, but expected: 0x%08X; Restoring." % (v_dma_put_addr_new_real, v_dma_put_addr_target)
      print(warning)
      addHTML(["WARNING", warning])
      #FIXME: Ensure that the pusher is still disabled, or we might be
      #       screwed already. Because the pusher probably pushed new data
      #       to the CACHE which we attempt to avoid.

      s1 = xbox.read_u32(put_state)
      if s1 & 1:
        print("PB was modified and pusher was already active!")
        time.sleep(60.0)

      xbox.write_u32(dma_put_addr, v_dma_put_addr_target)
      v_dma_put_addr_real = v_dma_put_addr_new_real
    return v_dma_put_addr_real



  #FIXME: we can save this read in some cases, as we should know where we are
  v_dma_get_addr = xbox.read_u32(dma_get_addr)


  # Loop while this command is being ran.
  # This is necessary because a whole command might not fit into CACHE.
  # So we have to process it chunk by chunk.
  command_base = v_dma_get_addr
  #FIXME: This used to be a check which made sure that `v_dma_get_addr` did
  #       never leave the known PB.
  while v_dma_get_addr != v_dma_put_addr_target:
    if DebugPrint: print("At 0x%08X, target is 0x%08X (Real: 0x%08X)" % (v_dma_get_addr, v_dma_put_addr_target, v_dma_put_addr_real))
    if DebugPrint: printDMAstate()

    # Disable PGRAPH, so it can't run anything from CACHE.
    disable_pgraph_fifo(xbox)
    wait_until_pgraph_idle(xbox)

    # This scope should be atomic.
    if True:

      # Avoid running bad code, if the PUT was modified sometime during
      # this command.
      v_dma_put_addr_real = JumpCheck(v_dma_put_addr_real)

      # Kick our planned commands into CACHE now.
      resume_fifo_pusher(xbox)
      pause_fifo_pusher(xbox)

    # Run the commands we have moved to CACHE, by enabling PGRAPH.
    enable_pgraph_fifo(xbox)

    # Get the updated PB address.
    v_dma_get_addr = xbox.read_u32(dma_get_addr)





  # It's possible that the CPU updated the PUT after execution
  v_dma_put_addr_real = JumpCheck(v_dma_put_addr_real)

  # Also show that we processed the commands.
  if DebugPrint: dumpPBState()


  return v_dma_put_addr_real







def parsePushBufferCommand(xbox, get_addr):
  global DebugPrint

  # Retrieve command type from Xbox
  word = xbox.read_u32(0x80000000 | get_addr)


  #FIXME: Get where this command ends
  next_parser_addr = parseCommand(get_addr, word, DebugPrint)

  # If we don't know where this command ends, we have to abort.
  if next_parser_addr == 0:
    return None, 0


  # Check which method it is.
  if ((word & 0xe0030003) == 0) or ((word & 0xe0030003) == 0x40000000):
    # methods
    method = word & 0x1fff;
    subchannel = (word >> 13) & 7;
    method_count = (word >> 18) & 0x7ff;
    method_nonincreasing = word & 0x40000000;

    # Download this command from Xbox
    command = xbox.read(0x80000000 | (get_addr + 4), method_count * 4)
    
    #FIXME: Unpack all of them?
    data = struct.unpack("<" + "L" * method_count, command)
    assert(len(data) == method_count)

    method_info = {}
    method_info['address'] = get_addr
    method_info['method'] = method
    method_info['nonincreasing'] = method_nonincreasing
    method_info['subchannel'] = subchannel
    method_info['data'] = data
  else:
    method_info = None

  return method_info, next_parser_addr

def filterPushBufferCommand(xbox, method_info):

  pre_callbacks = []
  post_callbacks = []

  method = method_info['method']
  for data in method_info['data']:
    pre_callbacks_this, post_callbacks_this = filterPGRAPHMethod(xbox, method)

    # Queue the callbacks
    pre_callbacks += pre_callbacks_this
    post_callbacks += post_callbacks_this

    if not method_info['nonincreasing']:
      method += 4

  return pre_callbacks, post_callbacks


def recordPushBufferCommand(xbox, address, method_info, pre_info, post_info):
  global commandCount

  # Put info in debug HTML
  addHTML(["%d" % commandCount, "%s" % method_info])
  for data in method_info['data']:
    recordPGRAPHMethod(xbox, method_info, data, pre_info, post_info)

  commandCount += 1

  return


def processPushBufferCommands(xbox, get_addr, put_addr):
  parser_addr = get_addr

  sched_post_callbacks = []

  timeout = 0

  while parser_addr != put_addr:

    # Filter commands and check where it wants to go to
    method_info, post_addr = parsePushBufferCommand(xbox, parser_addr)

    # We have a problem if we can't tell where to go next
    if post_addr == 0:
      return 0

    # If we have simulated too many instructions without running, we just run
    if timeout > 10:
      put_addr = run_fifo(xbox, parser_addr, put_addr)
      addHTML(["WARNING", "Flushing to FIFO due to %d unprocessed commands" % timeout])
      timeout = 0

    # If we have a method, work with it
    if method_info is None:

      addHTML(["WARNING", "No method. Going to 0x%08X" % post_addr])

      # Consider this as 1 instruction (not an exact science: arbitrary pick)
      timeout += 1

    else:

      # Check what method this is
      pre_callbacks, post_callbacks = filterPushBufferCommand(xbox, method_info)


      def foo(xbox, data, *args):
        return []
      #pre_callbacks = [] #[foo]
      #post_callbacks = #[]

      # Go where we can do pre-callback
      pre_info = []
      if len(pre_callbacks) > 0:
      
        # Go where we want to go
        put_addr = run_fifo(xbox, parser_addr, put_addr)
        timeout = 0

        # Do the pre callbacks before running the command
        #FIXME: assert we are where we wanted to be
        for callback in pre_callbacks:
          pre_info += callback(xbox, method_info['data'][0])


      # Go where we can do post-callback
      post_info = []
      if len(post_callbacks) > 0:

        # If we reached target, we can't step again without leaving valid buffer
        assert(parser_addr != put_addr)

        # Go where we want to go (equivalent to step)
        put_addr = run_fifo(xbox, post_addr, put_addr)
        timeout = 0

        # Do all post callbacks
        for callback in post_callbacks:
          post_info += callback(xbox, method_info['data'][0])


      # Add the pushbuffer command to log
      recordPushBufferCommand(xbox, parser_addr, method_info, pre_info, post_info)
    
      # Count number of simulated instructions
      timeout += 1 + len(method_info['data'])

      # Move parser to the next instruction
      parser_addr = post_addr



  return parser_addr, put_addr

def recordedFlipStallCount():
  global flipStallCount
  return flipStallCount

def recordedPushBufferCommandCount():
  global commandCount
  return commandCount














def methodHooks(method, pre_hooks, post_hooks, user = None):
  global method_callbacks
  print("Registering method hook for 0x%04X" % method)
  method_callbacks[method] = (pre_hooks, post_hooks)
  return



methodHooks(0x1D94, [],               [DumpSurfaces])    # CLEAR
methodHooks(0x17FC, [HandleBegin],    [HandleEnd])  # BEGIN_END

#FIXME: These shouldn't be necessary, but I can't find this address in PGRAPH
#methodHooks(0x0200, [],               [updateSurfaceClipX])
#methodHooks(0x0204, [],               [updateSurfaceClipY])
#methodHooks(0x0208, [],               [updateSurfaceFormat])
#methodHooks(0x020C, [],               [updateSurfacePitch])
#methodHooks(0x0210, [],               [updateSurfaceAddress])

# Check for texture address changes
#for i in range(4):
#  methodHooks(0x1B00 + 64 * i, [],    [HandleSetTexture], i)

# Add the list of commands which might trigger CPU actions
methodHooks(0x0100, [],               [CheckTarget])     # NOP
methodHooks(0x0130, [],               [CheckTarget,      # FLIP_STALL
                                       HandleFlipStall])
methodHooks(0x1D70, [],               [CheckTarget])     # BACK_END_WRITE_SEMAPHORE_RELEASE



