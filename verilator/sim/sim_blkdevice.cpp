#include <iostream>
#include <queue>
#include <string>
#include <cstring>
#include <cstdlib>
#include "cd_window.h"

#include "sim_blkdevice.h"
#include "sim_console.h"

#ifndef _MSC_VER
#else
#define WIN32
#endif


static DebugConsole console;

IData* sd_lba[kVDNUM]= {NULL,NULL,NULL,NULL,NULL,
                   NULL,NULL,NULL,NULL,NULL};
CData* sd_rd=NULL;           // 2-bit in MacLC
CData* sd_wr=NULL;           // 2-bit in MacLC
CData* sd_ack=NULL;          // 2-bit in MacLC
SData* sd_buff_addr=NULL;    // 13-bit like hps_io
CData* sd_blk_cnt=NULL;
SData* sd_buff_dout=NULL;    // 16-bit for MacLC
SData* sd_buff_din[kVDNUM]= {NULL,NULL,NULL,NULL,NULL,
                   NULL,NULL,NULL,NULL,NULL};  // 16-bit for MacLC
CData* sd_buff_wr=NULL;
CData* img_mounted=NULL;     // 2-bit in MacLC
CData* img_readonly=NULL;
QData* img_size=NULL;


#define bitset(byte,nbit)   ((byte) |=  (1<<(nbit)))
#define bitclear(byte,nbit) ((byte) &= ~(1<<(nbit)))
#define bitflip(byte,nbit)  ((byte) ^=  (1<<(nbit)))
#define bitcheck(byte,nbit) ((byte) &   (1<<(nbit)))

// Sector-read latency, in block-device ticks, before sd_ack/data is returned.
// Models the real HPS/SD round-trip.  The original 1200 is ~25x too fast: the
// double-buffer prefetch (kicked at byte 20 of each 512-byte block) finishes
// before the block boundary, so the target's io_busy never holds REQ low there
// and the disk driver's inter-block wait loop hangs in sim while real hardware
// (slow SD) shows the REQ-low window and proceeds.  Override with
// +blkdev_latency=<n> to sweep.  Default chosen large enough that the ~492-byte
// read-ahead cannot hide it, so io_busy produces the same window as the FPGA.
// +blkdbg: trace every request start/ignore/finish on stderr
static int blkdev_dbg() {
    static int v = -1;
    if (v < 0) v = Verilated::commandArgsPlusMatch("blkdbg")[0] ? 1 : 0;
    return v;
}

static bool ignored_reported = false;

static int blkdev_read_latency() {
    static int v = -1;
    if (v < 0) {
        v = 16000;
        const char* m = Verilated::commandArgsPlusMatch("blkdev_latency=");
        if (m && m[0]) { const char* eq = strchr(m, '='); if (eq) v = atoi(eq + 1); }
        fprintf(stderr, "blkdev sector-read latency = %d ticks\n", v);
    }
    return v;
}


void SimBlockDevice::MountDisk( std::string file, int index) {
        disk[index].open(file.c_str(), std::ios::in | std::ios::out | std::ios::binary | std::ios::ate);
        if (!disk[index]) {
                disk[index].clear();
                disk[index].open(file.c_str(), std::ios::in | std::ios::binary | std::ios::ate);
        }
        if (disk[index]) {
                fprintf(stderr,"we are here\n");
           // we shouldn't do the actual mount here..
           disk_size[index]= disk[index].tellg();
        //fprintf(stderr,"mount size %ld\n",disk_size[index]);
           disk[index].seekg(0);
           mountQueue[index]=1;
           printf("disk %d inserted (%s)\n",index,file.c_str());
        }else {
                fprintf(stderr,"some kind of error: %s\n",file.c_str());
        }

}


void SimBlockDevice::BeforeEval(long long cycles)
{
//
// switch to a new disk if current_disk is -1
// check to see if we need a read or a write or a mount
//

// wait until the computer boots to start mounting, etc
 if (cycles<2000) return;

 for (int i=0; i<kVDNUM;i++)
 {

   //if (current_disk == 0)
   //fprintf(stderr,"current_disk = %d *sd_rd %x ack_delay %x reading %d writing %d\n",current_disk,*sd_rd,ack_delay,reading,writing);

    if (current_disk == i) {
    // send data - 16-bit word at a time for MacLC
    if (ack_delay==1) {
      // The real hps_io raises sd_ack and only then strobes the words, and
      // scsi_cache enters its transfer state one clock after it sees the
      // ack.  Presenting word 0 on the ack's own tick lost that word (block
      // 0's 'ER' driver-descriptor signature, so the ROM saw no Mac disk and
      // rescanned forever, 2026-09-09).  Lead the first word by one tick.
      if (reading && (*sd_buff_wr==0) &&  (bytecnt<xfer_bytes) && ack_ticks > 0) {
         // Read 2 bytes and combine into 16-bit word (a window: from the
         // block cd_window built at the request)
         int byte1 = win ? winbuf[bytecnt]     : disk[i].get();
         int byte2 = win ? winbuf[bytecnt + 1] : disk[i].get();
         *sd_buff_dout = (byte1 << 8) | (byte2 & 0xFF);
         *sd_buff_addr = bytecnt/2;  // Word address
         bytecnt += 2;
         *sd_buff_wr= 1;
         //printf("cycles %x reading %X : %X ack %x\n",cycles,*sd_buff_addr,*sd_buff_dout,*sd_ack );
      } else if(writing && bytecnt < xfer_bytes && ack_ticks > 0) {
        // Write one word per clock from the target's sector buffer. q_a is
        // synchronous, so the next address is driven after consuming this word.
        // Write 16-bit word as 2 bytes
        unsigned short word = *(sd_buff_din[i]);
        // commandArgsPlusMatch returns "" (never NULL) when the plusarg is
        // absent, so `!ptr` was always false and every write was silently
        // discarded — test the string's emptiness, not the pointer
        if (win) {
          winbuf[bytecnt]     = (word >> 8) & 0xFF;
          winbuf[bytecnt + 1] = word & 0xFF;
        }
        else if (!Verilated::commandArgsPlusMatch("ignore_scsi_writes")[0]) {
          disk[i].put((word >> 8) & 0xFF);
          disk[i].put(word & 0xFF);
        }
        bytecnt += 2;
        *sd_buff_addr = (bytecnt < xfer_bytes) ? bytecnt/2 : 0;
      } else if(writing && ack_ticks > 0 && bytecnt >= xfer_bytes) {
        // Only once every word has been taken.  The first ack tick has
        // ack_ticks == 0 and used to fall through to here, finishing every
        // write with zero bytes moved: the gate corpus wrote all-zero results
        // and the Mac OS boot's first volume write was lost, after which the
        // scsi_cache, left mid-transfer by the early ack drop, never completed
        // the next read (the ROM parked in its SCSI Manager, 2026-09-12).
        if (win) cdwin_write(win_lba, winbuf, xfer_bytes);   // the command block
        else disk[i].flush();
        *sd_buff_addr = 0;
        writing = false;
      } else if(writing) {
        // the ack's first tick, or a word the core has not consumed yet
      } else {
          *sd_buff_wr=0;

          if (reading) {
                if(bytecnt >= xfer_bytes) {
                        reading = 0;
                }
        }
      }
    } else {
          *sd_buff_wr=0;
    }
    }

    // issue a mount if we aren't doing anything, and the img_mounted has no bits set
    if (!reading && !writing && mountQueue[i] && !*img_mounted) {
fprintf(stderr,"mounting.. %d\n",i);
           mountQueue[i]=0;
           *img_size = disk_size[i];
           if (img_readonly) *img_readonly=1;
           if (i == 2) cdwin_mount((uint64_t)disk_size[i]);   // the CD slot's window device follows the disc
fprintf(stderr,"img_size .. %llu\n",(unsigned long long)*img_size);
           disk[i].seekg(0);
           bitset(*img_mounted,i);
           ack_delay=1200;
    } else if (ack_delay==1 && bitcheck(*img_mounted,i) ) {
fprintf(stderr,"mounting flag cleared  %d\n",i);
        bitclear(*img_mounted,i) ;
        //*img_size = 0;
    } else { if (!reading && !writing && ack_delay>0) ack_delay--; }

    // start reading when sd_rd pulses high
    if ((current_disk==-1 || current_disk==i) && (bitcheck(*sd_rd,i) || bitcheck(*sd_wr,i) )) {
       // set current disk here..
//fprintf(stderr,"setting current disk %d %x ack_delay %x\n",i,*sd_rd,ack_delay);
       current_disk=i;
      // a request is level-held while the latency counts down: report the
      // first held tick only, not the sixteen thousand that follow it
      if (ack_delay && blkdev_dbg() && !ignored_reported) {
        ignored_reported = true;
        fprintf(stderr, "[BLK %lld] request on %d held: ack_delay=%d reading=%d writing=%d bytecnt=%d\n",
                cycles, i, ack_delay, reading, writing, bytecnt);
      }
      if (!ack_delay) {
        int lba = *(sd_lba[i]);
        ignored_reported = false;
        if (blkdev_dbg())
          fprintf(stderr, "[BLK %lld] start %s disk %d lba=%d blk_cnt=%d\n", cycles,
                  bitcheck(*sd_rd,i) ? "read" : "write", i, lba, sd_blk_cnt ? (int)*sd_blk_cnt : 0);
        if (bitcheck(*sd_rd,i)) {
                reading = true;
        }
        if (bitcheck(*sd_wr,i)) {
                writing = true;
        }

        // A multi-block transaction (hps_io sd_blk_cnt = sectors - 1) moves
        // its sectors back to back under one ack, the buffer address running
        // on past 255: this is how the scsi_cache's 8-sector groups arrive
        // from the real Main.  Without it every group fill got one sector and
        // seven stale ones, and no image has booted in this sim since the
        // block cache landed (2026-09-07).
        xfer_bytes = (sd_blk_cnt ? ((int)*sd_blk_cnt + 1) : 1) * kBLKSZ;
        if (xfer_bytes > (int)sizeof(winbuf)) xfer_bytes = sizeof(winbuf);
        // the CD slot's windows never touch the image file
        win = (i == 2) && cdwin_is_window((unsigned int)lba);
        win_lba = (unsigned int)lba;
        if (win) {
          if (reading) cdwin_read(win_lba, winbuf, xfer_bytes);
        } else {
          disk[i].clear();
          disk[i].seekg((lba) * kBLKSZ);
          disk[i].seekp((lba) * kBLKSZ);
        }
      //  printf("seek %06X lba: (%x) (%d,%d) drive %d reading %d writing %d ack %x\n", (lba) * kBLKSZ,lba,lba,kBLKSZ,i,reading,writing,*sd_ack);
        bytecnt = 0;
        *sd_buff_addr = 0;
        ack_delay = blkdev_read_latency();
      }
    }

    if (current_disk == i) {
      int was = bitcheck(*sd_ack,i) ? 1 : 0;
      // ack_delay also paces a mount pulse; only a transfer that actually
      // started (reading/writing) may raise the ack.  A mount countdown
      // expiring while a request was merely held used to raise sd_ack for
      // nothing, release the slot, and leave the ack high forever (the
      // phase-1 CD boot: the reset notice and the CD mount coincide).
      if (ack_delay==1 && (reading || writing)) {
           bitset(*sd_ack,i);
           ack_ticks++;
           //printf("setting sd_ack: %x\n",*sd_ack);
      } else {
           bitclear(*sd_ack,i);
           ack_ticks = 0;
           //printf("clearing sd_ack: %x\n",*sd_ack);
      }
      if (blkdev_dbg() && was != (bitcheck(*sd_ack,i) ? 1 : 0))
        fprintf(stderr, "[BLK %lld] ack %s disk %d ack_delay=%d reading=%d writing=%d bytecnt=%d win=%d mount_pending=%d\n",
                cycles, was ? "fall" : "rise", i, ack_delay, reading, writing, bytecnt, win, (int)bitcheck(*img_mounted,i));
      if((ack_delay > 1) || ((ack_delay == 1) && !reading && !writing))
        ack_delay--;
      if (ack_delay==0 && !reading && !writing) {
        if (blkdev_dbg()) fprintf(stderr, "[BLK %lld] done disk %d bytecnt=%d\n", cycles, i, bytecnt);
        bitclear(*sd_ack,i);          // never hand the slot back with its ack up
        current_disk=-1;
      }
    }
  }
}

void SimBlockDevice::AfterEval()
{
}


SimBlockDevice::SimBlockDevice(DebugConsole c) {
        console = c;
        current_disk=-1;

        sd_rd = NULL;
        sd_wr = NULL;
        sd_ack = NULL;
        sd_buff_addr = NULL;
        sd_blk_cnt = NULL;
        xfer_bytes = kBLKSZ;
        ack_ticks = 0;
        sd_buff_dout = NULL;
        for (int i=0;i<kVDNUM;i++) {
           sd_lba[i] = NULL;
           sd_buff_din[i] = NULL;
           mountQueue[i]=0;
        }
        sd_buff_wr=NULL;
        img_mounted=NULL;
        img_readonly=NULL;
        img_size=NULL;
}

SimBlockDevice::~SimBlockDevice() {

}
