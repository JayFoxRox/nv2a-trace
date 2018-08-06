#!/usr/bin/env python3 -u

from xboxpy import *

from helper import *

# Create output folder
import os
try:
  os.mkdir("out")
except:
  pass

import time
import signal
import sys
import struct
import traceback


import Trace


abortNow = False


def signal_handler(signal, frame):
  global abortNow
  if abortNow == False:
    print('Got first SIGINT! Aborting..')
    abortNow = True
  else:
    print('Got second SIGINT! Forcing exit')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)



# Hack to pretend we have a better API in xboxpy
class Xbox:
  def __init__(self):
    self.read_u32 = read_u32
    self.write_u32 = write_u32
    self.read = read
    self.write = write
xbox = Xbox()

def main():

  global abortNow


  print("\n\nSearching stable PB state\n\n")
  
  while True:

    # Stop consuming CACHE entries.
    disable_pgraph_fifo(xbox)

    # Kick the pusher, so that it fills the cache CACHE.
    resume_fifo_pusher(xbox)
    pause_fifo_pusher(xbox)

    # Now drain the CACHE
    enable_pgraph_fifo(xbox)

    # Check out where the PB currently is and where it was supposed to go.
    v_dma_put_addr_real = xbox.read_u32(dma_put_addr)
    v_dma_get_addr = xbox.read_u32(dma_get_addr)

    # Check if we have any methods left to run and skip those.
    v_dma_state = xbox.read_u32(dma_state)
    v_dma_method_count = (v_dma_state >> 18) & 0x7ff
    v_dma_get_addr += v_dma_method_count * 4

    # Hide all commands from the PB by setting PUT = GET.
    v_dma_put_addr_target = v_dma_get_addr
    xbox.write_u32(dma_put_addr, v_dma_put_addr_target)

    # Resume pusher - The PB can't run yet, as it has no commands to process.
    resume_fifo_pusher(xbox)

  
    # We might get issues where the pusher missed our PUT (miscalculated).
    # This can happen as `v_dma_method_count` is not the most accurate.
    # Probably because the DMA is halfway through a transfer.
    # So we pause the pusher again to validate our state
    pause_fifo_pusher(xbox)

    v_dma_put_addr_target_check = xbox.read_u32(dma_put_addr)
    v_dma_get_addr_check = xbox.read_u32(dma_get_addr)

    # We want the PB to be paused
    if v_dma_get_addr_check != v_dma_put_addr_target_check:
      print("Oops GET did not reach PUT!")
      continue

    # Ensure that we are at the correct offset
    if v_dma_put_addr_target_check != v_dma_put_addr_target:
      print("Oops PUT was modified!")
      continue

    break
   
  print("\n\nStepping through PB\n\n")

  # Start measuring time
  begin_time = time.monotonic()

  # Step through the PB until we finish.
  while(v_dma_get_addr != v_dma_put_addr_real):

    # Check if the user wants to exit first
    if abortNow:
      xbox.write_u32(dma_put_addr, v_dma_put_addr_real)
      break

    # Loop until we hit an instruction we have to filter
    try:

      # Verify we are where we think we are
      v_dma_get_addr_real = xbox.read_u32(dma_get_addr)
      assert(v_dma_get_addr == v_dma_get_addr_real)

      v_dma_get_addr, v_dma_put_addr_real = Trace.processPushBufferCommands(xbox, v_dma_get_addr, v_dma_put_addr_real)
    except:
      traceback.print_exc()
      abortNow = True


  print("\n\nFinished PB\n\n")

  # We can continue the cache updates now.
  resume_fifo_pusher(xbox)

  # Finish measuring time
  end_time = time.monotonic()
  duration = end_time - begin_time

  flipStallCount = Trace.recordedFlipStallCount()
  commandCount = Trace.recordedPushBufferCommandCount()
  
  print("Recorded %d flip stalls and %d PB commands (%.2f commands / second)" % (flipStallCount, commandCount, commandCount / duration))

if __name__ == '__main__':
  main()
