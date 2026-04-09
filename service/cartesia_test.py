from cartesia import Cartesia
import subprocess
import os
from dotenv import load_dotenv



load_dotenv()

client = Cartesia(api_key=os.getenv("CARTESIA_API_KEY"))


def tts_generate_to_file(client: Cartesia, chunk_number: int, chunk_of_text: str) -> None:
    """Use generate() and write_to_file() to write a wav file."""
    response = client.tts.generate(
        model_id="sonic-3",
        transcript=chunk_of_text,
        voice={"mode": "id", "id": "6ccbfb76-1fc6-48f7-b71d-91ac6298247b"},
        output_format={"container": "wav", "encoding": "pcm_f32le", "sample_rate": 44100},
    )
    response.write_to_file(f"{chunk_number}.mp3")
    print(f"Saved audio to output.wav")
    print(f"Play with: ffplay -f wav output.wav")



