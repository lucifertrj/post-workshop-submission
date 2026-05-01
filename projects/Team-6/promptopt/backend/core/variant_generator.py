import google.generativeai as genai
import os
import json

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

META_PROMPT = """You are an expert prompt engineer. Improve this base prompt for: {task_name} ({task_type}).
Return exactly a JSON array of {n} unique prompt strings. No markdown, no explanations.

Base prompt: {base}
Feedback: {feedback}"""

def generate_variants(base_prompt, task_type, task_name, n, feedback="None"):
    prompt = META_PROMPT.format(task_name=task_name, task_type=task_type, n=n, base=base_prompt, feedback=feedback)
    try:
        res = model.generate_content(prompt)
        text = res.text.strip()
        if text.startswith("```"): text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text)[:n]
    except Exception as e:
        print(f"⚠️ Variant gen error: {e}")
        return [f"{base_prompt} [variant {i+1}]" for i in range(n)]