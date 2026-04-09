import asyncio
import edge_tts
import os
from typing import List, Dict, Any
from pydub import AudioSegment
import glob
import logging
from cartesia import Cartesia
import subprocess
import os
from dotenv import load_dotenv
from service.cartesia_test import tts_generate_to_file




load_dotenv()

client = Cartesia(api_key=os.getenv("CARTESIA_API_KEY"))




logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


# Voice Actors
voice_actors = ["en-US-AvaNeural", "en-US-GuyNeural", "en-GB-SoniaNeural"]
current_chunk_number = 0

async def generate_speech_from_chunks(chunks_to_chapter: List[Dict[str, Any]], output_dir: str = "audio_chunks"):
    converted_chunks_to_audio = []
    #print("Generating audio for chunk number:", chunk_number)
    os.makedirs(output_dir, exist_ok=True)
    if len(chunks_to_chapter) == 0 or chunks_to_chapter is None:
        logger.info("Chapters list is empty.")
    for chunk in chunks_to_chapter:
        chapter = chunk.get("chapter") # string, the chapters
        full_chunk = chunk.get("chunk") # A list of string
       
        chunked_audio_path = await generate_audio(full_chunk, output_dir)
        converted_chunks_to_audio.append(
            {
                "chapter" : chapter,
                "chunked_audio" : chunked_audio_path
                }
                )
    print("We're DONE, each chapter now points to its chunked audio, now merge em")
    current_chunk_number = 0
    chapters_audio = await stitch_chunked_audio_chapters(converted_chunks_to_audio)
    print("The chapters are one", chapters_udio)
    logger.info("Begin, the stitch of chapters into a single audio")
    await stitch_chunked_audio_single(chapters_audio)
    logger.info("Chapters merged into a single audio. DONE.")


async def generate_audio(chunks_of_text: List[str], output_dir: str) -> List[str]:
    chunk_audio_path = []
    global current_chunk_number
    for chunk in chunks_of_text:
        current_chunk_number += 1
        print("Processing chunk number: ", current_chunk_number)
        print("Chunk content as: ", chunk)
        tts_generate_to_file(client, current_chunk_number, chunk)
        #output_path = os.path.join(output_dir, f"chunk_{current_chunk_number:03d}.mp3")
        #comm = edge_tts.Communicate(chunk, voice=voice_actors[2])
        #await comm.save(output_path)
        #chunk_audio_path.append(output_path)
        #print("DONE WITH A CHAPTER, CHUNKED!!!", output_path)
        await asyncio.sleep(0.3)
    return chunk_audio_path



async def stitch_chunked_audio_chapters(chunked_audio_path: List[Dict], chapter_path: str = "chapters") -> List:
    stitched_chapters_path = []
    """
    Asynchronously orchestrates the concatenation of audio fragments 
    from an explicit list of file paths.
    """
    if not chunked_audio_path:
        logger.warning("The provided path list is vacant; execution terminated.")
        return

    # Ensure the destination directory exists to prevent FileNotFoundError
    os.makedirs(chapter_path, exist_ok=True)

    logger.info("Commencing the synthesis of chunked audio entities...")
    for chapter_and_path in chunked_audio_path:
        chapter = chapter_and_path.get("chapter")
        audio_chunks = chapter_and_path.get("chunked_audio")
        try:
            # Initialize the accumulation buffer with the first element
            # It is prudent to assume the list is already ordered correctly
            combined = AudioSegment.from_mp3(audio_chunks[0])

            # Traverse the remaining paths
            for path in audio_chunks[1:]:
                next_segment = AudioSegment.from_mp3(path)
                # The 'append' method facilitates a seamless transition
                combined = combined.append(next_segment, crossfade=120)

            # Construct the terminal destination path
            output_filename = f"{chapter}.mp3"
            full_output_path = os.path.join(chapter_path, output_filename)

            # Export the composite audio buffer
            # Note: pydub's export is synchronous; in a high-concurrency 
            # environment, consider running this in a thread pool.
            combined.export(full_output_path, format="mp3", bitrate="192k")
            stitched_chapters_path.append({"chapter": chapter, "chapter_audio": full_output_path})
            logger.info(f"Stitching operation concluded. Artifact located at: {full_output_path}")
        except Exception as error:
            logger.error(f"A critical failure occurred during the stitching protocol: {error}")
    return stitched_chapters_path
    



async def stitch_chunked_audio_single(chunked_audio_path : List[Dict], final_path: str = "final_audio"):
    if not chunked_audio_path:
        print("List containing the path to chapters, empty.")
    
    os.makedirs(final_path, exist_ok=True)
    combined = AudioSegment.from_mp3(chunked_audio_path[0].get("chapter_audio"))
    for chapter_and_path in chunked_audio_path[1:]:
        next_chapter = chapter_and_path.get("chapter_audio")
        
        try:
            combined = combined.append(next_chapter, crossfade=120)
            full_path = os.path.join(final_path, "Erasing History.mp3")
            logger.info("Stitching of chapter to single audio DONE!")
            combined.export(full_path, format="mp3", bitrate="192k")
            logger.info("Give it a listen")

        except Exception as e:
            print("Error occured during stitch of chapters to single audio", e)