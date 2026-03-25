import soundfile as sf
from kokoro_onnx import Kokoro as KokoroEngine # Aliasing to avoid collision
import asyncio



class VoiceSynthesizer:
    def __init__(self, model_path: str, voices_path: str):
        # Initializing the 'Acoustic Latent Space'
        self.model = KokoroEngine(model_path, voices_path)

    async def generate_speech(self, text: str, output_path: str, voice: str = "bm_george"):
        """
        Transmutes text into an auditory waveform using the INT8 engine.
        """
        # We use 'to_thread' because local TTS is a blocking CPU task
        samples, sample_rate = await asyncio.to_thread(
            self.model.create, 
            text, 
            voice=voice, 
            speed=0.9, 
            lang="en-us"
        )

        await self.save_to_disk(samples, sample_rate, output_path)
       
    async def save_to_disk(self, samples, sample_rate, path: str):
        # Persisting the auditory artifact
        await asyncio.to_thread(sf.write, path, samples, sample_rate)
        print(f"Synthesis complete: {path}")