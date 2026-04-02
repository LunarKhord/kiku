import soundfile as sf
import numpy as np
from kokoro_onnx import Kokoro as KokoroEngine
from typing import List, Dict
import os


class VoiceSynthesizer:
    """
    """

    def __init__(self, model_path: str, voices_path: str):
        print("🔊 Initializing Kokoro Engine...")
        self.engine = KokoroEngine(model_path, voices_path)
        self.sample_rate = 24000  # Kokoro standard
    

