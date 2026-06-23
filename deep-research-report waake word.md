# Executive Summary  
Designing a robust voice front-end for My‑PA (My Personal AI OS) requires carefully balancing accuracy, latency, and resource use across wake-word detection, voice activity detection (VAD), and speech-to-text (STT).  We surveyed leading open-source and edge-capable solutions.  **Wake-word engines** range from Picovoice’s **Porcupine** (97%+ accuracy at low false alarm rates) to older projects like Snowboy (now archived and far less accurate).  **VAD** options span simple libraries (Google’s WebRTC VAD – ultra-lightweight C code) to modern DNN models (Silero VAD – high accuracy in noise but needs PyTorch).  **STT engines** include offline toolkits like Vosk (Kaldi-based, Apache‑licensed, supports 20+ languages) and OpenAI’s Whisper (multilingual, high accuracy, but large models requiring GPUs).  We found that combining a low-footprint wake-word detector with a smart VAD and a tiered STT approach (local small model + cloud fallback) best meets the requirements for My‑PA’s desktop/mobile, privacy-preserving deployment. 

**Key findings:** Porcupine leads in lightweight wake-word accuracy, WebRTC VAD is minimal CPU but less noise-robust, and Silero VAD offers high accuracy at the cost of PyTorch dependency.  Vosk runs real-time on CPU with multi-language support, while Whisper (via [whisper.cpp](https://github.com/ggerganov/whisper.cpp)) yields the best accuracy across ~99 languages if hardware allows.  Coqui STT (MPL‑2.0) was once popular but is now **unmaintained**.  Mycroft Precise (Apache‑2.0) can do wake words on Linux, but it’s heavier and less portable than Porcupine.  

**Recommendations:** Use **Porcupine** (or a free alternative like [OpenWakeWord](https://github.com/open-jarvis/OpenJarvis)) for wake-word detection; **Silero VAD** for high-quality speech boundary detection (falling back to WebRTC VAD on ultra-light hardware); **Whisper.cpp (Whisper)** as the primary on-device ASR (with model choice per device) and **Vosk** as a secondary offline fallback (or vice-versa); plus an optional cloud-STT API as a last-resort.  We outline an integration plan with a flowchart, code-level hooks in FastAPI, a provider-abstraction layer for VAD/STT, and stepwise migration to avoid breaking existing functionality.  We also specify benchmarks (WER, FRR/FAR, end-to-end latency) using standard audio test sets. Finally, we include “Claude/IDE prompts” for analyzing each key repo (Porcupine, Vosk, Whisper, Silero, etc.) to extract reusable modules without wholesale copying.

# Project Comparison Table

| Component              | Project (Repo) & Link                                 | Key Features                                                   | Pros                                                            | Cons                                                    | Integr. Effort    | Use-Case                             |
|------------------------|------------------------------------------------------|----------------------------------------------------------------|-----------------------------------------------------------------|---------------------------------------------------------|-------------------|---------------------------------------|
| **Wake-Word (KWS)**    | **Porcupine** (Picovoice)<br/>(github.com/Picovoice/porcupine) | On-device keyword spotting; custom wake-word training; C/Python/Go SDKs; ~3.8% CPU on RPi.           | Industry-leading accuracy (≈97% at 1 FA/10hr); very low CPU; 100% offline; easy training UI.   | Proprietary (requires Picovoice console/key for custom words); limited free tier.  | Medium (needs SDK & key) | Primary wake-word trigger (e.g. “Hey Jarvis”). |
| **Wake-Word**          | **Snowboy** (Kitt-AI) (archived)      | Offline hotword detection (pre-trained models or custom); Python/C++; ~24% CPU on RPi.             | Open-source (historically); ad-hoc custom model training.       | **Discontinued**; very high CPU; poor accuracy vs Porcupine; no recent updates. | High (Legacy, unsupported) | Legacy fallback, not recommended.      |
| **Wake-Word**          | **Mycroft Precise** (apache-2.0)      | RNN-based wake-word engine; “Hey Mycroft” style listening; binary+Python runner.                                     | Fully open-source (Apache 2.0); supports training; used on Linux.               | Linux-only; CPU-heavy; modest accuracy; aging codebase (Mycroft moving away). | High (fits Linux only) | Wake-word on Linux devices, optional. |
| **VAD**                | **WebRTC VAD** (py-webrtcvad)         | C-based GMM detector (Google WebRTC); Python bindings; accepts 10/20/30ms frames; lightweight.                  | Extremely lightweight (C only, minimal CPU); cross-platform; no deps; free/BSD.    | Classic signal-processing (not ML) – lower accuracy in noise; some false triggers.   | Low (pip install)      | Basic voice-activity gating when CPU is very constrained. |
| **VAD**                | **Silero VAD** (MIT)<br/>(snakers4/silero-vad) | PyTorch DNN for VAD; ultra-responsive (32ms chunks); trained on 6000+ languages.        | High accuracy in noise; MIT license; easy PyTorch Hub install.   | Larger footprint (PyTorch); heavier runtime; no native mobile SDK; platform support mostly Python. | Medium (adds PyTorch)  | Preferred VAD for desktop/edge where accuracy matters. |
| **Speech-to-Text**     | **Vosk** (Apache-2.0)<br/>(alphacep/vosk-api)  | DNN-HMM engine (Kaldi-based); 20+ languages; lightweight models (~50MB); true streaming API.    | CPU-only, works on Android/iOS/RPi; Apache license; continuous recognition. | Moderate accuracy (WER ~12–35% depending on model/data); fewer updates than bigger projects. | Medium (pip + models)  | Offline transcription, especially on low-end hardware (e.g. RPi, Android). |
| **Speech-to-Text**     | **Whisper (OpenAI)** (MIT)<br/>(openai/whisper)  | Transformer-based ASR; 99+ languages; robust to noise; multiple sizes (39M–1.5B params). | Very high accuracy (10–30% WER); multilingual; open-source; has optimized C++ port (whisper.cpp). | Huge models require GPUs/10+GB RAM; natively batch-mode (needs extra work for streaming); latency on CPU is high. | High (GPU or optimized runtime)  | Primary ASR on desktop/server; whisper.cpp for faster CPU/mobile inference. |
| **Speech-to-Text**     | **Silero STT** (MIT)<br/>(snakers4/silero-models) | Compact PyTorch ASR models (EN/DE/ES); optimized for CPU; simple Torch Hub interface.  | Lightweight (runs on CPU); MIT license; surprisingly robust to domain/noise.    | Fewer languages (currently ~3); open-source but niche community; smaller models may lag Whisper accuracy. | Medium (pip PyTorch)  | Offline STT on CPU where Whisper is too heavy; multi-accent capable. |
| **Speech-to-Text**     | **Coqui STT** (Mozilla’s DeepSpeech fork) – *archived* | TensorFlow ASR; English models; fine-tuning support.                     | Open-source (MPL 2.0); previously had active models.            | **Discontinued (2023)**; community dead; older neural approach (no longer state-of-art).   | Low (avoid)            | **Deprecated – not recommended.**     |
| **Speech-to-Text**     | **Kaldi** (apache-2.0) – *toolkit*<br/>(kaldi-asr/kaldi)  | Research ASR engine (HMM-DNN); extremely accurate if tuned; highly flexible. | Very high accuracy; extremely customizable; extensive language models available.        | Complex to configure; heavyweight (training typically needs GPUs/TPUs); integration is non-trivial.      | Very High (expertise needed) | Large-scale or research ASR work (out of scope for quick integration). |

*Table: Top voice processing projects relevant to My-PA.  Accuracy/WER data mostly from open benchmarks. Integration effort is relative: low means pip-ready; high means major code/infra work.*  

# Recommended Voice Stack for My‑PA  

We recommend a **layered pipeline**: an always-listening wake-word detector activates detailed listening (via VAD) and STT only when needed.  A typical flow is:  
1. **Audio capture:** Microphone streams into a background listener.  
2. **Wake-word engine:** Run a KWS engine (e.g. Porcupine) on the raw stream. When the user says the trigger word (e.g. “Jarvis”), the system “wakes up”. Porcupine offers ≈97% accuracy with very low CPU. As an alternative, an open-engine like [OpenWakeWord](https://github.com/open-jarvis/OpenJarvis) or Mycroft Precise could be used (Precise is Apache‑2.0 but Linux-only) if licensing is a concern.  
3. **Voice Activity Detection:** Upon wake, feed the ensuing audio to a VAD. We suggest **Silero VAD** (MIT license) for best accuracy in noisy conditions. It processes short frames (~32 ms) with minimal latency. On very low-end devices (or for fallback), one can use **WebRTC VAD** (py-webrtcvad, BSD-like), which is trivial to run on any CPU. The VAD trims silence and avoids unnecessary STT calls.  
4. **Speech-to-Text (Offline):** Once a voice segment is captured, run an on-device ASR. Our primary choice is **Whisper**, using the `whisper.cpp` C++ runtime for efficiency. Smaller Whisper models (tiny/base) run in real-time on modern desktop CPUs. Whisper gives top-tier accuracy (10–30% WER) and supports 99+ languages. For critical mobile or CPU-only cases, consider **Vosk** as an alternate STT: its 50MB models allow continuous streaming on phones and Raspberry Pis, albeit with somewhat higher WER (12–35%). We also include **Silero STT** (Python) for English/Spanish/German, since it is ultra-fast on CPU and complements Whisper if resources are scarce. All these run **offline** for privacy.  
5. **Cloud Fallback:** If offline ASR is unavailable or confidence is low, route audio to a cloud API (e.g. Whisper API, Azure, etc.) as fallback. This retains privacy-first operation by default.  
6. **Text processing:** The recognized text enters My-PA’s orchestrator for agent/action processing (beyond our scope here).  

```mermaid
graph LR
    A([Audio Input (microphone)]) --> B{Wake-Word Detector}
    B -->|Trigger "Hey Jarvis"| C[Start Recording Utterance]
    B -->|No trigger| B
    C --> D{Voice Activity Detection}
    D -->|Speech end detected| E[Run STT (Offline)]
    E --> F((Transcript Text))
    D -->|Speech end & low confidence| H[Fallback: Cloud STT]
    H --> F
    F --> G{Text → My-PA Agents / Tools}
```

*Figure: Voice pipeline. “Offline STT” can be Whisper (with whisper.cpp) or Vosk/Silero. VAD ensures we only transcribe speech segments.*  

# Integration Plan for My‑PA  

To integrate this stack into My‑PA’s FastAPI/Python codebase (https://github.com/codervinitjangir/My-PA), we propose:  

- **Providers/Abstraction Layer:** Define new provider interfaces in Python, e.g. `class WakeWordProvider`, `VADProvider`, `SpeechToTextProvider`. Implement classes like `PorcupineProvider`, `SileroVADProvider`, `WhisperProvider`, `VoskProvider`. This follows the existing LangChain-style architecture in My-PA, enabling plug-and-play of different engines.  

- **Code Hooks:** Insert hooks in the core audio service. For example, modify `app/audio_listener.py` (or similar) to start a background thread capturing microphone audio (e.g. via `sounddevice` or `pyaudio`). Feed these audio buffers to the wake-word provider. On trigger, switch to VAD+STT mode. Use FastAPI’s WebSocket or streaming endpoints to send transcribed text to the brain.  

- **Incremental Migration:** Start by adding the wake-word module without changing existing command logic. For instance, let My-PA continue listening as before, but concurrently check for the wake word. Once validated, implement VAD+STT. New modules should be added under a `speech/` directory (e.g. `speech/wakeword.py`, `speech/vad.py`, `speech/asr.py`), without disturbing existing code.  

- **Configuration:** Allow selecting engines via config or environment. For example, a YAML config can list which wake-word and STT engines to use, so we can switch out providers without code changes.  

- **Testing:** Develop unit tests simulating audio buffers. E.g. sample `.wav` files or generated waveforms for “Jarvis, turn on the light” with/without noise. Test that wake-word is detected appropriately (measure FRR/FAR), VAD splits speech correctly, and STT returns expected text (measure WER). CI pipeline should run key speech providers in a simple mode to catch integration errors.  

- **Fallback Logic:** If primary ASR fails (e.g. returns low-confidence or empty result), catch the exception or empty output and reroute to a cloud API via a `CloudSTTProvider`. Implement exponential backoff/retry and clear user feedback if all ASRs fail.  

- **Code Example Snippet (Python):**  

   ```python
   # speech/providers.py
   class WakeWordProvider:
       def __init__(self, model_path): ...
       def is_trigger(self, audio_frame): ...
   class PorcupineProvider(WakeWordProvider):
       def __init__(...): super().__init__(...)
       def is_trigger(self, frame): return porcupine.process(frame) >= 0

   class VADProvider:
       def __init__(self): ...
       def is_speech(self, frame): ...
   class SileroVADProvider(VADProvider):
       def __init__(self): self.model = load_silero_vad(...)
       def is_speech(self, frame): return self.model(frame) > 0.5

   class STTProvider:
       def transcribe(self, audio_data): ...
   class WhisperProvider(STTProvider):
       def __init__(self, model_size): self.model = whisper.load_model(model_size)
       def transcribe(self, audio): return self.model.transcribe(audio)["text"]

   # In audio_listener.py
   vad = SileroVADProvider()
   stt = WhisperProvider('small')
   if wake_word_provider.is_trigger(buffer):
       # collect until silence via VAD
       transcript = stt.transcribe(collected_audio)
   ```  

# Migration & Risk Analysis  

- **Dependency Bloat:** Adding PyTorch (for Silero models) and whisper.cpp may significantly enlarge the Python env. We mitigate by making these optional providers. Lazy-load heavy libraries only when enabled.  

- **Platform Variability:** Not all engines run everywhere. For example, Mycroft Precise only runs on Linux, so avoid it if cross-plat support is needed. Whisper large models need ≥10GB RAM/GPU; on weaker machines use smaller models or fallback to Vosk/whisper.cpp CPU mode. Always test on each target platform (Windows/macOS/Linux/Android/iOS/RPi).  

- **Latency:** Running large ASR on CPU can incur multi-second latency. Aim for end-to-end voice cycle <500ms on desktops. Use VAD to avoid transcribing silence, and consider batching (buffer + process) or streaming modes.  

- **Accuracy Trade-offs:** Lower model sizes or simpler VAD may increase errors. Balance by allowing user to configure sensitivity or switch engines. We should log FRR/FAR metrics in production for tuning (as Picovoice suggests).  

- **Licensing and Vendor Lock-in:** Picovoice Porcupine/Cobra are not fully free for commercial use; ensure we comply (or use an alternative like OpenWakeWord). All chosen open tools (Vosk, Whisper, Silero) use permissive licenses (Apache/MIT). Mycroft Precise (Apache) and WebRTC (BSD) are fine. Coqui (MPL) is no longer active.  

- **Security/Privacy:** Since all components run locally, user audio never leaves the device unless cloud fallback is used. We must secure any API keys.  

# Benchmark Strategy  

To evaluate performance, we suggest:  

- **Test Sets:** Use standard corpora (e.g. LibriSpeech test sets, CommonVoice, or a custom voice commands dataset) mixed with realistic noise. Include accented speakers and different languages for multilingual STT.  

- **Metrics:** Measure Word Error Rate (WER) and Command Accuracy for STT. For wake-word, measure False Rejection Rate (FRR) and False Acceptance Rate (FAR) per 10 hours. For VAD, use false positive/negative rates on speech vs silence segments. Also track system metrics: end-to-end latency (audio capture to text), CPU/RAM usage (profiling on target hardware). Aim for <500ms latency (as in Fig. above) and FAR ≪ 1/hour.  

- **Benchmarks Tools:** Use libraries like [jiwer](https://github.com/jitsi/jiwer) for WER, [webrtcvad](https://github.com/wiseman/py-webrtcvad) to generate ground-truth VAD labels, and simple scripts to simulate live audio input.  

- **Hardware Targets:** Test on representative devices: a Linux desktop (x86_64), a midrange Windows laptop, an Android phone/RPi. Compare CPU% and real-time factor.  

# Implementation Prompts for Claude/IDE  

For each recommended project, we will have Claude (or a similar code assistant) produce a **REUSE_PLAN.md** by analyzing *My-PA* alongside the project.  These prompts ensure we *extract ideas/code patterns*, not blindly copy code. Below are example prompts (one per project):

```plaintext
**Prompt:** Analyze the **Picovoice Porcupine** wake-word engine (GitHub: https://github.com/Picovoice/porcupine) in detail. Also scan My-PA (https://github.com/codervinitjangir/My-PA). Identify reusable components or patterns (e.g. audio frame processing, provider interface) that could fit into My-PA. For each, explain how it would integrate (e.g. required files, Python bindings via `pvporcupine` package), complexity, and risk. Generate a document `PORCUPINE_REUSE_PLAN.md` listing:
- Modules/functions to adapt (e.g. PorcupinePython API usage).
- Why useful for My-PA (on-device KWS).
- Implementation notes (e.g. need access key, model download).
- No code changes – focus on plan only.
```

```plaintext
**Prompt:** Analyze **Vosk** (alphacep/vosk-api, GitHub: https://github.com/alphacep/vosk-api) alongside My-PA. Identify how My-PA could reuse Vosk’s offline STT capabilities. Focus on:
- Python bindings (`pip install vosk`), example usage.
- How to hook into FastAPI (stream or file input).
- Required model management.
- Compare with current STT (if any) in My-PA.
Create `VOSK_REUSE_PLAN.md` describing integration of Vosk ASR with My-PA (files impacted, interfaces, performance expectations).
```

```plaintext
**Prompt:** Analyze **OpenAI Whisper** (https://github.com/openai/whisper) with My-PA. Since Whisper is primarily an ASR model, focus on:
- Its Python API (torch/cpu or whisper.cpp for speed).
- How to modularize as a speech provider.
- Memory and GPU needs.
- How to choose model sizes.
Generate `WHISPER_REUSE_PLAN.md` outlining how to call Whisper within My-PA’s architecture (e.g. as a SpeechToTextProvider), and fallback logic.
```

```plaintext
**Prompt:** Analyze **Silero VAD/STT** models (snakers4/silero-vad and snakers4/silero-models on GitHub). For My-PA:
- Identify how to use Silero VAD (32ms frames) in Python (Torch Hub).
- Identify how to use Silero STT (English/ES/DE) with Torch Hub.
- Determine how to manage PyTorch dependency and ensure real-time use.
- Produce `SILERO_REUSE_PLAN.md` with actionable steps (e.g. install Torch Hub models, preprocess audio, integrate into the voice pipeline).
```

```plaintext
**Prompt:** Analyze **py-webrtcvad** (https://github.com/wiseman/py-webrtcvad) with My-PA. Focus on:
- Using it for simple voice activity detection (frame lengths, modes).
- How to integrate as a lightweight VAD fallback in My-PA.
- Compare latency vs Silero VAD.
Generate `WEBRTC_VAD_REUSE_PLAN.md` explaining adding py-webrtcvad as a VADProvider.
```

```plaintext
**Prompt:** *(If chosen)* Analyze **Mycroft Precise** (https://github.com/MycroftAI/mycroft-precise) with My-PA. Check:
- How precise handles audio and triggers.
- Its Python runner (`precise-runner`).
- Limitations (Linux only).
Write `PRECISE_REUSE_PLAN.md` summarizing potential reuse of Precise components (e.g. model files, APIs) and why we might or might not adopt it.
```

```plaintext
**Prompt:** Analyze **Vosk Android** (if using mobile targets) or **whisper.cpp** (https://github.com/ggerganov/whisper.cpp). For My-PA, determine how to utilize Whisper on-device via whisper.cpp (C++ binding) or Vosk’s Android API. Outline `WHISPER_CPP_REUSE_PLAN.md` detailing integrating the C++ Whisper engine (or Vosk Android) into My-PA (e.g. via Python bindings or subprocess).
```

*(Each prompt above instructs an AI code assistant to thoroughly scan both My‑PA and the given repo, then draft a markdown plan of reusable components and integration steps without writing actual implementation code.)*  

