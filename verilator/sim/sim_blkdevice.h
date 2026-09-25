#pragma once
#include <iostream>
#include <fstream>
#include "verilated.h"
#include "sim_console.h"


#ifndef _MSC_VER
#else
#define WIN32
#endif

#define kVDNUM 10
#define kBLKSZ 512

struct SimBlockDevice {
public:

	IData* sd_lba[kVDNUM];
	CData* sd_rd;           // 2-bit in MacLC
	CData* sd_wr;           // 2-bit in MacLC
	CData* sd_ack;          // 2-bit in MacLC
	CData* sd_blk_cnt;      // 6-bit: sectors - 1 per transaction (hps_io sd_blk_cnt); NULL = always one sector
	SData* sd_buff_addr;    // 13-bit like hps_io (was 8-bit for MacLC)
	SData* sd_buff_dout;    // 16-bit for MacLC
	SData* sd_buff_din[kVDNUM];  // 16-bit for MacLC
	CData* sd_buff_wr;
	CData* img_mounted;     // 2-bit in MacLC
	CData* img_readonly;
	QData* img_size;

	int bytecnt;
	int ack_ticks;          // ticks since sd_ack rose: the first word is strobed one tick after the ack, as hps_io does
	int xfer_bytes;         // bytes in the current transaction: (sd_blk_cnt + 1) * kBLKSZ
        long int disk_size[kVDNUM];
	bool reading;
	bool writing;
	int ack_delay;
	int current_disk;
	bool mountQueue[kVDNUM];
	std::fstream disk[kVDNUM];

	// The CD slot's windows (LBA >= 0x40000000 on disk 2) are served by
	// sim/cd_window.cpp -- the Main fork's builders -- not by the image file.
	bool win;
	unsigned int win_lba;
	unsigned char winbuf[4096];

	// cycles is the sim's half-cycle counter: must be 64-bit — an int
	// wraps negative at 2^31 (~1.07G machine cycles) and the <2000 boot
	// guard then disables the block device forever, mid-transfer
	void BeforeEval(long long cycles);
	void AfterEval(void);
	//void QueueDownload(std::string file, int index);
	//void QueueDownload(std::string file, int index, bool restart);
	//bool HasQueue();
	void MountDisk( std::string file, int index);

	SimBlockDevice(DebugConsole c);
	~SimBlockDevice();


private:
	//std::queue<SimBus_DownloadChunk> downloadQueue;
	//SimBus_DownloadChunk currentDownload;
	//void SetDownload(std::string file, int index);
};
