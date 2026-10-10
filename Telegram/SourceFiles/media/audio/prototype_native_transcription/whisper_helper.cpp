#include "common.hpp"
#include "whisper.h"
#include <algorithm>
#include <cmath>
#include <limits>
#include <memory>

namespace {

void Hex(std::string_view bytes) {
	constexpr auto digits = "0123456789abcdef";
	std::cout << '"';
	for (const auto ch : bytes) {
		const auto value = static_cast<unsigned char>(ch);
		std::cout << digits[value >> 4] << digits[value & 15];
	}
	std::cout << '"';
}

void Number(float value) {
	if (std::isfinite(value)) {
		std::cout.precision(std::numeric_limits<float>::max_digits10);
		std::cout << value;
	} else {
		std::cout << "null";
	}
}

void Evidence(
		whisper_context *context,
		const whisper_full_params &params,
		std::string_view text,
		std::string_view language,
		size_t samples,
		double seconds,
		int calls) {
	std::cout << "{\"status\":\"ok\",\"text\":";
	Prototype::Quote(text);
	std::cout << ",\"raw_text_hex\":";
	Hex(text);
	std::cout << ",\"language\":";
	Prototype::Quote(language);
	std::cout << ",\"seconds\":" << seconds
		<< ",\"calls\":" << calls << ",\"samples\":" << samples;
	Prototype::MemoryFields();
	std::cout << ",\"scores_calibrated\":false,\"abstention_policy\":null"
		<< ",\"timing\":\"estimated_centiseconds_request_local\""
		<< ",\"dtw\":false,\"configuration\":{\"strategy\":\"greedy\""
		<< ",\"threads\":" << params.n_threads
		<< ",\"translate\":false,\"no_context\":true"
		<< ",\"token_timestamps\":true,\"temperature_inc\":0"
		<< ",\"entropy_thold\":" << params.entropy_thold
		<< ",\"logprob_thold\":" << params.logprob_thold
		<< ",\"no_speech_thold\":" << params.no_speech_thold
		<< ",\"suppress_blank\":" << (params.suppress_blank ? "true" : "false")
		<< ",\"suppress_nst\":" << (params.suppress_nst ? "true" : "false")
		<< "},\"segments\":[";
	for (auto i = 0; i < whisper_full_n_segments(context); ++i) {
		if (i) {
			std::cout << ',';
		}
		std::cout << "{\"text_hex\":";
		Hex(whisper_full_get_segment_text(context, i));
		std::cout << ",\"t0\":" << whisper_full_get_segment_t0(context, i)
			<< ",\"t1\":" << whisper_full_get_segment_t1(context, i)
			<< ",\"no_speech_prob\":";
		Number(whisper_full_get_segment_no_speech_prob(context, i));
		std::cout << ",\"tokens\":[";
		for (auto j = 0; j < whisper_full_n_tokens(context, i); ++j) {
			if (j) {
				std::cout << ',';
			}
			const auto token = whisper_full_get_token_data(context, i, j);
			std::cout << "{\"id\":" << token.id << ",\"text_hex\":";
			Hex(whisper_full_get_token_text(context, i, j));
			std::cout << ",\"p\":";
			Number(token.p);
			std::cout << ",\"plog\":";
			Number(token.plog);
			std::cout << ",\"t0\":" << token.t0 << ",\"t1\":" << token.t1
				<< ",\"dtw_time\":null}";
		}
		std::cout << "]}";
	}
	std::cout << "]}" << std::endl;
}

} // namespace

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
				&& whisper_lang_id(request.language.c_str()) < 0) {
				Prototype::Error("unsupported language");
				continue;
			}
			auto params = whisper_full_default_params(WHISPER_SAMPLING_GREEDY);
			params.n_threads = 8;
			params.translate = false;
			params.no_context = true;
			params.no_timestamps = false;
			params.token_timestamps = true;
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
			Evidence(context.get(), params, text,
				language ? language : "unknown", request.audio.size(),
				Prototype::Seconds(started), ++calls);
			std::fill(request.audio.begin(), request.audio.end(), 0.f);
		}
		return 0;
	} catch (const std::exception &error) {
		std::cerr << error.what() << std::endl;
		return 2;
	}
}
