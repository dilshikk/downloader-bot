import asyncio
from aiogram.types import Message


SPINNER_FRAMES = [
    "⬛⬛⬛⬛⬛",
    "🟥⬛⬛⬛⬛",
    "🟥🟧⬛⬛⬛",
    "🟥🟧🟨⬛⬛",
    "🟥🟧🟨🟩⬛",
    "🟥🟧🟨🟩🟦",
]

EFFECT_FRAMES = [
    "🎵 ░░░░░░░░░░  0%",
    "🎵 ██░░░░░░░░ 20%",
    "🎵 ████░░░░░░ 40%",
    "🎵 ██████░░░░ 60%",
    "🎵 ████████░░ 80%",
    "🎵 ██████████ 99%",
]

DOWNLOAD_FRAMES = [
    "📥 ░░░░░░░░░░  0%",
    "📥 ██░░░░░░░░ 20%",
    "📥 ████░░░░░░ 40%",
    "📥 ██████░░░░ 60%",
    "📥 ████████░░ 80%",
    "📥 ██████████ 99%",
]


class AnimatedLoader:
    """Animates a loading message while a task runs."""

    def __init__(self, message: Message, frames: list, interval: float = 1.2):
        self.message = message
        self.frames = frames
        self.interval = interval
        self._msg = None
        self._task = None

    async def start(self):
        self._msg = await self.message.answer(self.frames[0])
        self._task = asyncio.create_task(self._animate())
        return self._msg

    async def _animate(self):
        idx = 1
        while True:
            await asyncio.sleep(self.interval)
            try:
                frame = self.frames[idx % len(self.frames)]
                await self._msg.edit_text(frame)
                idx += 1
            except Exception:
                break

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._msg:
            try:
                await self._msg.delete()
            except Exception:
                pass
