"""Check the proposed uq1 write rule at the abstract FIFO level, not RTL.

The producer emits only when occupancy != 2 (useq.room_out). Compare the
current assignments with leaving uq0/count intact and writing uq1 on every
emit. Differences in an invalid slot are allowed. This does not replace a
CPU regression or formal proof of the actual implementation.
"""
from collections import deque
import json

initial = (0, 0, 0, 0, 0)  # occupancy, old slot0/1, proposed slot0/1
seen = {initial}
pending = deque([initial])
transitions = 0
while pending:
    count, old0, old1, new0, new1 = pending.popleft()
    assert [old0, old1][:count] == [new0, new1][:count]
    for pop in (False, True):
        for value in (None, 0, 1, 2):
            emit = value is not None
            if count == 2 and emit:
                continue
            if pop and count:
                next_old0 = value if emit and count == 1 else old1
                next_old1 = value if emit and count == 2 else old1
                next_count = count if emit else count - 1
                next_new0 = value if emit and count == 1 else new1
            else:
                next_old0 = value if emit and count == 0 else old0
                next_old1 = value if emit and count == 1 else old1
                next_count = count + 1 if emit else count
                next_new0 = value if emit and count == 0 else new0
            next_new1 = value if emit else new1
            state = (next_count, next_old0, next_old1, next_new0, next_new1)
            transitions += 1
            assert [next_old0, next_old1][:next_count] == [next_new0, next_new1][:next_count]
            if state not in seen:
                seen.add(state)
                pending.append(state)

print(json.dumps({
    "result": "PASS",
    "scope": "abstract FIFO valid contents; not RTL/formal equivalence",
    "reachable_paired_states": len(seen),
    "transitions": transitions,
    "flush": "Both queues return to initial state",
}, indent=2))
