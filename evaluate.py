"""Evaluation: how GOOD is our code? (Tests only check that it WORKS.)

Run:  .\\venv\\Scripts\\python.exe evaluate.py

1. Skill finder vs hand-labelled job posts -> precision, recall, F1
     precision = of the skills we found, how many were right?   (no false alarms)
     recall    = of the real skills, how many did we find?      (no misses)
     F1        = one number that balances both (1.0 = perfect)
2. Ranking: in pairs where the answer is obvious, did the better job win?

Always uses the EXAMPLE resume + rubric, so the numbers are the same for everyone.
"""

from pathlib import Path

import yaml

import config
from jobhunt import data_files, ranking, skills

CASES_FILE = Path(__file__).resolve().parent / "evaluation" / "cases.yaml"


def load_cases() -> dict:
    with open(CASES_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def example(path: Path) -> dict:
    return data_files.load_yaml(data_files.example_path(path))


def f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    score = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, score


def evaluate_skills(jobs: list[dict]) -> dict:
    rows, tp_all, fp_all, fn_all = [], 0, 0, 0
    for job in jobs:
        expected = {skills.canonical(s) for s in job["expected_skills"]}
        found = set(skills.extract_skills(f"{job['role']}\n{job['description']}"))
        tp, fp, fn = len(found & expected), len(found - expected), len(expected - found)
        tp_all, fp_all, fn_all = tp_all + tp, fp_all + fp, fn_all + fn
        rows.append({"id": job["id"], "f1": f1(tp, fp, fn)[2],
                     "missed": sorted(expected - found), "wrong": sorted(found - expected)})
    precision, recall, score = f1(tp_all, fp_all, fn_all)
    return {"rows": rows, "precision": precision, "recall": recall, "f1": score}


def evaluate_ranking(jobs: list[dict], pairs: list[list[str]]) -> dict:
    rubric = example(config.RUBRIC_PATH)
    my_skills = example(config.MASTER_RESUME_PATH)["skills"]
    scores = {}
    for job in jobs:
        row = {"company": "Example", "role": job["role"], "location": job["location"],
               "description": job["description"], "salary_lpa": job.get("salary_lpa")}
        scores[job["id"]] = ranking.score_job(row, rubric, my_skills)["score"]
    results = [{"better": a, "worse": b, "ok": scores[a] > scores[b],
                "scores": (scores[a], scores[b])} for a, b in pairs]
    return {"pairs": results, "correct": sum(r["ok"] for r in results), "scores": scores}


def main() -> None:
    cases = load_cases()
    report = evaluate_skills(cases["jobs"])
    print("SKILL FINDER (vs hand labels)")
    print(f"{'case':<26}{'F1':>6}  missed / wrong")
    for row in report["rows"]:
        notes = []
        if row["missed"]:
            notes.append("missed " + ", ".join(row["missed"]))
        if row["wrong"]:
            notes.append("wrong " + ", ".join(row["wrong"]))
        print(f"{row['id']:<26}{row['f1']:>6.2f}  {'; '.join(notes) or 'perfect'}")
    print(f"\nOverall  precision {report['precision']:.2f} | recall {report['recall']:.2f}"
          f" | F1 {report['f1']:.2f}")

    rank = evaluate_ranking(cases["jobs"], cases["ranking_pairs"])
    print("\nRANKING (obvious pairs)")
    for pair in rank["pairs"]:
        mark = "OK  " if pair["ok"] else "FAIL"
        print(f"{mark} {pair['better']} ({pair['scores'][0]}) > "
              f"{pair['worse']} ({pair['scores'][1]})")
    print(f"\n{rank['correct']}/{len(rank['pairs'])} pairs ranked correctly")


if __name__ == "__main__":
    main()
