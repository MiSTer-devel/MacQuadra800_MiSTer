#include "../sim_control.h"
#include <cassert>
#include <cstdio>
#include <cstdlib>

static void feed(SimControl& control, const std::string& text) {
	assert(control.feed(text.data(), text.size()) == text.size());
}

int main() {
    {
        SimControl dumps; SimControlCommand cmd{};
        feed(dumps,"ramdump 0\nramdump 129\nramdump -1\nramdump 8 extra\nramdump 8\n");
        assert(dumps.rejected()==4);
        assert(dumps.step(false,true,cmd));
        assert(cmd.kind==SimControlCommand::RamDump && cmd.value==8);
    }

    {
        SimControl quit_control;
        SimControlCommand quit_command{};
        feed(quit_control, "quit extra\nquit\n");
        assert(quit_control.rejected() == 1);
        assert(quit_control.step(false, true, quit_command));
        assert(quit_command.kind == SimControlCommand::Quit);
    }

	SimControl c;
	SimControlCommand command{};
	assert(!c.enabled() && !c.step(false, true, command)); // opt-in, idle by default
	feed(c, "# comment\n\r\ndown 0x1c");
	assert(c.queued() == 0); // incomplete lines never execute
	feed(c, "\r\nup 1C\ndown 75 ext # arrow\nprofile start\nprofile stop\nshot\n");
	assert(c.queued() == 6 && c.rejected() == 0);
	assert(!c.step(true, true, command));  // reset blocks guest commands
	assert(!c.step(false, false, command)); // existing PS/2 queue/timer owns input
	assert(c.step(false, true, command) && command.kind == SimControlCommand::Down && command.value == 0x1c && !command.extended);
	assert(c.step(false, true, command) && command.kind == SimControlCommand::Up && command.value == 0x1c);
	assert(c.step(false, true, command) && command.extended && command.value == 0x75);
	assert(c.step(false, true, command) && command.kind == SimControlCommand::ProfileStart);
	assert(c.step(false, true, command) && command.kind == SimControlCommand::ProfileStop);
	assert(c.step(false, true, command) && command.kind == SimControlCommand::Shot);
	feed(c, "wait 3\ndown 5a\nwait 0\nup 5a\n");
	assert(!c.step(true, true, command)); // screenshot/reset pause keeps order
	assert(c.step(false, true, command) && command.kind == SimControlCommand::Wait);
	assert(!c.step(false, true, command));
	assert(!c.step(true, true, command)); // paused clocks do not consume wait
	assert(!c.step(false, true, command));
	assert(!c.step(false, true, command));
	assert(c.step(false, true, command) && command.kind == SimControlCommand::Down);
	assert(c.step(false, true, command) && command.kind == SimControlCommand::Wait);
	assert(c.step(false, true, command) && command.kind == SimControlCommand::Up);
	feed(c, "down 100\nup -1\nwait -2\nwait 18446744073709551616\ndown 1c extra\nshot file.png\nprofile end\nwait 1 extra\n");
	assert(c.rejected() == 8 && c.queued() == 0);
	feed(c, std::string(161, 'x') + "down 1c\nshot\n");
	assert(c.rejected() == 9 && c.queued() == 1); // long-line suffix cannot execute
	assert(c.step(false, true, command) && command.kind == SimControlCommand::Shot);

	// Backpressure returns exactly the unconsumed suffix; no commands drop.
	std::string many;
	for (unsigned i = 0; i < 100; ++i) many += "wait " + std::to_string(i) + "\n";
	SimControl bounded;
	size_t consumed = bounded.feed(many.data(), many.size());
	assert(consumed < many.size() && bounded.queued() == SimControl::QueueLimit);
	for (unsigned expected = 0; expected < 100; ++expected) {
		while (!bounded.step(false, true, command)) {}
		assert(command.kind == SimControlCommand::Wait && command.value == expected);
		if (consumed < many.size())
			consumed += bounded.feed(many.data() + consumed, many.size() - consumed);
	}
	assert(consumed == many.size() && bounded.queued() == 0);

#ifndef _WIN32
	char fixture[] = "/tmp/ap040-control-test.XXXXXX";
	assert(::mkdtemp(fixture));
	const std::string fifo = std::string(fixture) + "/commands.fifo";
	const std::string file = std::string(fixture) + "/commands.txt";
	assert(::mkfifo(fifo.c_str(), 0600) == 0);
	std::string error;
	{
		SimControl reader;
		assert(reader.open(fifo, error)); // returns with no writer present
		reader.poll(); assert(reader.queued() == 0);
		int writer = ::open(fifo.c_str(), O_WRONLY | O_NONBLOCK);
		assert(writer >= 0 && ::write(writer, "down 1c", 7) == 7);
		reader.poll(); assert(reader.queued() == 0);
		assert(::write(writer, "\nwait 3\n", 8) == 8);
		::close(writer); reader.poll(); assert(reader.queued() == 2);
		writer = ::open(fifo.c_str(), O_WRONLY | O_NONBLOCK);
		assert(writer >= 0 && ::write(writer, "up 1c\n", 6) == 6);
		::close(writer); reader.poll(); assert(reader.queued() == 3);
		assert(reader.step(false, true, command) && command.kind == SimControlCommand::Down);
		assert(reader.step(false, true, command) && command.kind == SimControlCommand::Wait);
		for (int i = 0; i < 3; ++i) assert(!reader.step(false, true, command));
		assert(reader.step(false, true, command) && command.kind == SimControlCommand::Up);
	}
	{
		int writer = ::open(file.c_str(), O_CREAT | O_EXCL | O_WRONLY, 0600);
		assert(writer >= 0 && ::write(writer, "shot\n", 5) == 5);
		::close(writer);
		SimControl reader;
		assert(reader.open(file, error)); reader.poll();
		assert(reader.step(false, true, command) && command.kind == SimControlCommand::Shot);
		reader.poll(); assert(reader.queued() == 0); // EOF does not replay
		writer = ::open(file.c_str(), O_WRONLY | O_APPEND);
		assert(writer >= 0 && ::write(writer, "profile start\n", 14) == 14);
		::close(writer); reader.poll();
		assert(reader.step(false, true, command) && command.kind == SimControlCommand::ProfileStart);
		assert(!reader.open(fixture, error)); // reject directories/devices
	}
	assert(::unlink(fifo.c_str()) == 0 && ::unlink(file.c_str()) == 0);
	assert(::rmdir(fixture) == 0);
#endif
	std::puts("PASS: optional control parser, bounds, pacing, FIFO reconnect and file append");
}
