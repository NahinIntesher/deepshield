from typing import List, Dict, Any
from ..models.db_models import ResearchSubmission

class MetricsCalculator:
    @staticmethod
    def calculate_kpis(submissions: List[ResearchSubmission]) -> Dict[str, Any]:
        """
        Computes academic evaluation metrics comparing Human evaluators vs Swin/DCT/Transformer AI detector.
        """
        if not submissions:
            return {
                "total_evaluations": 0,
                "human_accuracy": 0.0,
                "human_precision": 0.0,
                "human_recall": 0.0,
                "human_f1": 0.0,
                "ai_accuracy": 0.0,
                "ai_precision": 0.0,
                "ai_recall": 0.0,
                "ai_f1": 0.0,
                "hybrid_accuracy": 0.0,
                "human_confusion_matrix": {"TP": 0, "FP": 0, "TN": 0, "FN": 0},
                "ai_confusion_matrix": {"TP": 0, "FP": 0, "TN": 0, "FN": 0},
                "quadrant_breakdown": {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0},
                "calibration_data": []
            }

        total = len(submissions)

        # Human Confusion Matrix (Positive = "Fake", Negative = "Real")
        h_tp = sum(1 for s in submissions if s.human_prediction == "Fake" and s.ground_truth == "Fake")
        h_fp = sum(1 for s in submissions if s.human_prediction == "Fake" and s.ground_truth == "Real")
        h_tn = sum(1 for s in submissions if s.human_prediction == "Real" and s.ground_truth == "Real")
        h_fn = sum(1 for s in submissions if s.human_prediction == "Real" and s.ground_truth == "Fake")

        # AI Confusion Matrix
        ai_tp = sum(1 for s in submissions if s.ai_prediction == "Fake" and s.ground_truth == "Fake")
        ai_fp = sum(1 for s in submissions if s.ai_prediction == "Fake" and s.ground_truth == "Real")
        ai_tn = sum(1 for s in submissions if s.ai_prediction == "Real" and s.ground_truth == "Real")
        ai_fn = sum(1 for s in submissions if s.ai_prediction == "Real" and s.ground_truth == "Fake")

        # Hybrid Complementary Ensemble:
        # A sample is flagged Fake if either Human (confidence >= 4) or AI (confidence >= 0.75) flags it
        hybrid_correct = 0
        for s in submissions:
            hybrid_pred = "Real"
            if s.human_prediction == "Fake" and s.human_confidence >= 4:
                hybrid_pred = "Fake"
            elif s.ai_prediction == "Fake" and s.ai_confidence >= 0.75:
                hybrid_pred = "Fake"
            elif s.human_prediction == "Fake" and s.ai_prediction == "Fake":
                hybrid_pred = "Fake"
            
            if hybrid_pred == s.ground_truth:
                hybrid_correct += 1

        def safe_metrics(tp, fp, tn, fn):
            acc = round(((tp + tn) / max(tp + fp + tn + fn, 1)) * 100, 1)
            prec = round((tp / max(tp + fp, 1)) * 100, 1) if (tp + fp) > 0 else 0.0
            rec = round((tp / max(tp + fn, 1)) * 100, 1) if (tp + fn) > 0 else 0.0
            f1 = round((2 * prec * rec / max(prec + rec, 1e-5)), 1) if (prec + rec) > 0 else 0.0
            return acc, prec, rec, f1

        h_acc, h_prec, h_rec, h_f1 = safe_metrics(h_tp, h_fp, h_tn, h_fn)
        ai_acc, ai_prec, ai_rec, ai_f1 = safe_metrics(ai_tp, ai_fp, ai_tn, ai_fn)
        hybrid_acc = round((hybrid_correct / total) * 100, 1)

        # 4 Quadrants
        q1_count = sum(1 for s in submissions if s.disagreement_quadrant == "Q1")
        q2_count = sum(1 for s in submissions if s.disagreement_quadrant == "Q2")
        q3_count = sum(1 for s in submissions if s.disagreement_quadrant == "Q3")
        q4_count = sum(1 for s in submissions if s.disagreement_quadrant == "Q4")

        # Calibration Data by Human Confidence level (1 to 5)
        calibration = []
        for conf_level in range(1, 6):
            subset = [s for s in submissions if s.human_confidence == conf_level]
            if subset:
                subset_acc = round((sum(1 for s in subset if s.is_human_correct) / len(subset)) * 100, 1)
                calibration.append({
                    "confidence_level": conf_level,
                    "confidence_label": f"Level {conf_level}",
                    "expected_accuracy": conf_level * 20.0,
                    "actual_accuracy": subset_acc,
                    "sample_count": len(subset)
                })
            else:
                calibration.append({
                    "confidence_level": conf_level,
                    "confidence_label": f"Level {conf_level}",
                    "expected_accuracy": conf_level * 20.0,
                    "actual_accuracy": 0.0,
                    "sample_count": 0
                })

        return {
            "total_evaluations": total,
            "human_accuracy": h_acc,
            "human_precision": h_prec,
            "human_recall": h_rec,
            "human_f1": h_f1,
            "ai_accuracy": ai_acc,
            "ai_precision": ai_prec,
            "ai_recall": ai_rec,
            "ai_f1": ai_f1,
            "hybrid_accuracy": hybrid_acc,
            "human_confusion_matrix": {"TP": h_tp, "FP": h_fp, "TN": h_tn, "FN": h_fn},
            "ai_confusion_matrix": {"TP": ai_tp, "FP": ai_fp, "TN": ai_tn, "FN": ai_fn},
            "quadrant_breakdown": {"Q1": q1_count, "Q2": q2_count, "Q3": q3_count, "Q4": q4_count},
            "calibration_data": calibration
        }

metrics_calculator = MetricsCalculator()
