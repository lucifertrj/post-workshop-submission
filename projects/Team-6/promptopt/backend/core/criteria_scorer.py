import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

def criteria_score(variant, criteria, test_input):
    if not criteria: return 0.5
    judge_prompt = f"""Evaluate this prompt on the test input.
Prompt: {variant}
Input: {test_input}
Output: (simulate LLM output based on prompt)

Rules:
{chr(10).join(f"- {c}" for c in criteria)}

How many rules does this prompt likely satisfy? Return only a number 0-1."""
    try:
        res = model.generate_content(judge_prompt, generation_config={"max_output_tokens": 10})
        return float(res.text.strip())
    except: return 0.5