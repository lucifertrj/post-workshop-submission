"""Benchmark evaluation harness: answer extraction and scoring."""
from __future__ import annotations
import re
import string

def normalize_answer(s: str) -> str:
    """Lower text and remove punctuation, articles and extra whitespace."""
    def remove_articles(text: str) -> str:
        return re.sub(r'\b(a|an|the)\b', ' ', text)

    def white_space_fix(text: str) -> str:
        return ' '.join(text.split())

    def remove_punc(text: str) -> str:
        exclude = set(string.punctuation)
        return ''.join(ch for ch in text if ch not in exclude)

    def lower(text: str) -> str:
        return text.lower()

    return white_space_fix(remove_articles(remove_punc(lower(s))))

def exact_match_score(prediction: str, ground_truth: str) -> float:
    """Calculate exact match score after normalization."""
    if not prediction or not ground_truth:
        return 0.0
    return 1.0 if normalize_answer(prediction) == normalize_answer(ground_truth) else 0.0

def extract_gsm8k_answer(text: str) -> str:
    """Extract numeric answer from GSM8K ground truth or model prediction."""
    # Look for #### <number> in ground truth
    match = re.search(r'####\s*(-?\d+(?:\.\d+)?)', text)
    if match:
        return match.group(1)
    
    # Heuristic for predictions: find the last number
    numbers = re.findall(r'-?\d+(?:\.\d+)?', text)
    if numbers:
        return numbers[-1]
    return ""

def evaluate_prediction(prediction: str, ground_truth: str, dataset_name: str) -> dict[str, float]:
    """Evaluate a prediction against the ground truth."""
    if "gsm8k" in dataset_name.lower():
        pred_ans = extract_gsm8k_answer(prediction)
        gt_ans = extract_gsm8k_answer(ground_truth)
        em = 1.0 if pred_ans and gt_ans and abs(float(pred_ans) - float(gt_ans)) < 1e-5 else 0.0
        return {"exact_match": em, "accuracy": em}
    else:
        # Default string matching (e.g., HotpotQA, TriviaQA)
        em = exact_match_score(prediction, ground_truth)
        return {"exact_match": em, "accuracy": em}
