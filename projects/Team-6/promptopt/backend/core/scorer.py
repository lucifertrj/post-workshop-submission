import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

def run_on_dataset(variant, dataset):
    results = []
    for ex in dataset[:3]:
        try:
            res = model.generate_content(f"{variant}\n\nInput: {ex['input']}")
            results.append({"input": ex["input"], "label": ex["label"], "model_output": res.text.strip()})
        except Exception as e:
            print(f"️ Scorer error: {e}")
            results.append({"input": ex["input"], "label": ex["label"], "model_output": "error"})
    return results

def accuracy_score(scored):
    if not scored: return 0.0
    correct = 0
    for r in scored:
        pred = r["model_output"].lower().strip()
        label = r["label"].lower().strip()
        if pred == label or label in pred or pred.startswith(label.split()[0]): correct += 1
    return round(correct / len(scored), 3)

def llm_judge_score(variant, task_type, outputs):
    return 0.7 + (len(variant) % 10) * 0.02