from openai import OpenAI
import json
import os
import asyncio
import re
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv



load_dotenv()


class StepFun:
    def __init__(self):
        self.model = "nvidia/nemotron-3-nano-30b-a3b:free"
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
        self.REQUEST_DELAY = 8

    async def call_stepfun(
        self,
        messages: List[Dict],
        max_tokens: int = 2000,
        stream: bool = False,
        max_retries: int = 5,
    ) -> Optional[str | Any]:
        """Call the model with retry logic.
        If stream=True, returns an async generator yielding tokens.
        Otherwise returns the full content string.
        """
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    stream=stream,
                    extra_body={
                        "reasoning": {"enabled": True}
                    },  # disable to save tokens
                )

                if stream:
                    # Return an async generator that yields text chunks
                    async def stream_generator():
                        for chunk in response:
                            content = chunk.choices[0].delta.content
                            if content:
                                yield content
                        await asyncio.sleep(
                            self.REQUEST_DELAY
                        )  # rate limit after stream

                    return stream_generator()
                else:
                    # Non-streaming: wait for full response
                    await asyncio.sleep(self.REQUEST_DELAY)

                    return response.choices[0].message.content

            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "rate limit" in error_msg.lower():
                    wait_time = 8 * (attempt + 1)
                    print(f"⚠️ Rate limited. Waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                if "404" in error_msg or "No endpoints found" in error_msg:
                    print(f"⚠️ Model unavailable. Switching to nemotron-nano-9b...")
                    self.model = "nvidia/nemotron-nano-9b-v2:free"
                    await asyncio.sleep(2)
                    continue
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2**attempt)

    async def generate_chapters_from_corpus(
        self, full_corpus: str, book_metadata: Dict
    ):
        full_corpus = full_corpus.replace("\n", "").replace("\\", "")
        # We put the text at the END. Models often forget instructions if
        # a 50,000-word book is placed after the command.
        system_prompt = (
            "You are a strict JSON-only data extractor. "
            "Output ONLY a valid JSON array. No markdown, no explanations, no reasoning."
        )

        user_prompt = f"""
        TASK: Identify all chapters in the provided text and extract their exact boundaries.

        REQUIRED JSON FORMAT:
        [
        {{
            "title": "Exact Chapter/Part Title (e.g. 'Chapter 1' or 'Part II')",
            "start": "First 50 chars of narrative text (skip title & blank lines)",
            "end": "Last 50 chars of narrative text (stop BEFORE next title)"
        }}
        ]

        CRITICAL BOUNDARY RULES:
        1. STOP BEFORE NEXT TITLE: The "end" string must END exactly before the title of the next chapter/part begins. It must NEVER include the next title (e.g., "PART II").
        2. IGNORE PAGE ARTIFACTS: Do NOT include page numbers (like "Page 71"), headers, or footers in the "start" or "end" strings. Extract the narrative content only.
        3. EXACT MATCH: "start" and "end" strings must match the source text character-for-character, including spaces/newlines.
        4. NO OVERLAP: The text in "end" for Chapter 1 must be completely distinct from the "title" of Chapter 2.

        METADATA: {json.dumps(book_metadata)}

        TEXT TO ANALYZE:
        {full_corpus}

        JSON OUTPUT:"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = await self.call_stepfun(messages, max_tokens=8000, stream=False)

        # Clean up the response in case it wrapped it in markdown code blocks
        clean_json = response.replace("```json", "").replace("```", "").strip()

        try:
            manifest = json.loads(clean_json)
            
            chapter_to_content = await self.extract_content(full_corpus, manifest)
            return chapter_to_content

        except Exception as e:
            print(f"Failed to parse JSON: {e}")
            print(f"Raw response: {response}")
            return None

    async def extract_content(self, full_corpus, manifest) -> List[Dict]:
        book_chunk = []
        # Normalize the corpus for searching (remove extra spaces/newlines)
        # But we keep the original for the actual extraction!

        for index, entry in enumerate(manifest):
            # 1. Clean the anchor from the LLM (strip extra spaces)
            search_anchor = entry["start"].strip()

            # 2. Try to find the anchor
            start_index = full_corpus.find(search_anchor)

            # DEBUG: If it fails, let's see why
            if start_index == -1:
                print(f"⚠️ Warning: Could not find start anchor for {entry['title']}")
                # Fallback: if we can't find it, we just stay at the last known position
                start_index = 0 if index == 0 else book_chunk[-1]["end_pos"]

            # 3. Determine the end
            if index + 1 < len(manifest):
                next_anchor = manifest[index + 1]["start"].strip()
                end_index = full_corpus.find(next_anchor)
                if end_index == -1:
                    # If we can't find the next chapter, go until the end for now
                    end_index = len(full_corpus)
            else:
                end_index = len(full_corpus)

            # 4. Slice the text
            chapter_text = full_corpus[start_index:end_index].strip()

            # Store the end_pos so the next chapter can use it if it fails
            book_chunk.append(
                {
                    "title": entry["title"],
                    "text": chapter_text,
                }
            )
       
        print(f"✅ Successfully separated {len(book_chunk)} chapters.")
        return book_chunk
