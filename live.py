"""Gemini Live orqali real vaqtdagi telefon suhbati (Telegram qo'ng'iroq <-> Gemini)."""

import asyncio
import logging
import os
import time

from google.genai import types

log = logging.getLogger("live")

LIVE_MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.1-flash-live-preview")
LIVE_VOICE = os.getenv("GEMINI_VOICE", "Aoede") or "Aoede"
LIVE_LANG = os.getenv("GEMINI_LANG", "uz-UZ")  # o'zbekcha talaffuz va tanish
PREBUFFER_MS = int(os.getenv("LIVE_PREBUFFER_MS", "200"))  # uzilishsiz ovoz uchun bufer
IN_RATE = 16000  # qo'ng'iroqdan Gemini'ga
OUT_RATE = 24000  # Gemini'dan qo'ng'iroqqa
FRAME_MS = 10
OUT_FRAME = OUT_RATE * 2 * FRAME_MS // 1000  # 10 ms = 480 bayt
SILENCE = bytes(OUT_FRAME)
PREBUFFER = OUT_RATE * 2 * PREBUFFER_MS // 1000

END_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="qongiroqni_tugat",
            description="Suhbatdosh xayrlashganda yoki suhbat tugaganda qo'ng'iroqni yakunlaydi.",
        )
    ]
)


class LiveCall:
    def __init__(self, calls, ai, peer_id: int, hangup: asyncio.Event):
        self.calls = calls
        self.ai = ai
        self.peer_id = peer_id
        self.hangup = hangup
        self.mic: asyncio.Queue = asyncio.Queue(maxsize=500)
        self.out = bytearray()
        self.finish_requested = False
        self.turn_done = True
        self.transcript: list[tuple[str, str]] = []
        self._in_text = ""
        self._out_text = ""

    # ---- qo'ng'iroqdan kelgan ovoz (pytgcalls handleridan chaqiriladi)
    def feed_mic(self, pcm: bytes):
        try:
            self.mic.put_nowait(pcm)
        except asyncio.QueueFull:
            pass

    async def _sender(self, session):
        """Mikrofon ovozini ~100 ms bo'laklarda Gemini'ga yuboradi."""
        buf = bytearray()
        while True:
            buf += await self.mic.get()
            if len(buf) >= IN_RATE * 2 // 10:
                await session.send_realtime_input(
                    audio=types.Blob(data=bytes(buf), mime_type=f"audio/pcm;rate={IN_RATE}")
                )
                buf.clear()

    async def _player(self):
        """Gemini ovozini real vaqt tezligida (10 ms kadrlar) qo'ng'iroqqa uzatadi."""
        from pytgcalls.types import Device

        next_t = time.monotonic()
        playing = False
        while True:
            # Gap boshida biroz bufer yig'amiz: ovoz bo'linib-bo'linib chiqmasligi uchun
            if not playing and (len(self.out) >= PREBUFFER or (self.turn_done and self.out)):
                playing = True
            if playing and len(self.out) >= OUT_FRAME:
                frame = bytes(self.out[:OUT_FRAME])
                del self.out[:OUT_FRAME]
            else:
                if playing and self.out and self.turn_done:  # gap oxiridagi qoldiq
                    frame = bytes(self.out).ljust(OUT_FRAME, bytes(1))
                    self.out.clear()
                else:
                    frame = SILENCE
                if not self.out:
                    playing = False
            try:
                await self.calls.send_frame(self.peer_id, Device.MICROPHONE, frame)
            except Exception:
                return
            next_t += FRAME_MS / 1000
            delay = next_t - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)
            else:
                next_t = time.monotonic()  # orqada qolsak, vaqtni qayta tiklaymiz

    def _flush_text(self):
        if self._in_text.strip():
            self.transcript.append(("Siz", self._in_text.strip()))
        if self._out_text.strip():
            self.transcript.append(("Yordamchi", self._out_text.strip()))
        self._in_text = self._out_text = ""

    async def _receiver(self, session):
        while True:
            async for msg in session.receive():
                if msg.tool_call:
                    for fc in msg.tool_call.function_calls:
                        if fc.name == "qongiroqni_tugat":
                            self.finish_requested = True
                    await session.send_tool_response(
                        function_responses=[
                            types.FunctionResponse(id=fc.id, name=fc.name, response={"natija": "ok"})
                            for fc in msg.tool_call.function_calls
                        ]
                    )
                sc = msg.server_content
                if not sc:
                    continue
                if sc.interrupted:  # foydalanuvchi gapini bo'ldi: ovozni to'xtatamiz
                    self.out.clear()
                    self.turn_done = True
                if sc.model_turn:
                    self.turn_done = False
                    for part in sc.model_turn.parts:
                        if part.inline_data and part.inline_data.data:
                            self.out += part.inline_data.data
                if sc.input_transcription and sc.input_transcription.text:
                    self._in_text += sc.input_transcription.text
                if sc.output_transcription and sc.output_transcription.text:
                    self._out_text += sc.output_transcription.text
                if sc.turn_complete or sc.generation_complete:
                    self.turn_done = True
                if sc.turn_complete:
                    if self._in_text or self._out_text:
                        log.info("Jonli: siz=%r | u=%r", self._in_text.strip()[:80], self._out_text.strip()[:80])
                    self._flush_text()

    async def run(self, system: str, opening: str, max_seconds: int) -> list[tuple[str, str]]:
        from pytgcalls.types import CallConfig, ExternalMedia, MediaStream, RecordStream
        from pytgcalls.types.raw import AudioParameters

        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                language_code=LIVE_LANG or None,
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=LIVE_VOICE)
                )
            ),
            system_instruction=system,
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            tools=[END_TOOL],
            # Telefondagi shovqin gapni bo'lib qo'ymasin, odam gapini tugatishini kutsin
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_LOW,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
                    prefix_padding_ms=200,
                    silence_duration_ms=int(os.getenv("LIVE_SILENCE_MS", "800")),
                )
            ),
        )
        async with self.ai.aio.live.connect(model=LIVE_MODEL, config=config) as session:
            # Qo'ng'iroq: ovozni biz o'zimiz kadrma-kadr uzatamiz
            await self.calls.play(
                self.peer_id,
                MediaStream(ExternalMedia.AUDIO, audio_parameters=AudioParameters(OUT_RATE, 1)),
                CallConfig(timeout=60),
            )
            await self.calls.record(
                self.peer_id, RecordStream(audio=True, audio_parameters=AudioParameters(IN_RATE, 1))
            )
            log.info("Jonli suhbat ulandi (%s, %s)", LIVE_MODEL, LIVE_VOICE)
            tasks = [
                asyncio.create_task(self._player()),
                asyncio.create_task(self._sender(session)),
                asyncio.create_task(self._receiver(session)),
            ]
            await session.send_client_content(
                turns=types.Content(
                    role="user",
                    parts=[types.Part(text=f"(Qo'ng'iroq ulandi, suhbatdosh telefonni ko'tardi. {opening})")],
                ),
                turn_complete=True,
            )
            started = time.time()
            try:
                while not self.hangup.is_set() and time.time() - started < max_seconds:
                    if any(t.done() for t in tasks[1:]):  # Gemini aloqasi uzildi
                        for t in tasks:
                            if t.done() and t.exception():
                                log.warning("Jonli aloqa uzildi: %r", t.exception())
                        break
                    if self.finish_requested and len(self.out) == 0:
                        await asyncio.sleep(0.5)  # oxirgi so'z eshitilsin
                        break
                    await asyncio.sleep(0.2)
            finally:
                for t in tasks:
                    t.cancel()
                self._flush_text()
        return self.transcript
