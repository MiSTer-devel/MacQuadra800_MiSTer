// DPI-C shim: tb_ncr53c96's synthetic block device serves the CD slot's
// windows through sim/cd_window.cpp, i.e. through the Main fork's own
// response builders and playhead.

#include <stdint.h>
#include "svdpi.h"
#include "sim/cd_window.h"

static uint8_t rbuf[4096];
static uint8_t wbuf[512];

extern "C" {

int cdwin_dpi_read(int lba, int sz)
{
	if (sz > (int)sizeof(rbuf)) sz = sizeof(rbuf);
	return cdwin_read((uint32_t)lba, rbuf, sz);
}

int cdwin_dpi_rbyte(int i)
{
	return (i >= 0 && i < (int)sizeof(rbuf)) ? rbuf[i] : 0;
}

void cdwin_dpi_wbyte(int i, int b)
{
	if (i >= 0 && i < (int)sizeof(wbuf)) wbuf[i] = (uint8_t)b;
}

void cdwin_dpi_write(int lba)
{
	cdwin_write((uint32_t)lba, wbuf, sizeof(wbuf));
}

void cdwin_dpi_mount(int bytes)
{
	cdwin_mount((uint64_t)(uint32_t)bytes);
}

}
