#include "common.hpp"
#include <sherpa-onnx/c-api/c-api.h>

#include <algorithm>
#include <memory>
#include <stdexcept>
#include <string>

namespace {

using Recognizer = std::unique_ptr<const SherpaOnnxOfflineRecognizer,
	decltype(&SherpaOnnxDestroyOfflineRecognizer)>;
using Stream = std::unique_ptr<const SherpaOnnxOfflineStream,
	decltype(&SherpaOnnxDestroyOfflineStream)>;
using Recognition = std::unique_ptr<const SherpaOnnxOfflineRecognizerResult,
	decltype(&SherpaOnnxDestroyOfflineRecognizerResult)>;

const char *OrEmpty(const char *value) {
	return value ? value : "";
}

} // namespace

int main(int argc, char **argv) {
	if (argc == 2 && std::string_view(argv[1]) == "--network-probe") {
		return Prototype::NetworkProbe();
	}
	if (argc != 3) {
		Prototype::Error("usage: sherpa_helper MODEL_DIRECTORY cpu|coreml");
		return 2;
	}
	const auto provider = std::string_view(argv[2]);
	if (provider != "cpu" && provider != "coreml") {
		Prototype::Error("unsupported provider: expected cpu or coreml");
		return 2;
	}

	std::cerr << "sherpa-onnx native C API version="
		<< OrEmpty(SherpaOnnxGetVersionStr())
		<< " git=" << OrEmpty(SherpaOnnxGetGitSha1())
		<< " built=" << OrEmpty(SherpaOnnxGetGitDate())
		<< " onnxruntime=" << OrEmpty(SherpaOnnxGetOnnxruntimeVersionStr())
		<< " requested_provider=" << provider << '\n';
	std::cerr << "Parakeet automatic transcription; forced language unsupported. "
		"Language label is only returned if present in the native result. "
		"Native JSON diagnostics expose available token timestamps/durations/log probabilities; "
		"log probabilities are not calibrated transcript confidence or unclear markers. "
		"No in-process decode cancellation API; supervisor terminates the process.\n";
	if (provider == "coreml") {
		std::cerr << "CoreML requested, not verified graph offload: the sherpa C API "
			"does not expose selected providers/partition coverage; native source can "
			"fall back to CPU and ignores CoreML registration status. "
			"No ANE-only/int8 acceleration claim.\n";
	}

	const auto encoder = std::string(argv[1]) + "/encoder.int8.onnx";
	const auto decoder = std::string(argv[1]) + "/decoder.int8.onnx";
	const auto joiner = std::string(argv[1]) + "/joiner.int8.onnx";
	const auto tokens = std::string(argv[1]) + "/tokens.txt";
	Recognizer recognizer(nullptr, &SherpaOnnxDestroyOfflineRecognizer);
	const auto load = [&] {
		if (recognizer) {
			Prototype::State("ready");
			return true;
		}
		const auto start = Prototype::Clock::now();
		SherpaOnnxOfflineRecognizerConfig config{};
		config.feat_config.sample_rate = Prototype::kSampleRate;
		config.feat_config.feature_dim = 80;
		config.model_config.transducer.encoder = encoder.c_str();
		config.model_config.transducer.decoder = decoder.c_str();
		config.model_config.transducer.joiner = joiner.c_str();
		config.model_config.tokens = tokens.c_str();
		config.model_config.model_type = "nemo_transducer";
		config.model_config.provider = argv[2];
		config.model_config.num_threads = 2;
		config.model_config.debug = 1;
		config.decoding_method = "greedy_search";
		recognizer.reset(SherpaOnnxCreateOfflineRecognizer(&config));
		if (!recognizer) {
			Prototype::Error("sherpa native model loading failed; see stderr");
			return false;
		}
		Prototype::State("ready", Prototype::Seconds(start));
		return true;
	};

	try {
		Prototype::ObserveMemoryPressure();
		if (!load()) {
			return 1;
		}
		auto request = Prototype::Request();
		request.audio.reserve(Prototype::kMaximumSamples);
		auto calls = 0;
		while (Prototype::Read(request)) {
			if (request.command == "QUIT") {
				break;
			} else if (request.command == "UNLOAD") {
				recognizer.reset();
				Prototype::State("unloaded");
			} else if (request.command == "LOAD") {
				load();
			} else if (request.command != "RUN") {
				Prototype::Error("unsupported command");
			} else if (request.language == "de" || request.language == "en") {
				Prototype::Error("forced language unsupported for Parakeet nemo_transducer; use auto");
			} else if (request.language != "auto") {
				Prototype::Error("unsupported language: expected auto, de, or en");
			} else if (!recognizer) {
				Prototype::Error("model is unloaded; send LOAD first");
			} else {
				const auto start = Prototype::Clock::now();
				// A fresh native stream prevents previous utterance conditioning.
				Stream stream(SherpaOnnxCreateOfflineStream(recognizer.get()),
					&SherpaOnnxDestroyOfflineStream);
				if (!stream) {
					Prototype::Error("sherpa native stream creation failed");
					continue;
				}
				SherpaOnnxAcceptWaveformOffline(stream.get(), Prototype::kSampleRate,
					request.audio.data(), static_cast<int32_t>(request.audio.size()));
				SherpaOnnxDecodeOfflineStream(recognizer.get(), stream.get());
				Recognition result(SherpaOnnxGetOfflineStreamResult(stream.get()),
					&SherpaOnnxDestroyOfflineRecognizerResult);
				if (!result) {
					Prototype::Error("sherpa native result acquisition failed");
					continue;
				}
				const auto seconds = Prototype::Seconds(start);
				// Preserve native evidence without adding invented confidence/unclear policy.
				std::cerr << "sherpa_native_result=" << OrEmpty(result->json) << '\n';
				Prototype::Result(OrEmpty(result->text), OrEmpty(result->lang), seconds, ++calls);
				std::fill(request.audio.begin(), request.audio.end(), 0.f);
			}
		}
	} catch (const std::exception &error) {
		Prototype::Error(error.what());
		return 1;
	}
	return 0;
}
