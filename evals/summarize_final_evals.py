import argparse
import json

from collections import defaultdict
from pathlib import Path


def load_runs(
    raw_directory: Path,
) -> list[dict]:

    files = sorted(
        raw_directory.glob(
            "run_*.json"
        )
    )

    if not files:
        raise RuntimeError(
            "No evaluation run files found."
        )

    runs = []

    for path in files:

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(
                file
            )

        data["_source_file"] = (
            path.name
        )

        runs.append(
            data
        )

    return runs


def validate_runs(
    runs: list[dict],
    expected_runs: int,
) -> list[str]:

    if len(runs) != expected_runs:
        raise RuntimeError(
            (
                f"Expected {expected_runs} "
                f"runs but found "
                f"{len(runs)}."
            )
        )

    reference_cases = [
        case["name"]
        for case
        in runs[0]["cases"]
    ]

    reference_hash = (
        runs[0]
        .get("metadata", {})
        .get("evaluator_sha256")
    )

    for run in runs[1:]:

        names = [
            case["name"]
            for case
            in run["cases"]
        ]

        if names != reference_cases:
            raise RuntimeError(
                "Evaluation case definitions "
                "differ between runs."
            )

        current_hash = (
            run
            .get("metadata", {})
            .get("evaluator_sha256")
        )

        if (
            reference_hash
            and current_hash
            and current_hash
            != reference_hash
        ):
            raise RuntimeError(
                "Evaluator SHA-256 differs "
                "between runs."
            )

    return reference_cases


def build_summary(
    runs: list[dict],
    case_names: list[str],
) -> dict:

    total_executions = 0
    passed_executions = 0

    per_case = {
        name: {
            "passed": 0,
            "executions": 0,
        }
        for name in case_names
    }

    category_results = defaultdict(
        lambda: {
            "passed": 0,
            "executions": 0,
        }
    )

    for run in runs:

        for case in run["cases"]:

            total_executions += 1

            name = case["name"]

            category = case.get(
                "category",
                "unknown",
            )

            per_case[
                name
            ]["executions"] += 1

            category_results[
                category
            ]["executions"] += 1

            if case["passed"]:

                passed_executions += 1

                per_case[
                    name
                ]["passed"] += 1

                category_results[
                    category
                ]["passed"] += 1

    observed_pass_rate = (
        passed_executions
        / total_executions
        if total_executions
        else 0
    )

    for values in per_case.values():

        values["pass_rate"] = (
            values["passed"]
            / values["executions"]
        )

    for values in category_results.values():

        values["pass_rate"] = (
            values["passed"]
            / values["executions"]
        )

    return {
        "independent_runs":
            len(runs),

        "scenarios_per_run":
            len(case_names),

        "scenario_executions":
            total_executions,

        "passed_executions":
            passed_executions,

        "observed_pass_rate":
            observed_pass_rate,

        "all_executions_passed":
            (
                passed_executions
                == total_executions
            ),

        "git_commit":
            runs[0]
            .get("metadata", {})
            .get(
                "git_commit",
                "unknown",
            ),

        "model_name":
            runs[0]
            .get("metadata", {})
            .get(
                "model_name",
                "unknown",
            ),

        "evaluator_sha256":
            runs[0]
            .get("metadata", {})
            .get(
                "evaluator_sha256",
                "unknown",
            ),

        "per_category":
            dict(category_results),

        "per_case":
            per_case,
    }


def write_markdown(
    summary: dict,
    path: Path,
) -> None:

    percentage = (
        summary[
            "observed_pass_rate"
        ]
        * 100
    )

    lines = [
        "# Final Agent Evaluation",
        "",
        (
            f"- Independent runs: "
            f"{summary['independent_runs']}"
        ),
        (
            f"- Scenarios per run: "
            f"{summary['scenarios_per_run']}"
        ),
        (
            f"- Scenario executions: "
            f"{summary['scenario_executions']}"
        ),
        (
            f"- Passed executions: "
            f"{summary['passed_executions']}"
        ),
        (
            f"- Observed pass rate: "
            f"{percentage:.1f}%"
        ),
        (
            f"- Model: "
            f"{summary['model_name']}"
        ),
        (
            f"- Git commit: "
            f"{summary['git_commit']}"
        ),
        "",
        "## Results by Category",
        "",
        "| Category | Passed | Executions | Pass rate |",
        "|---|---:|---:|---:|",
    ]

    for (
        category,
        values,
    ) in sorted(
        summary[
            "per_category"
        ].items()
    ):

        category_rate = (
            values["pass_rate"]
            * 100
        )

        lines.append(
            (
                f"| {category} "
                f"| {values['passed']} "
                f"| {values['executions']} "
                f"| {category_rate:.1f}% |"
            )
        )

    lines.extend(
        [
            "",
            "## Results by Scenario",
            "",
            "| Scenario | Passed | Runs | Pass rate |",
            "|---|---:|---:|---:|",
        ]
    )

    for (
        case_name,
        values,
    ) in summary[
        "per_case"
    ].items():

        case_rate = (
            values["pass_rate"]
            * 100
        )

        lines.append(
            (
                f"| {case_name} "
                f"| {values['passed']} "
                f"| {values['executions']} "
                f"| {case_rate:.1f}% |"
            )
        )

    path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--raw-dir",
        default=(
            "evals/results/final/raw"
        ),
    )

    parser.add_argument(
        "--output-dir",
        default=(
            "evals/results/final"
        ),
    )

    parser.add_argument(
        "--expected-runs",
        type=int,
        default=5,
    )

    args = parser.parse_args()

    raw_directory = Path(
        args.raw_dir
    )

    output_directory = Path(
        args.output_dir
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    runs = load_runs(
        raw_directory
    )

    case_names = validate_runs(
        runs,
        expected_runs=(
            args.expected_runs
        ),
    )

    summary = build_summary(
        runs,
        case_names,
    )

    json_path = (
        output_directory
        / "final_summary.json"
    )

    markdown_path = (
        output_directory
        / "final_summary.md"
    )

    with json_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            summary,
            file,
            indent=2,
            ensure_ascii=False,
        )

    write_markdown(
        summary,
        markdown_path,
    )

    print(
        "\nFinal evaluation summary"
    )

    print(
        (
            "Runs: "
            f"{summary['independent_runs']}"
        )
    )

    print(
        (
            "Executions: "
            f"{summary['scenario_executions']}"
        )
    )

    print(
        (
            "Passed: "
            f"{summary['passed_executions']}"
        )
    )

    print(
        (
            "Observed pass rate: "
            f"{summary['observed_pass_rate']:.1%}"
        )
    )

    print(
        f"\nSaved: {json_path}"
    )

    print(
        f"Saved: {markdown_path}"
    )


if __name__ == "__main__":
    main()