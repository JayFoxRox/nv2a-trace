
dma_state = 0xFD003228
DMA_PUT_ADDR = 0xFD003240
DMA_GET_ADDR = 0xFD003244
dma_subroutine = 0xFD00324C

PUT_ADDR = 0xFD003210
PUT_STATE = 0xFD003220
GET_ADDR = 0xFD003270
GET_STATE = 0xFD003250

pgraph_state = 0xFD400720
pgraph_status = 0xFD400700


def delay():
  #FIXME: if this returns `True`, the functions below should have their own
  #       loops which check for command completion
  #time.sleep(0.01)
  return False


def disable_pgraph_fifo(xbox):
  s1 = xbox.read_u32(pgraph_state)
  xbox.write_u32(pgraph_state, s1 & 0xFFFFFFFE)

def wait_until_pgraph_idle(xbox):
  while(xbox.read_u32(pgraph_status) & 0x00000001):
    pass

def enable_pgraph_fifo(xbox):
  s1 = xbox.read_u32(pgraph_state)
  xbox.write_u32(pgraph_state, s1 | 0x00000001)
  if delay(): pass

def wait_until_pusher_idle(xbox):
  while(xbox.read_u32(GET_STATE) & (1 << 4)):
    pass

def pause_fifo_puller(xbox):
  # Idle the puller and pusher
  s1 = xbox.read_u32(GET_STATE)
  xbox.write_u32(GET_STATE, s1 & 0xFFFFFFFE)
  if delay(): pass
  #print("Puller State was 0x" + format(s1, '08X'))

def pause_fifo_pusher(xbox):
  s1 = xbox.read_u32(PUT_STATE)
  xbox.write_u32(PUT_STATE, s1 & 0xFFFFFFFE)
  if delay(): pass
  if False:
    s1 = xbox.read_u32(0xFD003200)
    xbox.write_u32(0xFD003200, s1 & 0xFFFFFFFE)
    if delay(): pass
    #print("Pusher State was 0x" + format(s1, '08X'))

def resume_fifo_puller(xbox):
  # Resume puller and pusher
  s2 = xbox.read_u32(GET_STATE)
  xbox.write_u32(GET_STATE, (s2 & 0xFFFFFFFE) | 1) # Recover puller state
  if delay(): pass

def resume_fifo_pusher(xbox):
  if False:
    s2 = xbox.read_u32(0xFD003200)
    xbox.write_u32(0xFD003200, s2 & 0xFFFFFFFE | 1)
    if delay(): pass
  s2 = xbox.read_u32(PUT_STATE)
  xbox.write_u32(PUT_STATE, (s2 & 0xFFFFFFFE) | 1) # Recover pusher state
  if delay(): pass









def parseCommand(addr, word, display=False):

  s = "0x%08X: Opcode: 0x%08X" % (addr, word)

  if ((word & 0xe0000003) == 0x20000000):
    #state->get_jmp_shadow = control->dma_get;
    #NV2A_DPRINTF("pb OLD_JMP 0x%" HWADDR_PRIx "\n", control->dma_get);
    addr = word & 0x1ffffffc
    print(s + "; old jump 0x%08X" % addr)
  elif ((word & 3) == 1):
    addr = word & 0xfffffffc
    print(s + "; jump 0x%08X" % addr)
    #state->get_jmp_shadow = control->dma_get;
  elif ((word & 3) == 2):
    print(s + "; unhandled opcode type: call")
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
    print(s + "; unhandled opcode type: return")
    addr = 0
  elif ((word & 0xe0030003) == 0) or ((word & 0xe0030003) == 0x40000000):
    # methods
    method = word & 0x1fff;
    subchannel = (word >> 13) & 7;
    method_count = (word >> 18) & 0x7ff;
    method_nonincreasing = word & 0x40000000;
    #state->dcount = 0;

    if display:
      print(s + "; Method: 0x%04X (%d times)" % (method, method_count))
    addr += 4 + method_count * 4

  else:
    print(s + "; unknown opcode type")


  return addr

def dumpPB(start, end):
  offset = start
  while(offset != end):
    offset = parseCommand(offset, True)
    if offset == 0:
      break

#FIXME: This works poorly if the method count is not 0
def dumpPBState(xbox):
  v_dma_get_addr = xbox.read_u32(DMA_GET_ADDR)
  v_dma_put_addr = xbox.read_u32(DMA_PUT_ADDR)
  v_dma_subroutine = xbox.read_u32(dma_subroutine)

  s1 = xbox.read_u32(PUT_STATE)

  print("PB-State: 0x%08X / 0x%08X / 0x%08X [PUT state: 0x%08X]" % (v_dma_get_addr, v_dma_put_addr, v_dma_subroutine, s1))
  dumpPB(v_dma_get_addr, v_dma_put_addr)
  print()

def dumpCacheState():
  v_get_addr = read_u32(GET_ADDR)
  v_put_addr = read_u32(PUT_ADDR)

  v_get_state = read_u32(GET_STATE)
  v_put_state = read_u32(PUT_STATE)

  print("CACHE-State: 0x%X / 0x%X" % (v_get_addr, v_put_addr))

  print("Put / Pusher enabled: %s" % ("Yes" if (v_put_state & 1) else "No"))
  print("Get / Puller enabled: %s" % ("Yes" if (v_get_state & 1) else "No"))

  print("Cache:")
  for i in range(128):

    cache1_method = read_u32(0xFD003800 + i * 8)
    cache1_data = read_u32(0xFD003804 + i * 8)

    s = "  [0x%02X] 0x%04X (0x%08X)" % (i, cache1_method, cache1_data)
    v_get_offset = i * 8 - v_get_addr
    if v_get_offset >= 0 and v_get_offset < 8:
      s += " < get[%d]" % v_get_offset
    v_put_offset = i * 8 - v_put_addr
    if v_put_offset >= 0 and v_put_offset < 8:
      s += " < put[%d]" % v_put_offset

    print(s)
  print()

  return

def printDMAstate():

  v_dma_state = read_u32(dma_state)
  v_dma_method = v_dma_state & 0x1FFC
  v_dma_subchannel = (v_dma_state >> 13) & 7
  v_dma_method_count = (v_dma_state >> 18) & 0x7ff
  v_dma_method_nonincreasing = v_dma_state & 1
  # higher bits are for error signalling?
  
  print("v_dma_method: 0x%04X (count: %d)" % (v_dma_method, v_dma_method_count))

