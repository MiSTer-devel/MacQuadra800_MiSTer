import sys
# Disassemble guest-RAM dumps made with gdump.py (run from the directory holding
# g_hi.bin / g_3c.bin / g_4e.bin / g_low.bin and the PC histogram; edit IMG).
from capstone import *
md=Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN|CS_MODE_M68K_040)
def load(name, base): return open(name,'rb').read(), base
IMG=[load('g_hi.bin',0x07890000), load('g_3c.bin',0x003C0000), load('g_4e.bin',0x004E0000), load('g_low.bin',0)]
hot={}
for l in open('dott_hang_pcs_0919.txt'):
    p=l.split()
    if len(p)==2 and len(p[0])==8:
        try: hot[int(p[0],16)]=int(p[1])
        except: pass
def dis(a0,a1):
    for d,b in IMG:
        if b<=a0<b+len(d):
            for ins in md.disasm(d[a0-b:a1-b],a0):
                h=hot.get(ins.address,'')
                print('%08x %6s  %-10s %s'%(ins.address,h,ins.mnemonic,ins.op_str))
            return
for r in sys.argv[1:]:
    a,b=[int(x,16) for x in r.split('-')]
    print('----',r); dis(a,b)
