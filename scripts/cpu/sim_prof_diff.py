import re,sys
blocks=[];cur=None
for l in open(sys.argv[1],errors='replace'):
    m=re.match(r'\[PROF\] (\d+) cycles, (\d+) dispatches',l)
    if m: cur={'cyc':int(m.group(1)),'disp':int(m.group(2)),'st':{},'x':{}}; blocks.append(cur); continue
    if cur is None: continue
    m=re.match(r'\[PROF\]\s+state\s+(\d+): (\d+)',l)
    if m: cur['st'][int(m.group(1))]=int(m.group(2)); continue
    m=re.match(r'\[PROF\]\s+(S_M.. by .*?|acceptance-cycle hits|S_FETCH|data reads by region.*?|data writes by region.*?):(.*)',l)
    if m: cur['x'][m.group(1)]=m.group(2).strip()
print(len(blocks),'blocks; last cycles',blocks[-1]['cyc'])
a=blocks[int(len(blocks)*float(sys.argv[2]))]; b=blocks[-1]
tot=b['cyc']-a['cyc']
print('bracket %d..%d = %d cycles, S_DECODE entries %d'%(a['cyc'],b['cyc'],tot,b['disp']-a['disp']))
names={3:'S_FETCH',4:'S_DECODE',8:'S_IMMF',9:'S_MRD',10:'S_MWR',20:'S_PIPE_START',21:'S_PIPE_SREG',22:'S_PIPE_SRD',23:'S_PIPE_SDONE',24:'S_PIPE_DST',25:'S_PIPE_DREG',26:'S_PIPE_DEA',27:'S_PIPE_DDONE',28:'S_EXEC',29:'S_SHIFT',190:'S_PIPE_REGS',51:'S_BCC_EXT',53:'S_DBCC1',48:'S_RET1',49:'S_RET2',70:'S_MOVEM_LOOP',71:'S_MOVEM_RD',5:'S_NEXT',11:'S_EA_DISP',12:'S_EA_BASE',13:'S_EA_D16',14:'S_EA_EXTW',7:'S_STOPPED',56:'S_JSR1',55:'S_JMP1',58:'S_LEA1',61:'S_LINK1',65:'S_UNLK1'}
d={k:b['st'].get(k,0)-a['st'].get(k,0) for k in b['st']}
for k,v in sorted(d.items(),key=lambda kv:-kv[1])[:22]:
    print('  %-14s %12d  %5.1f %%'%(names.get(k,'state %d'%k),v,100.0*v/tot))
for k in b['x']: print(' ',k,'| last:',b['x'][k][:150]); print(' ',' '*len(k),'| base:',a['x'].get(k,'')[:150])
