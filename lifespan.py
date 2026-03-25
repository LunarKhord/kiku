from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from typing import AsyncGenerator
import logging


from service.stepfun import StepFun
from service .kokoro import VoiceSynthesizer

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("LifeSpan set in motion, preflight needs started.")

    logger.info("Initializing an instance of StepFun LLM model")
    step_fun_instance = StepFun()
    logger.info("Step Fun address:", step_fun_instance)

    logger.info("Initializing an instance of Kokoro TTS model")
    kokoro_instance = VoiceSynthesizer(model_path= "/home/lunarkhord/Desktop/kiku/models/kokoro-v1.0.int8.onnx", voices_path="/home/lunarkhord/Desktop/kiku/models/voices-v1.0.bin")


    yield {"stepfun": step_fun_instance, "kokoro": kokoro_instance}




def get_step_fun(request: Request):
    """
    Extracts the 'instance' from the application's global state.
    """
    return request.state.stepfun


def get_kokoro(request: Request):
    return request.state.kokoro