"""Ovoz: matnni ovozga aylantirish (TTS), ovozni matnga aylantirish (STT), oddiy VAD."""

import array
import asyncio
import logging
import os
import subprocess
import tempfile
import time
import uuid
import wave

import edge_tts
from google.genai import types

log = logging.getLogger("voice")

GEMINI_TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
GEMINI_VOICE = os.getenv("GEMINI_VOICE", "Aoede")  # bo'sh qoldirilsa faqat Edge ishlatiladi
EDGE_VOICE = os.getenv("TTS_VOICE", "uz-UZ-MadinaNeural")
STT_MODEL = os.getenv("STT_MODEL", "gemini-flash-lite-latest")

_gemini_tts_off_until = 0.0


def _tmp(ext: str) -> str:
    return os.path.join(tempfile.gettempdir(), f"agent_{uuid.uuid4().hex[:10]}.{ext}")


def write_wav(path: str, pcm: bytes, rate: int, channels: int = 1):
    with wave.open(path, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)


def pcm_to_wav_bytes(pcm: bytes, rate: int) -> bytes:
    path = _tmp("wav")
    write_wav(path, pcm, rate)
    with open(path, "rb") as f:
        data = f.read()
    os.remove(path)
    return data


async def tts(ai, text: str) -> str:
    """Matnni ovozli faylga aylantiradi. Avval Gemini (Aoede), limit tugasa Edge (Madina)."""
    global _gemini_tts_off_until
    if GEMINI_VOICE and time.time() > _gemini_tts_off_until:
        try:
            r = await asyncio.wait_for(
                ai.aio.models.generate_content(
                    model=GEMINI_TTS_MODEL,
                    contents=text,  # faqat matn: ko'rsatma qo'shilsa, uni ham o'qib yuboradi
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=GEMINI_VOICE)
                            )
                        ),
                    ),
                ),
                timeout=25,
            )
            pcm = r.candidates[0].content.parts[0].inline_data.data
            path = _tmp("wav")
            write_wav(path, pcm, 24000)
            return path
        except Exception as e:
            code = getattr(e, "code", None)
            # 429 = bepul limit tugadi: 1 soat Edge ovozida ishlaymiz
            _gemini_tts_off_until = time.time() + (3600 if code == 429 else 300)
            log.warning("Gemini TTS ishlamadi (%s), Madina ovoziga o'tildi", code or type(e).__name__)
    path = _tmp("mp3")
    await edge_tts.Communicate(text, EDGE_VOICE, rate="+8%", pitch="+20Hz").save(path)
    return path


def to_ogg_opus(src: str) -> str:
    dst = _tmp("ogg")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-c:a", "libopus", "-b:a", "48k", dst],
        check=True,
    )
    return dst


def to_mp3(src: str) -> str:
    if src.endswith(".mp3"):
        return src
    dst = _tmp("mp3")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-b:a", "96k", dst], check=True)
    return dst


async def transcribe(ai, audio: bytes, mime: str) -> str:
    """Ovozli xabarni matnga aylantiradi."""
    r = await asyncio.wait_for(
        ai.aio.models.generate_content(
            model=STT_MODEL,
            contents=[
                types.Part.from_bytes(data=audio, mime_type=mime),
                "Bu ovozli xabarni so'zma-so'z matnga yoz (asosan o'zbek tilida). Faqat matnni qaytar, "
                "hech qanday izoh qo'shma. Hech narsa eshitilmasa, bo'sh qator qaytar.",
            ],
        ),
        timeout=30,
    )
    return (r.text or "").strip()


def rms(pcm: bytes) -> float:
    """16-bit PCM ovoz balandligi (har 4-namuna bo'yicha, tezlik uchun)."""
    a = array.array("h")
    a.frombytes(pcm[: len(pcm) - len(pcm) % 2])
    if not a:
        return 0.0
    s = a[::4]
    return (sum(x * x for x in s) / len(s)) ** 0.5


class VAD:
    """Gap boshlanishi va tugashini aniqlaydigan oddiy detektor."""

    def __init__(self, rate: int, threshold: float, end_silence_ms=900, min_speech_ms=300, max_ms=20000):
        self.rate = rate
        self.threshold = threshold
        self.end_silence_ms = end_silence_ms
        self.min_speech_ms = min_speech_ms
        self.max_ms = max_ms
        self.preroll_bytes = int(rate * 2 * 0.3)
        self.reset()
        self._stat_t = time.time()
        self._stat_max = 0.0

    def reset(self):
        self.buf = bytearray()
        self.pre = bytearray()
        self.in_speech = False
        self.voiced_ms = 0.0
        self.silence_ms = 0.0

    def feed(self, pcm: bytes) -> bytes | None:
        """Gap tugaganda butun gapning PCM'ini qaytaradi, aks holda None."""
        ms = len(pcm) / 2 / self.rate * 1000
        level = rms(pcm)
        self._stat_max = max(self._stat_max, level)
        if time.time() - self._stat_t > 5:
            log.info("Mikrofon darajasi (5s max): %.0f, chegara: %.0f", self._stat_max, self.threshold)
            self._stat_t, self._stat_max = time.time(), 0.0
        if level >= self.threshold:
            if not self.in_speech:
                self.in_speech = True
                self.buf = bytearray(self.pre)
            self.buf += pcm
            self.voiced_ms += ms
            self.silence_ms = 0
        elif self.in_speech:
            self.buf += pcm
            self.silence_ms += ms
        else:
            self.pre += pcm
            if len(self.pre) > self.preroll_bytes:
                del self.pre[: len(self.pre) - self.preroll_bytes]
            return None
        total_ms = len(self.buf) / 2 / self.rate * 1000
        if self.silence_ms >= self.end_silence_ms or total_ms >= self.max_ms:
            out = bytes(self.buf) if self.voiced_ms >= self.min_speech_ms else None
            self.reset()
            return out
        return None
