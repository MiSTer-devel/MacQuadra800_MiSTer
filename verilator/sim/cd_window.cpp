// CD-slot windows for the sims (see cd_window.h).  Keep in step with
// mac_cdrom_window_fill / mac_cdrom_command in the Main fork.

#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include "cd_window.h"
#include "mac_cdrom_resp.h"
#include "mac_cdrom_play.h"

#define TOC_BLK    0x7FFF0000u
#define AUDIO_BLK  0x40000000u
#define FRAME_BLK  0x7C000000u
#define CMD_BLK    0x7D000000u
#define RESP_BLK   0x7E000000u
#define CMD_CDB    496

static mac_cd_toc  toc;
static int         active;
static uint32_t    last_sectors;
static mac_cd_play play;
static int         inited;

static mac_cd_play *P(void)
{
	if (!inited) { mac_cd_play_init(&play); inited = 1; }
	return &play;
}

void cdwin_mount(uint64_t bytes)
{
	P();
	memset(&toc, 0, sizeof(toc));
	active = (bytes != 0);
	if (active)
	{
		toc.n        = 1;
		toc.ctrl[0]  = 0x14;
		toc.start[0] = 0;
		toc.leadout  = (uint32_t)(bytes / 2048);
		toc.data_trk = 0;
		last_sectors = toc.leadout;
	}
	mac_cd_play_set_toc(P(), active ? &toc : NULL);
}

int cdwin_is_window(uint32_t lba)
{
	return lba >= AUDIO_BLK;
}

int cdwin_read(uint32_t lba, uint8_t *buf, int sz)
{
	mac_cd_play *p = P();
	memset(buf, 0, sz);

	if (lba >= TOC_BLK && lba < TOC_BLK + 2)
	{
		if (active)
		{
			uint8_t blob[1024];
			mac_cd_build_blob(&toc, blob);
			memcpy(buf, blob + (lba - TOC_BLK) * 512, (sz < 512) ? sz : 512);
		}
		return 1;
	}

	if (lba >= RESP_BLK && lba < RESP_BLK + 0x01000000u)
	{
		if (sz < 512) return 1;
		uint8_t op = (uint8_t)(lba >> 16), a = (uint8_t)(lba >> 8), b = (uint8_t)lba;
		const mac_cd_toc *t = active ? &toc : NULL;
		mac_cd_pos pos;
		switch (op)
		{
		case 0x12: mac_cd_resp_inquiry(buf); break;
		case 0x1A: mac_cd_resp_mode_sense(a & 0x3F, last_sectors - 1, p->ports, buf); break;
		case 0x43: if (t) mac_cd_resp_toc_43(t, a, b, buf); break;
		case 0xC1: if (t) mac_cd_resp_toc_c1(t, a, b, buf); break;
		case 0x42: mac_cd_play_pos(p, &pos); mac_cd_resp_subch(&pos, a, b, buf); break;
		case 0xC2: mac_cd_play_pos(p, &pos); mac_cd_resp_subq(&pos, buf); break;
		case 0xCC: mac_cd_play_pos(p, &pos); mac_cd_resp_astat(&pos, a, buf);
		           if (getenv("CDWIN_TRACE")) fprintf(stderr, "[CDWIN] astat a=%d -> ast=%d state=%d cur=%u\n", a, pos.ast, p->state, p->cur);
		           break;
		default: break;
		}
		return 1;
	}

	if (lba == FRAME_BLK)
	{
		if (sz < 2358) return 1;
		uint32_t flba = 0;
		int have = mac_cd_play_frame(p, &flba);      // a flat data disc: silence, but the state is real
		buf[2352] = mac_cd_play_ast(p);
		buf[2353] = (uint8_t)have;
		buf[2354] = (uint8_t)p->flush_gen;         buf[2355] = (uint8_t)(p->flush_gen >> 8);
		buf[2356] = (uint8_t)(p->flush_gen >> 16); buf[2357] = (uint8_t)(p->flush_gen >> 24);
		return 1;
	}

	if (lba >= AUDIO_BLK) return 1;    // raw audio window (old-style fetch): silence
	return 0;
}

void cdwin_write(uint32_t lba, const uint8_t *buf, int sz)
{
	if (sz < 512 || lba < CMD_BLK || lba >= RESP_BLK) return;
	mac_cd_play *p = P();
	uint8_t op = (uint8_t)(lba >> 16);
	const uint8_t *cdb = buf + CMD_CDB;
	if (getenv("CDWIN_TRACE"))
		fprintf(stderr, "[CDWIN] command op=%02x cdb=%02x %02x %02x %02x %02x %02x %02x %02x %02x %02x state=%d\n", op,
		        cdb[0], cdb[1], cdb[2], cdb[3], cdb[4], cdb[5], cdb[6], cdb[7], cdb[8], cdb[9], p->state);
	switch (op)
	{
	case 0xFF: mac_cd_play_init(p); break;
	case 0xFE: mac_cd_play_stop(p); break;
	case 0x1B: case 0xC0: mac_cd_play_stop(p); break;
	case 0x15: mac_cd_play_command(p, cdb, buf, cdb[4]); break;
	case 0x1E: case 0xBB: case 0xCE: break;
	default:   mac_cd_play_command(p, cdb, NULL, 0); break;
	}
}
