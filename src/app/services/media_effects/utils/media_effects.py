import asyncio
import os

from pedalboard import Pedalboard
from pedalboard_native import HighpassFilter, Reverb, LowpassFilter, Compressor
from pedalboard_native.io import AudioFile

from src.app.utils.enums.general import GeneralEffectAction


class MediaEffectsTools:
    async def audio_effects(self, input_file: str, effect_type: GeneralEffectAction):
        try:
            base, _ = await asyncio.to_thread(os.path.splitext, input_file)
            output_file_path = f"{base}_effected.mp3"

            # 8D - bitta o'tishda: apulsator filtri bilan to'g'ridan-to'g'ri MP3 chiqarish
            if effect_type == GeneralEffectAction.EFFECT_8D:
                cmd = [
                    "ffmpeg", "-y", "-i", input_file,
                    "-filter_complex", "apulsator=hz=0.2",
                    "-codec:a", "libmp3lame", "-b:a", "192k", "-q:a", "4",
                    output_file_path
                ]
                p = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
                )
                await p.wait()

            # Slowed - bitta o'tishda
            elif effect_type == GeneralEffectAction.EFFECT_SLOWED:
                cmd = [
                    "ffmpeg", "-y", "-i", input_file,
                    "-filter_complex", "[0:a]asetrate=44100*0.85,aresample=44100,volume=1.05[a]",
                    "-map", "[a]",
                    "-codec:a", "libmp3lame", "-b:a", "192k", "-q:a", "4",
                    output_file_path
                ]
                p = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
                )
                await p.wait()

            # Minus - ovozni olib tashlash, bitta o'tishda
            elif effect_type == GeneralEffectAction.EFFECT_SPEED:
                cmd = [
                    "ffmpeg", "-y", "-i", input_file,
                    "-af", "pan=stereo|c0=c0-c1|c1=c1-c0",
                    "-codec:a", "libmp3lame", "-b:a", "192k", "-q:a", "4",
                    output_file_path
                ]
                p = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
                )
                await p.wait()

            # Konsert zal - pedalboard ishlatadi, shuning uchun WAV kerak
            elif effect_type == GeneralEffectAction.EFFECT_CONCERT_HALL:
                temp_wav = f"{base}_temp.wav"
                processed_wav = f"{base}_processed.wav"

                # Input -> WAV (pedalboard uchun)
                p0 = await asyncio.create_subprocess_exec(
                    "ffmpeg", "-y", "-i", input_file, "-ac", "2", "-ar", "44100", temp_wav,
                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
                )
                await p0.wait()

                def apply_concert_hall():
                    with AudioFile(temp_wav) as f:
                        audio = f.read(f.frames)
                        samplerate = f.samplerate
                    board = Pedalboard([
                        HighpassFilter(cutoff_frequency_hz=180),
                        LowpassFilter(cutoff_frequency_hz=9000),
                        Reverb(room_size=0.78, wet_level=0.30, dry_level=0.5, width=1.0),
                        Compressor(threshold_db=-18, ratio=2.0),
                    ])
                    effected = board(audio, samplerate)
                    with AudioFile(processed_wav, "w", samplerate, effected.shape[0]) as outf:
                        outf.write(effected)

                await asyncio.to_thread(apply_concert_hall)

                # WAV -> MP3
                p1 = await asyncio.create_subprocess_exec(
                    "ffmpeg", "-y", "-i", processed_wav,
                    "-codec:a", "libmp3lame", "-b:a", "192k", "-q:a", "4",
                    output_file_path,
                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
                )
                await p1.wait()

                for f in (temp_wav, processed_wav):
                    if await asyncio.to_thread(os.path.exists, f):
                        await asyncio.to_thread(os.remove, f)

            else:
                raise ValueError(f"Unknown effect type: {effect_type}")

            if await asyncio.to_thread(os.path.exists, output_file_path):
                return output_file_path
            else:
                raise FileNotFoundError("Output not created")

        except Exception as e:
            print("ERROR audio_effects:", e)
            return None

    async def video_effects(self, input_file: str, effect_type: GeneralEffectAction):
        base, _ = await asyncio.to_thread(os.path.splitext, input_file)
        temp_wav = f"{base}_temp.wav"
        processed_wav = f"{base}_processed.wav"
        output_file_path = f"{base}_effected.mp4"
        try:
            if effect_type == GeneralEffectAction.EFFECT_8D:
                cmd = ["ffmpeg", "-y", "-i", input_file, "-c:v", "copy", "-filter:a", "apulsator=hz=0.2", "-c:a", "aac", "-b:a", "192k", output_file_path]
                p = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                await p.wait()
                return output_file_path

            elif effect_type == GeneralEffectAction.EFFECT_SLOWED:
                cmd = ["ffmpeg", "-y", "-i", input_file, "-filter_complex", "[0:v]setpts=1.25*PTS[v];[0:a]atempo=0.8[a]", "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26", "-c:a", "aac", "-b:a", "192k", output_file_path]
                p = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                await p.wait()
                return output_file_path

            elif effect_type == GeneralEffectAction.EFFECT_SPEED:
                cmd = ["ffmpeg", "-y", "-i", input_file, "-filter_complex", "[0:a]pan=stereo|c0=c0-c1|c1=c1-c0[a]", "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", output_file_path]
                p = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                await p.wait()
                return output_file_path

            elif effect_type == GeneralEffectAction.EFFECT_CONCERT_HALL:
                ffmpeg_cmd = ["ffmpeg", "-y", "-i", input_file, "-ac", "2", "-ar", "44100", temp_wav]
                p = await asyncio.create_subprocess_exec(*ffmpeg_cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                await p.wait()

                if not await asyncio.to_thread(os.path.exists, temp_wav):
                    raise FileNotFoundError("Failed to convert input to WAV")

                def apply_concert_hall():
                    with AudioFile(temp_wav) as f:
                        audio = f.read(f.frames)
                        samplerate = f.samplerate
                    board = Pedalboard([
                        HighpassFilter(cutoff_frequency_hz=180),
                        LowpassFilter(cutoff_frequency_hz=9000),
                        Reverb(room_size=0.78, wet_level=0.30, dry_level=0.5, width=1.0),
                        Compressor(threshold_db=-18, ratio=2.0),
                    ])
                    effected = board(audio, samplerate)
                    with AudioFile(processed_wav, "w", samplerate, effected.shape[0]) as outf:
                        outf.write(effected)

                await asyncio.to_thread(apply_concert_hall)

                cmd = ["ffmpeg", "-y", "-i", input_file, "-i", processed_wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", output_file_path]
                p = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                await p.wait()
                return output_file_path

            else:
                return input_file

        except Exception as e:
            print("ERROR in video_effects:", e)
            return None

        finally:
            for f in (temp_wav, processed_wav):
                if await asyncio.to_thread(os.path.exists, f):
                    await asyncio.to_thread(os.remove, f)
