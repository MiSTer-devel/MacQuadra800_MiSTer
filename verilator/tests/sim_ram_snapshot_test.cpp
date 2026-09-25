#include "../sim_ram_snapshot.h"
#include <array>
#include <cassert>
int main() {
    std::array<uint32_t,1025> ram{};
    ram[0]=0x12345678;ram[1024]=0x89abcdef;
    FILE* f=tmpfile();assert(f);
    assert(!write_guest_ram(f,ram,3));
    assert(write_guest_ram(f,ram,4100));
    assert(ftell(f)==4100); rewind(f);
    assert(fgetc(f)==0x12 && fgetc(f)==0x34 && fgetc(f)==0x56 && fgetc(f)==0x78);
    fseek(f,4096,SEEK_SET);
    assert(fgetc(f)==0x89 && fgetc(f)==0xab && fgetc(f)==0xcd && fgetc(f)==0xef);
    assert(ram[0]==0x12345678 && ram[1024]==0x89abcdef);
    fclose(f); puts("PASS guest RAM snapshot byte order, chunk boundary, unchanged source");
}
