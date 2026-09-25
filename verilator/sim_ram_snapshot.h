#ifndef SIM_RAM_SNAPSHOT_H
#define SIM_RAM_SNAPSHOT_H
#include <cstdio>
#include <cstddef>
#include <cstdint>
// Emit guest byte order independently of host endianness. Read-only access.
template<class Words>
bool write_guest_ram(FILE* file, const Words& ram, size_t bytes) {
    if (!file || bytes % 4) return false;
    unsigned char block[4096];
    for (size_t offset = 0; offset < bytes;) {
        const size_t count = bytes-offset < sizeof(block) ? bytes-offset : sizeof(block);
        for (size_t i=0; i<count; i+=4) {
            const uint32_t word = ram[(offset+i)/4];
            block[i]=word>>24; block[i+1]=word>>16;
            block[i+2]=word>>8; block[i+3]=word;
        }
        if (fwrite(block,1,count,file)!=count) return false;
        offset += count;
    }
    return !ferror(file);
}
#endif
