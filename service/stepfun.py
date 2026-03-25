from openai import OpenAI
import json
from typing import Dict

"""
   CONTEXTUAL ANCHOR: 
    Use the following Metadata to identify structure and prune noise:
    {json.dumps(book_metadata, indent=2)}

"""

class StepFun:

  def __init__(self):
    self.model = OpenAI(base_url="https://openrouter.ai/api/v1", api_key="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",)



  async def clean_corpus(self, book_corpus: str) -> Dict:
    print("I was called for the purpose of cleaning up the text you sent in.")
 
    prompt = f"""
    ACT AS A MASTER LINGUISTIC SYNTHESIZER AND NARRATIVE ARCHITECT.
 
    TASK:
    1. DISENTANGLE & RECONSTRUCT: Rectify the OCR-degraded fragments into their pristine literary form.
    2. CHRONOLOGICAL SEQUENCING: Determine the correct narrative order of the fragments based on the source text.
    3. AGGREGATE BY CHAPTER: Instead of returning a list of fragments, COALESCE all text belonging to the same chapter into a SINGLE entry.
   
    OUTPUT SCHEMA (STRICT JSON):
    Return an object where each key is the Chapter Number, containing:
      - "full_text": (The complete, appended, and rectified prose for that chapter)

    SOURCE TEXT:
    {book_corpus}
    """

    response = self.model.chat.completions.create(
      model="stepfun/step-3.5-flash:free",
      messages=[
          {"role": "system", "content": "You are an expert in literary prosody. High-precision output required."},
          {"role": "user", "content": prompt}
      ],
      extra_body={"reasoning": {"enabled": True}}
    )
    print(response.choices[0].message.content)
    #print(json.loads(response.choices[0].message.content))
    return json.loads(response.choices[0].message.content)