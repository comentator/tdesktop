#include "common.hpp"
#include "whisper.h"
#include <algorithm>
#include <memory>

int main(int argc, char **argv) {
	try {
		if (argc == 2 && std::string_view(argv[1]) == "--network-probe") {
			return Prototype::NetworkProbe();
		}
		if (argc != 3) {
			std::cerr << "usage: whisper_helper MODEL cpu|metal" << std::endl;
			return 2;
		}
		const auto mode = std::string_view(argv[2]);
		if (mode != "cpu" && mode != "metal") {
			throw std::runtime_error("unsupported Whisper backend");
		}
		std::cerr << "whisper_version=" << whisper_version()
			<< " requested_backend=" << mode << std::endl;
		Prototype::ObserveMemoryPressure();
		using Context = std::unique_ptr<whisper_context, decltype(&whisper_free)>;
		auto context = Context(nullptr, whisper_free);
		const auto load = [&] {
			const auto started = Prototype::Clock::now();
			auto params = whisper_context_default_params();
			params.use_gpu = (mode == "metal");
			context.reset(whisper_init_from_file_with_params(argv[1], params));
			if (!context) {
				throw std::runtime_error("Whisper model load failed");
			}
			Prototype::State("ready", Prototype::Seconds(started));
		};
		load();
		auto request = Prototype::Request();
		request.audio.reserve(Prototype::kMaximumSamples);
		auto text = std::string();
		auto calls = 0;
		while (Prototype::Read(request)) {
			if (request.command == "QUIT") {
				break;
			} else if (request.command == "UNLOAD") {
				context.reset();
				Prototype::State("unloaded");
				continue;
			} else if (request.command == "LOAD") {
				context.reset();
				load();
				continue;
			} else if (request.command != "RUN") {
				Prototype::Error("unsupported command");
				continue;
			} else if (!context) {
				Prototype::Error("model is unloaded");
				continue;
			}
			if (request.language != "auto"
				&& request.language != "de"
				&& request.language != "en") {
				Prototype::Error("unsupported language");
				continue;
			}
			auto params = whisper_full_default_params(WHISPER_SAMPLING_GREEDY);
			params.n_threads = 8;
			params.translate = false;
			params.no_context = true;
			params.no_timestamps = true;
			params.print_special = false;
			params.print_progress = false;
			params.print_realtime = false;
			params.print_timestamps = false;
			params.language = (request.language == "auto")
				? nullptr
				: request.language.c_str();
			params.temperature_inc = 0;
			const auto started = Prototype::Clock::now();
			const auto result = whisper_full(context.get(), params,
				request.audio.data(), static_cast<int>(request.audio.size()));
			if (result) {
				Prototype::Error("Whisper inference failed");
				continue;
			}
			text.clear();
			for (auto i = 0; i < whisper_full_n_segments(context.get()); ++i) {
				text += whisper_full_get_segment_text(context.get(), i);
			}
			const auto language = whisper_lang_str(
				whisper_full_lang_id(context.get()));
			Prototype::Result(text, language ? language : "unknown",
				Prototype::Seconds(started), ++calls);
			std::fill(request.audio.begin(), request.audio.end(), 0.f);
		}
		return 0;
	} catch (const std::exception &error) {
		std::cerr << error.what() << std::endl;
		return 2;
	}
}
