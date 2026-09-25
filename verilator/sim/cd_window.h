// The optimized core's CD-slot windows, served the way the Main fork serves
// them (../Main_MiSTer/support/mac/mac_cdrom.cpp: mac_cdrom_window_fill and
// mac_cdrom_command) over the very builders and playhead Main compiles
// (mac_cdrom_resp.cpp, mac_cdrom_play.cpp), so the sim and the box serve
// identical bytes.  Discs here are flat data images: one 2048-byte-sector
// track, no audio, which is what the sim mounts.
//
// Used by tb_ncr53c96 (through the DPI-C shim in ../cd_win_dpi.cpp) and by
// the full-machine block-device model (sim_blkdevice.cpp).

#ifndef CD_WINDOW_H
#define CD_WINDOW_H

#include <stdint.h>

void cdwin_mount(uint64_t image_bytes);                   // 0 = no disc
int  cdwin_is_window(uint32_t lba);                       // at/above the CD-DA window: never the image file
int  cdwin_read(uint32_t lba, uint8_t *buf, int sz);      // 1 = served (blob, response, frame, raw audio); 0 = data window
void cdwin_write(uint32_t lba, const uint8_t *buf, int sz);   // the command block

#endif
