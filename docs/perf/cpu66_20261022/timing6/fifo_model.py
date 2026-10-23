"""Exhaust the two-slot rewrite with three representative payload values."""
from collections import deque
import json
# count, old_head, old_tail, bank0, bank1, read_ptr, write_ptr
initial=(0,0,0,0,0,0,0)
seen={initial};pending=deque([initial]);transitions=0
while pending:
 state=pending.popleft()
 n,h,t,b0,b1,r,w=state
 banks=[b0,b1]
 assert n==0 or h==banks[r]
 assert n<2 or t==banks[1-r]
 for emit in (0,1):
  for pop in (0,1):
   for flush in (0,1):
    for exc_go in (0,1):
     if emit and (n==2 or flush or exc_go):continue
     for value in range(3):
      take=pop and n!=0
      oh=(value if emit and n==1 else t) if take else (value if emit and n==0 else h)
      ot=value if emit else t
      nn=n+emit-take
      nb=banks.copy();nr=r^take;nw=w^emit
      if emit:nb[w]=value
      if flush or exc_go:nn=0;nr=0;nw=0
      out=(nn,oh,ot,nb[0],nb[1],nr,nw)
      assert 0<=nn<=2
      assert nn==0 or oh==nb[nr]
      assert nn<2 or ot==nb[1-nr]
      transitions+=1
      if out not in seen:seen.add(out);pending.append(out)
print(json.dumps(dict(result='PASS',reachable_paired_states=len(seen),transitions=transitions,payload_values=3)))
