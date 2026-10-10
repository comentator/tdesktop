#pragma once

#include <arpa/inet.h>
#include <dispatch/dispatch.h>
#include <mach/mach.h>
#include <sys/resource.h>
#include <sys/socket.h>
#include <unistd.h>
#include <cerrno>
#include <charconv>
#include <chrono>
#include <csignal>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace Prototype {

constexpr auto kSampleRate = 16000;
constexpr auto kMaximumSamples = 30 * kSampleRate;
using Clock = std::chrono::steady_clock;

inline double Seconds(Clock::time_point start) {
	return std::chrono::duration<double>(Clock::now() - start).count();
}

inline void Quote(std::string_view text) {
	std::cout << '"';
	for (const auto ch : text) {
		switch (ch) {
		case '"': std::cout << "\\\""; break;
		case '\\': std::cout << "\\\\"; break;
		case '\n': std::cout << "\\n"; break;
		case '\r': std::cout << "\\r"; break;
		case '\t': std::cout << "\\t"; break;
		default:
			if (static_cast<unsigned char>(ch) >= 32) {
				std::cout << ch;
			}
		}
	}
	std::cout << '"';
}

inline void MemoryFields() {
	auto info = mach_task_basic_info_data_t{};
	auto count = mach_msg_type_number_t(MACH_TASK_BASIC_INFO_COUNT);
	const auto result = task_info(mach_task_self(), MACH_TASK_BASIC_INFO,
		reinterpret_cast<task_info_t>(&info), &count);
	auto usage = rusage{};
	if (result == KERN_SUCCESS && getrusage(RUSAGE_SELF, &usage) == 0) {
		std::cout << ",\"resident_bytes\":" << info.resident_size
			<< ",\"peak_resident_bytes\":" << usage.ru_maxrss;
	}
}

inline void State(const char *state, double seconds = 0.) {
	std::cout << "{\"state\":\"" << state
		<< "\",\"seconds\":" << seconds;
	MemoryFields();
	std::cout << "}" << std::endl;
}

inline void Error(const char *message) {
	std::cout << "{\"status\":\"error\",\"message\":";
	Quote(message);
	std::cout << "}" << std::endl;
}

inline void Result(
		std::string_view text,
		std::string_view language,
		double seconds,
		int calls) {
	std::cout << "{\"status\":\"ok\",\"text\":";
	Quote(text);
	std::cout << ",\"language\":";
	Quote(language);
	std::cout << ",\"seconds\":" << seconds
		<< ",\"calls\":" << calls;
	MemoryFields();
	std::cout << "}" << std::endl;
}

inline void PressureExit() {
	std::cerr << "PROTOTYPE_MEMORY_PRESSURE_EXIT" << std::endl;
	std::_Exit(75);
}

inline void MemoryPressure(void *context) {
	const auto source = reinterpret_cast<dispatch_source_t>(context);
	if (dispatch_source_get_data(source) & DISPATCH_MEMORYPRESSURE_CRITICAL) {
		PressureExit();
	}
}

inline void ObserveMemoryPressure() {
	std::signal(SIGUSR1, [](int) { _exit(75); });
	const auto source = dispatch_source_create(
		DISPATCH_SOURCE_TYPE_MEMORYPRESSURE,
		0,
		DISPATCH_MEMORYPRESSURE_CRITICAL,
		dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0));
	if (!source) {
		throw std::runtime_error("memory pressure observer unavailable");
	}
	dispatch_set_context(source, source);
	dispatch_source_set_event_handler_f(source, MemoryPressure);
	dispatch_resume(source);
}

inline int NetworkProbe() {
	const auto fd = socket(AF_INET, SOCK_STREAM, 0);
	if (fd < 0) {
		return 2;
	}
	auto address = sockaddr_in{};
	address.sin_family = AF_INET;
	address.sin_port = htons(9);
	address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
	const auto result = connect(fd,
		reinterpret_cast<const sockaddr*>(&address), sizeof(address));
	const auto error = errno;
	close(fd);
	std::cout << "{\"connect_result\":" << result
		<< ",\"errno\":" << error << "}" << std::endl;
	return (result == -1 && error == EPERM) ? 0 : 3;
}

struct Request {
	std::string header;
	std::string command;
	std::string language;
	std::vector<float> audio;
};

inline bool Read(Request &request) {
	if (!std::getline(std::cin, request.header)) {
		return false;
	}

	const auto fields = std::string_view(request.header);
	const auto first = fields.find(' ');
	request.command.assign(fields.substr(0, first));
	if (request.command == "PRESSURE") {
		PressureExit();
	} else if (request.command == "CRASH") {
		std::raise(SIGSEGV);
	} else if (request.command != "RUN") {
		return true;
	}

	auto count = 0;
	const auto second = (first == fields.npos)
		? fields.npos
		: fields.find(' ', first + 1);
	if (second == fields.npos) {
		throw std::runtime_error("missing PCM request fields");
	}
	request.language.assign(fields.substr(first + 1, second - first - 1));
	const auto number = fields.substr(second + 1);
	const auto parsed = std::from_chars(
		number.data(), number.data() + number.size(), count);
	if (parsed.ec != std::errc()
		|| parsed.ptr != number.data() + number.size()
		|| count <= 0
		|| count > kMaximumSamples) {
		throw std::runtime_error("invalid or oversized PCM request");
	}
	request.audio.resize(count);
	std::cin.read(reinterpret_cast<char*>(request.audio.data()),
		count * sizeof(float));
	if (!std::cin) {
		throw std::runtime_error("truncated PCM request");
	}
	return true;
}

} // namespace Prototype
