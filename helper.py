
dma_state = 0xFD003228
dma_put_addr = 0xFD003240
dma_get_addr = 0xFD003244
dma_subroutine = 0xFD00324C

put_addr = 0xFD003210
put_state = 0xFD003220
get_addr = 0xFD003270
get_state = 0xFD003250

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
  while(xbox.read_u32(get_state) & (1 << 4)):
    pass

def pause_fifo_puller(xbox):
  # Idle the puller and pusher
  s1 = xbox.read_u32(get_state)
  xbox.write_u32(get_state, s1 & 0xFFFFFFFE)
  if delay(): pass
  #print("Puller State was 0x" + format(s1, '08X'))

def pause_fifo_pusher(xbox):
  s1 = xbox.read_u32(put_state)
  xbox.write_u32(put_state, s1 & 0xFFFFFFFE)
  if delay(): pass
  if False:
    s1 = xbox.read_u32(0xFD003200)
    xbox.write_u32(0xFD003200, s1 & 0xFFFFFFFE)
    if delay(): pass
    #print("Pusher State was 0x" + format(s1, '08X'))

def resume_fifo_puller(xbox):
  # Resume puller and pusher
  s2 = xbox.read_u32(get_state)
  xbox.write_u32(get_state, (s2 & 0xFFFFFFFE) | 1) # Recover puller state
  if delay(): pass

def resume_fifo_pusher(xbox):
  if False:
    s2 = xbox.read_u32(0xFD003200)
    xbox.write_u32(0xFD003200, s2 & 0xFFFFFFFE | 1)
    if delay(): pass
  s2 = xbox.read_u32(put_state)
  xbox.write_u32(put_state, (s2 & 0xFFFFFFFE) | 1) # Recover pusher state
  if delay(): pass

def dumpPB(start, end):
  offset = start
  while(offset != end):
    offset = parseCommand(offset, True)
    if offset == 0:
      break

#FIXME: This works poorly if the method count is not 0
def dumpPBState():
  v_dma_get_addr = read_u32(dma_get_addr)
  v_dma_put_addr = read_u32(dma_put_addr)
  v_dma_subroutine = read_u32(dma_subroutine)

  print("PB-State: 0x%08X / 0x%08X / 0x%08X" % (v_dma_get_addr, v_dma_put_addr, v_dma_subroutine))
  dumpPB(v_dma_get_addr, v_dma_put_addr)
  print()

def dumpCacheState():
  v_get_addr = read_u32(get_addr)
  v_put_addr = read_u32(put_addr)

  v_get_state = read_u32(get_state)
  v_put_state = read_u32(put_state)

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

