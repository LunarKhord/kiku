import asyncio
import edge_tts
import os
from typing import List
from pydub import AudioSegment
import glob
import logging


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)



# Voice Actors
voice_actors = ["en-US-AvaNeural", "en-US-GuyNeural", "en-GB-SoniaNeural"]

async def generate_speech_from_chunks(chunks: List[str], output_dir: str = "audio_chunks"):
    os.makedirs(output_dir, exist_ok=True)
    for chunk_number, chunked_text in enumerate(chunks):
        output_path = os.path.join(output_dir, f"chunk_{chunk_number:03d}.mp3")
        print("Generating audio for chunk number:", chunk_number)

        comm = edge_tts.Communicate(chunked_text, voice=voice_actors[2])
        await comm.save(output_path)

        await asyncio.sleep(0.3)
    await stitch_chunked_audio(output_dir)



async def stitch_chunked_audio(chunk_dir_path: str, final_path: str = "final_audio"):
    os.makedirs(final_path, exist_ok=True)
    files = sorted(glob.glob(f"{chunk_dir_path}/chunk_*.mp3"))
    combined = AudioSegment.from_mp3(files[0])
    for file in files[1:]:
        combined = combined.append(AudioSegment.from_mp3(file), crossfade=120)
    full_path = os.path.join(final_path, f"Farenheit_351.mp3")
    logger.info("Stiching of chunked audio start....")
    combined.export(full_path, format="mp3", bitrate="192k")
    logger.info("Stitching of chunked audio DONE!")
    return