#include "common.hpp"
#include <atomic>
#include <fcntl.h>
#include <thread>

namespace {

void ReadFile(const char *name, const char *path) {
	const auto fd = open(path, O_RDONLY | O_NOFOLLOW);
	const auto openError = (fd < 0) ? errno : 0;
	auto byte = char(0);
	const auto count = (fd < 0) ? ssize_t(-1) : read(fd, &byte, 1);
	const auto readError = (fd >= 0 && count < 0) ? errno : 0;
	if (fd >= 0) {
		close(fd);
	}
	std::cout << '"' << name << "\":{\"opened\":"
		<< (fd >= 0 ? "true" : "false") << ",\"read\":"
		<< (count == 1 ? "true" : "false")
		<< ",\"open_errno\":" << openError
		<< ",\"read_errno\":" << readError << '}';
}

int Files(char **paths) {
	std::cout << '{';
	ReadFile("model", paths[0]);
	std::cout << ',';
	ReadFile("managed", paths[1]);
	std::cout << ',';
	ReadFile("denied", paths[2]);
	const auto fd = open(paths[3], O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW, 0600);
	const auto openError = (fd < 0) ? errno : 0;
	const auto byte = char(0);
	const auto count = (fd < 0) ? ssize_t(-1) : write(fd, &byte, 1);
	const auto writeError = (fd >= 0 && count < 0) ? errno : 0;
	if (fd >= 0) {
		close(fd);
		unlink(paths[3]);
	}
	std::cout << ",\"write\":{\"opened\":"
		<< (fd >= 0 ? "true" : "false") << ",\"wrote\":"
		<< (count == 1 ? "true" : "false")
		<< ",\"open_errno\":" << openError
		<< ",\"write_errno\":" << writeError << "}}" << std::endl;
	return 0;
}

struct PressureContext {
	dispatch_source_t source = nullptr;
	dispatch_semaphore_t canceled = nullptr;
	std::atomic<unsigned long> bits{0};
	std::atomic<unsigned int> callbacks{0};
};

void PressureEvent(void *opaque) {
	auto &context = *static_cast<PressureContext*>(opaque);
	context.bits.fetch_or(dispatch_source_get_data(context.source));
	context.callbacks.fetch_add(1);
}

void PressureCanceled(void *opaque) {
	dispatch_semaphore_signal(static_cast<PressureContext*>(opaque)->canceled);
}

int Pressure(int seconds) {
	const auto started = Prototype::Clock::now();
	auto context = PressureContext();
	const auto queue = dispatch_queue_create("prototype.passive-pressure", DISPATCH_QUEUE_SERIAL);
	context.canceled = dispatch_semaphore_create(0);
	context.source = dispatch_source_create(DISPATCH_SOURCE_TYPE_MEMORYPRESSURE, 0,
		DISPATCH_MEMORYPRESSURE_NORMAL | DISPATCH_MEMORYPRESSURE_WARN
			| DISPATCH_MEMORYPRESSURE_CRITICAL, queue);
	const auto registered = (context.source != nullptr);
	const auto registrationSeconds = Prototype::Seconds(started);
	if (registered) {
		dispatch_set_context(context.source, &context);
		dispatch_source_set_event_handler_f(context.source, PressureEvent);
		dispatch_source_set_cancel_handler_f(context.source, PressureCanceled);
		dispatch_resume(context.source);
		std::this_thread::sleep_for(std::chrono::seconds(seconds));
		dispatch_source_cancel(context.source);
		// WHY: cancellation must finish before its stack context is destroyed.
		dispatch_semaphore_wait(context.canceled, DISPATCH_TIME_FOREVER);
	}
	const auto bits = context.bits.load();
	std::cout << "{\"registered\":" << (registered ? "true" : "false")
		<< ",\"registration_seconds\":" << registrationSeconds
		<< ",\"observation_seconds\":" << Prototype::Seconds(started)
		<< ",\"callbacks\":" << context.callbacks.load()
		<< ",\"event_bits\":" << bits
		<< ",\"normal_observed\":" << ((bits & DISPATCH_MEMORYPRESSURE_NORMAL) ? "true" : "false")
		<< ",\"warn_observed\":" << ((bits & DISPATCH_MEMORYPRESSURE_WARN) ? "true" : "false")
		<< ",\"critical_observed\":" << ((bits & DISPATCH_MEMORYPRESSURE_CRITICAL) ? "true" : "false")
		<< ",\"critical_reclamation_proven\":false}" << std::endl;
#if !OS_OBJECT_USE_OBJC
	if (context.source) {
		dispatch_release(context.source);
	}
	dispatch_release(context.canceled);
	dispatch_release(queue);
#endif
	return registered ? 0 : 2;
}

} // namespace

int main(int argc, char **argv) {
	if (argc == 2 && std::string_view(argv[1]) == "--network-probe") {
		return Prototype::NetworkProbe();
	} else if (argc == 6 && std::string_view(argv[1]) == "--files") {
		return Files(argv + 2);
	} else if (argc == 3 && std::string_view(argv[1]) == "--pressure") {
		auto seconds = 0;
		const auto text = std::string_view(argv[2]);
		const auto parsed = std::from_chars(text.data(), text.data() + text.size(), seconds);
		if (parsed.ec == std::errc() && parsed.ptr == text.data() + text.size()
			&& seconds >= 1 && seconds <= 120) {
			return Pressure(seconds);
		}
	}
	std::cerr << "usage: isolation_probe --network-probe | --files MODEL MANAGED DENIED WRITE | --pressure SECONDS(1..120)" << std::endl;
	return 2;
}
