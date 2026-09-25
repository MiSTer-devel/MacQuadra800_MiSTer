#!/usr/bin/env python3
"""audit_task_sites.py CORE.v TASK -- same-path audit for hoisting a task out of
the sequencer's state case.

Before a task that is expanded at many call sites (fetch_next, mrd/mwr, exc,
immf, go_pc, decode_dbcc_brf) is turned into a carrier whose body runs once
after the case statement, every call site must be checked: a nonblocking
write, on the same execution path AFTER the call, to any register the task
writes would have overridden the task's write in the inlined form and is
overridden by it in the hoisted form.  This walks each call site forward
through its block structure (continuing past inner block ends, skipping
sibling else/case branches) and reports such writes, calls to other tasks
that write those registers, and reads of the block's blocking carriers.
Reported sites need reading by eye: sibling-branch artefacts still slip
through where an else-if chain follows a single-statement if, and a hit on
apply_record_decode means the decode record supersedes the body on that
opcode (see the xgo cancel in apply_record_decode).  The simulation gates
(scripts/cpu_gates_wsl.sh) are the arbiter.
"""
import re,sys
src=open(sys.argv[1],encoding='utf-8',errors='replace').read()
callee=sys.argv[2]
lines=[l.split('//')[0].rstrip('\r') for l in src.split('\n')]
def task_body(name):
    i=[k for k,l in enumerate(lines) if re.match(r'\s*task '+name+r'\s*;',l)][0]
    j=i
    while not lines[j].strip().startswith('endtask'): j+=1
    return '\n'.join(lines[i:j])
tasknames=set(re.findall(r'^\s*task ([a-zA-Z_0-9]+)\s*;','\n'.join(lines),re.M))
def writes_of(name,seen=None):
    seen=seen if seen is not None else set()
    if name in seen or name not in tasknames: return set()
    seen.add(name); b=task_body(name)
    w=set(m.group(1) for m in re.finditer(r'\b([a-zA-Z_][a-zA-Z0-9_]*)(\[[^\]]*\])?\s*(<=|=)(?!=)',b))
    for m in re.finditer(r'\b([a-z_][a-z0-9_]*)\s*(\(|;)',b):
        if m.group(1) in tasknames: w|=writes_of(m.group(1),seen)
    return w
noise={'if','else','begin','end','case','input','reg','integer','i','w','ok','line_hit','refill_hit','a','s','vec','fmt','spc','addr','size','ret','d','n','mode','rn','t','taken','c','cnt'}
written=writes_of(callee)-noise
carriers={'epf_flushed','epf_issue','epf_pop','rd_queue_pop','brf_seed_req','brf_seed_n','brf_seed_a','epf_fillw','retire_req'}
main_start=[k for k,l in enumerate(lines) if l.startswith('always @(posedge clk) begin')][1]
end_case=[k for k,l in enumerate(lines) if l.startswith('\t\tendcase') and k>main_start][0]
arm_labels=[k for k,l in enumerate(lines) if re.match(r'\t\t\tS_[A-Z0-9_]+\s*:',l) and main_start<k<end_case]
sites=[k for k,l in enumerate(lines) if re.search(r'(^|[^a-zA-Z_])'+callee+r'\s*(;|\()',l) and main_start<k<end_case]
label=re.compile(r"^\s*(default|[0-9a-zA-Z_'`{}\[\],\s]+)\s*:(?!=)")
def is_label(t): return bool(label.match(t)) and not re.match(r'\s*(if|for|while)\b',t.strip())
def opens(t): return len(re.findall(r'\b(begin|case|casez|casex)\b',t))
def closes(t): return len(re.findall(r'\b(end|endcase)\b',t))
def skip_stmt(k):
    """skip one statement/block starting at line k (an else branch or a case item body); return next line"""
    t=lines[k]; st=t.strip()
    # remove leading 'else' / 'end else'
    body=re.sub(r'^\s*(end\s+)?else\s*','',t)
    d=opens(body)-closes(body)
    if d<=0 and (';' in body or body.strip()=='' ): return k+1 if ';' in body or d<0 else k+1
    k+=1
    while d>0 and k<end_case:
        d+=opens(lines[k])-closes(lines[k]); k+=1
    return k
print(f"{callee}: {len(sites)} sites; writes {len(written)} regs")
flagged=0
for s in sites:
    arm_end=min([a for a in arm_labels if a>s]+[end_case])
    l=lines[s]; after=l.split(callee,1)[1]; after=re.sub(r'^\s*\([^)]*\)','',after)
    after=after.split(';',1)[1] if ';' in after else ''
    path=[after]; depth=0; k=s+1
    while k<arm_end:
        t=lines[k]; st=t.strip()
        if not st: k+=1; continue
        if depth==0:
            if re.match(r'(end\s+)?else\b',st):
                k=skip_stmt(k); continue            # alternative branch of the if we came from
            if re.match(r'end\b',st) and not re.match(r'endcase',st):
                depth-=1; k+=1                       # leave the enclosing block: continue outside it
                # an 'end else' handled above; a bare end followed by else on the next line:
                if k<arm_end and re.match(r'\s*else\b',lines[k]): k=skip_stmt(k)
                depth=0; continue
            if re.match(r'endcase',st):
                depth-=1; k+=1; depth=0; continue    # leave the enclosing case: continue after it
            if is_label(t):
                # a sibling case item: skip to the enclosing endcase
                d=0
                while k<arm_end:
                    d+=opens(lines[k])-closes(lines[k])
                    if d<0: break
                    k+=1
                k+=1; depth=0; continue
        d=opens(t)-closes(t)
        if re.match(r'end',st):   # 'end' closes first
            depth-=closes(t)
            if depth<0: depth=0
            depth+=opens(t)
        else: depth+=d
        if depth<0: depth=0
        path.append(t); k+=1
    text='\n'.join(path)
    hits=set(m.group(1) for m in re.finditer(r'\b([a-zA-Z_][a-zA-Z0-9_]*)(\[[^\]]*\])?\s*(<=|=)(?!=)',text) if m.group(1) in written)
    hits|=set(m.group(1)+'()' for m in re.finditer(r'\b([a-z_][a-z0-9_]*)\s*(\(|;)',text) if m.group(1) in tasknames and m.group(1)!=callee and (writes_of(m.group(1))&written))
    reads=set(c for c in carriers if re.search(r'\b'+c+r'\b',text))
    if hits or reads:
        flagged+=1
        arm=[a for a in arm_labels if a<=s][-1]
        print("  line %d (%s): later writes %s; carrier reads %s" % (s+1, re.match(r'\s*(S_[A-Z0-9_]+)',lines[arm]).group(1), sorted(hits), sorted(reads)))
print("flagged:",flagged)
