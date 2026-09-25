#include "../cpu_dispatch_observer.h"
#include <cassert>
#include <cstdio>

// Replay the production sampling order: observe every post-eval rising edge,
// process profile requests only outside reset, then gate consumers. PC/state
// are deliberately fixed: neither is an event discriminator anymore.
struct Replay {
	CpuDispatchObserver observer;
	CpuProfileGate profile;
	unsigned cycles = 0, opcodes = 0, traces = 0, dumps = 0;
	bool pending_start = false, pending_stop = false;
	void edge(bool reset, bool toggle, bool trace_enabled,
	          bool start = false, bool stop = false) {
		pending_start |= start;
		pending_stop |= stop;
		const bool dispatch = observer.sample(reset, toggle);
		if (reset) return;
		const auto action = profile.sample(pending_start, pending_stop);
		pending_start = pending_stop = false;
		if (action == CpuProfileGate::Start) cycles = opcodes = 0;
		if (action == CpuProfileGate::Start || action == CpuProfileGate::Count) {
			++cycles;
			if (dispatch) ++opcodes;
		}
		if (action == CpuProfileGate::Stop) ++dumps;
		if (trace_enabled && dispatch) ++traces;
	}
};

int main() {
	// Attaching with a high toggle is not itself a dispatch.
	CpuDispatchObserver attached;
	assert(!attached.sample(false, true));
	assert(!attached.sample(false, true));
	assert(attached.sample(false, false));
	// Reset-induced toggle changes do not appear as opcodes. A real opcode
	// on the first nonreset sample is retained after a reset baseline.
	assert(!attached.sample(true, true));
	assert(!attached.sample(true, false));
	assert(attached.sample(false, true));

	Replay r;
	r.edge(true, false, false);
	r.edge(false, false, false, true); // start at an idle/stalled opcode
	assert(r.cycles == 1 && r.opcodes == 0 && r.traces == 0);
	r.edge(false, true, true);        // same PC and state 190
	r.edge(false, false, true);       // same PC and state 190, next opcode load
	r.edge(false, true, true);        // same PC and state 190, next opcode load
	assert(r.opcodes == 3 && r.traces == 3);
	for (int i = 0; i < 4; ++i) r.edge(false, true, true); // ce=0: toggle holds
	assert(r.opcodes == 3 && r.traces == 3 && r.cycles == 8);
	r.edge(false, false, true, false, true); // stop excludes current event
	assert(r.opcodes == 3 && r.traces == 4 && r.dumps == 1 && r.cycles == 8);
	r.edge(false, true, false);        // disabled consumers still observed
	r.edge(false, true, true, true);   // reenable/start does not replay it
	assert(r.opcodes == 0 && r.traces == 4 && r.cycles == 1);
	r.edge(false, false, true, true);  // restart includes current real event
	assert(r.opcodes == 1 && r.cycles == 1 && r.traces == 5);
	r.edge(false, true, true, true, true); // simultaneous requests: start wins
	assert(r.opcodes == 1 && r.cycles == 1 && r.traces == 6 && r.dumps == 1);
	// Active profile spans reset without counting reset clocks/events.
	r.edge(true, false, true);
	r.edge(true, false, true);
	r.edge(false, false, true);
	assert(r.opcodes == 1 && r.cycles == 2 && r.traces == 6);
	r.edge(false, true, true);
	assert(r.opcodes == 2 && r.traces == 7);
	// Requests during reset are applied at the next nonreset sample.
	r.edge(true, false, true, false, true);
	r.edge(false, true, true);
	assert(r.opcodes == 2 && r.traces == 8 && r.dumps == 2);
	r.edge(false, false, false);       // odd number of unobserved-by-output events
	r.edge(true, false, false, true);
	r.edge(false, false, true);        // new bracket: no stale event
	assert(r.opcodes == 0 && r.cycles == 1 && r.traces == 8);
	r.edge(false, true, true);
	assert(r.opcodes == 1 && r.traces == 9);
	r.profile.stop();
	assert(!r.profile.active());
	std::puts("PASS: dispatch reset/stalls/same-PC-state and profile/trace boundaries");
}
