#include "common.hpp"

#include <Accelerate/Accelerate.h>
#include <ctranslate2/logging.h>
#include <ctranslate2/models/whisper.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <limits>
#include <memory>
#include <string_view>
#include <unordered_map>
#include <unordered_set>

namespace {

using Json = nlohmann::json;
constexpr auto kFFT = 400;
constexpr auto kHop = 160;
constexpr auto kBins = kFFT / 2 + 1;
constexpr auto kFrames = Prototype::kMaximumSamples / kHop;
constexpr auto kPi = 3.14159265358979323846;

Json Metadata(const std::string &directory, const char *name) {
	auto file = std::ifstream(directory + "/" + name);
	if (!file) throw std::runtime_error(std::string("missing local metadata: ") + name);
	return Json::parse(file);
}

std::array<int, 512> ByteDecoder() {
	auto result = std::array<int, 512>{};
	result.fill(-1);
	auto next = 256;
	for (auto byte = 0; byte != 256; ++byte) {
		const auto visible = (byte >= 33 && byte <= 126)
			|| (byte >= 161 && byte <= 172) || byte >= 174;
		result[visible ? byte : next++] = byte;
	}
	return result;
}

size_t Codepoint(const std::string &text, size_t position, unsigned &value) {
	const auto first = static_cast<unsigned char>(text[position]);
	if (first < 128) { value = first; return 1; }
	const auto length = (first >= 0xC2 && first <= 0xDF) ? 2
		: (first >= 0xE0 && first <= 0xEF) ? 3
		: (first >= 0xF0 && first <= 0xF4) ? 4 : 0;
	if (!length || position + length > text.size()) return 0;
	value = first & ((1u << (7 - length)) - 1);
	for (auto i = 1; i < length; ++i) {
		const auto byte = static_cast<unsigned char>(text[position + i]);
		if ((byte & 0xC0) != 0x80) return 0;
		value = (value << 6) | (byte & 0x3F);
	}
	if ((length == 2 && value < 0x80) || (length == 3 && value < 0x800)
		|| (length == 4 && value < 0x10000) || value > 0x10FFFF
		|| (value >= 0xD800 && value <= 0xDFFF)) return 0;
	return length;
}

std::string Utf8(std::string bytes) {
	for (size_t position = 0; position < bytes.size();) {
		auto codepoint = 0u;
		const auto length = Codepoint(bytes, position, codepoint);
		if (length) {
			position += length;
			continue;
		}
		const auto first = static_cast<unsigned char>(bytes[position]);
		const auto expected = (first >= 0xC2 && first <= 0xDF) ? 2
			: (first >= 0xE0 && first <= 0xEF) ? 3
			: (first >= 0xF0 && first <= 0xF4) ? 4 : 1;
		auto consumed = size_t(1);
		while (consumed < static_cast<size_t>(expected) && position + consumed < bytes.size()) {
			const auto next = static_cast<unsigned char>(bytes[position + consumed]);
			if ((next & 0xC0) != 0x80
				|| (consumed == 1 && ((first == 0xE0 && next < 0xA0)
					|| (first == 0xED && next >= 0xA0)
					|| (first == 0xF0 && next < 0x90)
					|| (first == 0xF4 && next >= 0x90)))) break;
			++consumed;
		}
		bytes.replace(position, consumed, "\xEF\xBF\xBD");
		position += 3;
	}
	return bytes;
}

class Detokenizer {
public:
	explicit Detokenizer(const std::string &directory) {
		const auto tokenizer = Metadata(directory, "tokenizer.json");
		const auto vocabulary = Metadata(directory, "vocabulary.json");
		if (tokenizer.at("decoder").at("type") != "ByteLevel"
			|| tokenizer.at("model").at("type") != "BPE"
			|| !vocabulary.is_array()) {
			throw std::runtime_error("unsupported tokenizer: expected Whisper GPT2 ByteLevel BPE");
		}
		auto addedIds = std::unordered_map<std::string, size_t>();
		for (const auto &token : tokenizer.at("added_tokens")) {
			const auto content = token.at("content").get<std::string>();
			const auto id = token.at("id").get<size_t>();
			if (id >= vocabulary.size() || vocabulary[id] != content) {
				throw std::runtime_error("native vocabulary and added token IDs disagree");
			}
			addedIds.emplace(content, id);
			if (token.at("special").get<bool>()) {
				_special.emplace(token.at("content").get<std::string>());
			}
		}
		const auto decoder = ByteDecoder();
		const auto &tokenIds = tokenizer.at("model").at("vocab");
		_bytes.reserve(vocabulary.size());
		for (size_t id = 0; id < vocabulary.size(); ++id) {
			const auto token = vocabulary[id].get<std::string>();
			if (_special.count(token)) continue;
			const auto added = addedIds.find(token);
			const auto matches = tokenIds.contains(token)
				? (tokenIds.at(token).get<size_t>() == id)
				: (added != addedIds.end() && added->second == id);
			if (!matches) {
				throw std::runtime_error("native vocabulary and tokenizer token IDs disagree");
			}
			auto bytes = std::string();
			bytes.reserve(token.size());
			for (size_t position = 0; position < token.size();) {
				auto value = 0u;
				const auto length = Codepoint(token, position, value);
				if (!length || value >= decoder.size() || decoder[value] < 0) {
					throw std::runtime_error("vocabulary contains a non-GPT2 byte token");
				}
				bytes.push_back(static_cast<char>(decoder[value]));
				position += length;
			}
			_bytes.emplace(token, std::move(bytes));
		}
		for (const auto token : {"<|startoftranscript|>", "<|de|>", "<|en|>",
			"<|transcribe|>", "<|notimestamps|>"}) {
			if (!_special.count(token)) throw std::runtime_error("missing Whisper prompt token");
		}
	}

	std::string Decode(const std::vector<std::string> &tokens) const {
		auto size = size_t(0);
		for (const auto &token : tokens) {
			if (!_special.count(token)) size += _bytes.at(token).size();
		}
		auto bytes = std::string();
		bytes.reserve(size);
		for (const auto &token : tokens) {
			if (!_special.count(token)) bytes += _bytes.at(token);
		}
		return Utf8(std::move(bytes));
	}

private:
	std::unordered_set<std::string> _special;
	std::unordered_map<std::string, std::string> _bytes;
};

class LogMel {
public:
	explicit LogMel(size_t mels)
	: _mels(mels)
	, _filters(mels * kBins)
	, _features({1, static_cast<ctranslate2::dim_t>(mels), kFrames},
		ctranslate2::DataType::FLOAT32, ctranslate2::Device::CPU) {
		if (mels != 80 && mels != 128) throw std::runtime_error("unsupported Whisper n_mels");
		for (auto i = 0; i < kFFT; ++i) {
			_window[i] = static_cast<float>(0.5 - 0.5 * std::cos(2 * kPi * i / kFFT));
		}
		const auto melToHz = [](double mel) {
			return mel < 15 ? mel * (200. / 3.)
				: 1000. * std::exp((mel - 15.) * (std::log(6.4) / 27.));
		};
		constexpr auto maximumMel = 45.245640471924965;
		for (size_t mel = 0; mel < mels; ++mel) {
			const auto left = melToHz(maximumMel * mel / (mels + 1));
			const auto middle = melToHz(maximumMel * (mel + 1) / (mels + 1));
			const auto right = melToHz(maximumMel * (mel + 2) / (mels + 1));
			for (auto bin = 0; bin < kBins; ++bin) {
				const auto hz = static_cast<double>(Prototype::kSampleRate) * bin / kFFT;
				const auto triangle = std::max(0.,
					std::min((hz - left) / (middle - left), (right - hz) / (right - middle)));
				_filters[mel * kBins + bin] = static_cast<float>(triangle * (2. / (right - left)));
			}
		}
		// The direct 400-point setup failed on this host. Five supported 80-point
		// DFTs plus precomputed outer twiddles preserve the actual FFT400 bins
		// without zero-padding to a different transform length.
		for (auto bin = 0; bin < kBins; ++bin) {
			for (auto residue = 1; residue < 5; ++residue) {
				const auto angle = -2 * kPi * bin * residue / kFFT;
				_twiddles[bin * 4 + residue - 1] = {
					static_cast<float>(std::cos(angle)),
					static_cast<float>(std::sin(angle))};
			}
		}
		_dft = vDSP_DFT_zop_CreateSetup(nullptr, kFFT / 5, vDSP_DFT_FORWARD);
		if (!_dft) throw std::runtime_error("Accelerate 80-point DFT unavailable");
	}

	~LogMel() { vDSP_DFT_DestroySetup(_dft); }
	LogMel(const LogMel&) = delete;
	LogMel &operator=(const LogMel&) = delete;

	const ctranslate2::StorageView &Extract(const std::vector<float> &audio) {
		if (audio.empty() || audio.size() > Prototype::kMaximumSamples) {
			throw std::runtime_error("PCM outside 30-second frontend bound");
		}
		const auto sample = [&](int position) {
			if (position < 0) position = -position;
			if (position >= Prototype::kMaximumSamples) {
				position = 2 * Prototype::kMaximumSamples - 2 - position;
			}
			return position < static_cast<int>(audio.size()) ? audio[position] : 0.f;
		};
		for (const auto value : audio) {
			if (!std::isfinite(value)) throw std::runtime_error("non-finite PCM");
		}
		auto *features = _features.data<float>();
		auto maximum = -std::numeric_limits<float>::infinity();
		for (auto frame = 0; frame < kFrames; ++frame) {
			for (auto residue = 0; residue < 5; ++residue) {
				for (auto inner = 0; inner < kFFT / 5; ++inner) {
					const auto i = 5 * inner + residue;
					_inputReal[inner] = sample(frame * kHop + i - kFFT / 2) * _window[i];
				}
				vDSP_DFT_Execute(_dft, _inputReal.data(), _zeroImag.data(),
					_innerReal.data() + residue * (kFFT / 5),
					_innerImag.data() + residue * (kFFT / 5));
			}
			for (auto bin = 0; bin < kBins; ++bin) {
				const auto innerBin = bin % (kFFT / 5);
				auto real = _innerReal[innerBin];
				auto imag = _innerImag[innerBin];
				for (auto residue = 1; residue < 5; ++residue) {
					const auto index = residue * (kFFT / 5) + innerBin;
					const auto twiddle = _twiddles[bin * 4 + residue - 1];
					real += _innerReal[index] * twiddle.real - _innerImag[index] * twiddle.imag;
					imag += _innerReal[index] * twiddle.imag + _innerImag[index] * twiddle.real;
				}
				_power[bin] = real * real + imag * imag;
			}
			for (size_t mel = 0; mel < _mels; ++mel) {
				auto energy = 0.f;
				vDSP_dotpr(_power.data(), 1, _filters.data() + mel * kBins, 1,
					&energy, kBins);
				const auto value = std::log10(std::max(energy, 1e-10f));
				features[mel * kFrames + frame] = value;
				maximum = std::max(maximum, value);
			}
		}
		for (size_t i = 0; i < _mels * kFrames; ++i) {
			features[i] = (std::max(features[i], maximum - 8.f) + 4.f) / 4.f;
		}
		return _features;
	}

private:
	size_t _mels;
	std::vector<float> _filters;
	ctranslate2::StorageView _features;
	vDSP_DFT_Setup _dft = nullptr;
	alignas(16) std::array<float, kFFT / 5> _inputReal{};
	alignas(16) std::array<float, kFFT / 5> _zeroImag{};
	alignas(16) std::array<float, kFFT> _innerReal{};
	alignas(16) std::array<float, kFFT> _innerImag{};
	alignas(16) std::array<DSPComplex, kBins * 4> _twiddles{};
	alignas(16) std::array<float, kFFT> _window{};
	alignas(16) std::array<float, kBins> _power{};
};

class Adapter {
public:
	Adapter(std::string directory, ctranslate2::ComputeType compute)
	: _directory(std::move(directory)), _compute(compute) {
	}

	void Load() {
		if (_whisper) { Prototype::State("ready"); return; }
		const auto start = Prototype::Clock::now();
		auto decoder = std::make_unique<Detokenizer>(_directory);
		auto model = ctranslate2::models::Model::load(_directory,
			ctranslate2::Device::CPU, 0, _compute);
		if (model->effective_compute_type() != _compute) {
			throw std::runtime_error("requested CPU compute type was not selected");
		}
		auto config = ctranslate2::ReplicaPoolConfig{};
		config.num_threads_per_replica = 4;
		auto whisper = std::make_unique<ctranslate2::models::Whisper>(model, config);
		if (!whisper->is_multilingual()) throw std::runtime_error("multilingual Whisper model required");
		const auto preprocessor = Metadata(_directory, "preprocessor_config.json");
		if (preprocessor.at("sampling_rate") != Prototype::kSampleRate
			|| preprocessor.at("n_fft") != kFFT || preprocessor.at("hop_length") != kHop
			|| preprocessor.at("chunk_length") != 30
			|| preprocessor.at("feature_size").get<size_t>() != whisper->n_mels()) {
			throw std::runtime_error("cached preprocessor metadata does not match native frontend");
		}
		auto frontend = std::make_unique<LogMel>(whisper->n_mels());
		std::cerr << "CT2_NATIVE_COMPONENT_QUALIFICATION compute="
			<< ctranslate2::compute_type_to_str(model->effective_compute_type())
			<< " n_mels=" << whisper->n_mels()
			<< " frontend_protocol=waveform_pad30sec; fixture comparison evidence"
			<< " recorded in frontend-notes.md; wrapper bit-identity and"
			<< " faster-whisper short-input feature padding parity not established;"
			<< " no Metal/CoreML backend or production quality claim" << std::endl;
		_decoder = std::move(decoder);
		_frontend = std::move(frontend);
		_whisper = std::move(whisper);
		Prototype::State("ready", Prototype::Seconds(start));
	}

	void Unload() {
		_whisper.reset();
		_frontend.reset();
		_decoder.reset();
		Prototype::State("unloaded");
	}

	void Run(const Prototype::Request &request) {
		if (!_whisper) throw std::runtime_error("model is unloaded; send LOAD");
		if (request.language != "auto" && request.language != "de" && request.language != "en") {
			throw std::runtime_error("unsupported forced language; expected auto/de/en");
		}
		const auto start = Prototype::Clock::now();
		const auto &features = _frontend->Extract(request.audio);
		const auto encoded = _whisper->encode(features, true).get();
		auto language = request.language;
		auto languageToken = std::string();
		if (language == "auto") {
			const auto detected = _whisper->detect_language(encoded).front().get();
			if (detected.empty()) throw std::runtime_error("native language detection returned no candidates");
			languageToken = detected.front().first;
			if (languageToken.size() < 5 || languageToken.substr(0, 2) != "<|"
				|| languageToken.substr(languageToken.size() - 2) != "|>") {
				throw std::runtime_error("native language token has unexpected format");
			}
			language = languageToken.substr(2, languageToken.size() - 4);
		} else {
			languageToken = "<|" + language + "|>";
		}
		auto prompt = std::vector<std::vector<std::string>>{{
			"<|startoftranscript|>", languageToken, "<|transcribe|>", "<|notimestamps|>"}};
		auto options = ctranslate2::models::WhisperOptions{};
		options.beam_size = 5;
		options.max_length = 448;
		const auto generated = _whisper->generate(encoded, std::move(prompt), options).front().get();
		if (generated.sequences.empty()) throw std::runtime_error("native generation returned no hypotheses");
		const auto text = _decoder->Decode(generated.sequences.front());
		Prototype::Result(text, language, Prototype::Seconds(start), ++_calls);
	}

private:
	std::string _directory;
	ctranslate2::ComputeType _compute;
	std::unique_ptr<ctranslate2::models::Whisper> _whisper;
	std::unique_ptr<LogMel> _frontend;
	std::unique_ptr<Detokenizer> _decoder;
	int _calls = 0;
};

}

int main(int argc, char **argv) {
	if (argc == 2 && std::string_view(argv[1]) == "--network-probe") return Prototype::NetworkProbe();
	try {
		if (argc == 3 && std::string_view(argv[1]) == "--decode-tokens") {
			const auto decoder = Detokenizer(argv[2]);
			const auto tokens = Json::parse(std::cin).get<std::vector<std::string>>();
			const auto text = decoder.Decode(tokens);
			std::cout << "{\"text\":";
			Prototype::Quote(text);
			std::cout << "}" << std::endl;
			return 0;
		}
		if (argc == 2 && std::string_view(argv[1]) == "--frontend-dump") {
			Prototype::ObserveMemoryPressure();
			auto request = Prototype::Request{};
			if (!Prototype::Read(request) || request.command != "RUN") {
				throw std::runtime_error("frontend dump requires one RUN request");
			}
			auto frontend = LogMel(128);
			const auto &features = frontend.Extract(request.audio);
			std::cout.write(reinterpret_cast<const char*>(features.data<float>()),
				features.size() * sizeof(float));
			if (!std::cout) throw std::runtime_error("frontend dump output failed");
			return 0;
		}
		if (argc < 2 || argc > 3) {
			throw std::runtime_error("usage: ct2_helper MODEL_DIRECTORY [float32|int8_float32]");
		}
		const auto compute = (argc == 3) ? std::string_view(argv[2]) : std::string_view("float32");
		if (compute != "float32" && compute != "int8_float32") {
			throw std::runtime_error("unsupported compute type: native macOS qualification allows CPU float32/int8_float32 only");
		}
		ctranslate2::init_logger();
		Prototype::ObserveMemoryPressure();
		auto adapter = Adapter(argv[1], compute == "float32"
			? ctranslate2::ComputeType::FLOAT32
			: ctranslate2::ComputeType::INT8_FLOAT32);
		adapter.Load();
		auto request = Prototype::Request{};
		request.audio.reserve(Prototype::kMaximumSamples);
		while (Prototype::Read(request)) {
			try {
				if (request.command == "QUIT") break;
				else if (request.command == "UNLOAD") adapter.Unload();
				else if (request.command == "LOAD") adapter.Load();
				else if (request.command == "RUN") adapter.Run(request);
				else Prototype::Error("unknown command");
			} catch (const std::exception &error) {
				Prototype::Error(error.what());
			}
		}
		return 0;
	} catch (const std::exception &error) {
		Prototype::Error(error.what());
		return 1;
	}
}
