import argparse
import json
import os
import random
import shutil
from pathlib import Path
from typing import Any, Dict, List, Union


def load_jsonl_file(file_path: str) -> List[Dict[str, Any]]:
    """Load records from a JSONL file."""
    records = []
    with open(file_path) as f:
        for line in f:
            records.append(json.loads(line))
    return records


def save_jsonl_file(records: List[Dict[str, Any]], file_path: str) -> None:
    """Save records to a JSONL file, ensuring they are sorted by ID."""
    # Sort records before saving
    sorted_records = sort_by_numeric_id(records)

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        for record in sorted_records:
            f.write(json.dumps(record) + "\n")


def get_record_ids(records: Union[List[Dict[str, Any]], Dict[str, Any]]) -> set:
    """Extract IDs from records."""
    return {record.get("id") for record in records}


def get_answer_ids(answers: List[Dict[str, Any]]) -> set:
    """Extract IDs from possible answers."""
    return {answer.get("id") for answer in answers}


def filter_records_with_answers(
    records: Union[List[Dict[str, Any]], Dict[str, Any]], answer_ids: set
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """Filter records to only include those that have corresponding answers."""
    return [record for record in records if record.get("id") in answer_ids]


def extract_numeric_id(record: Dict[str, Any]) -> tuple:
    """Extract prefix and numeric parts from record ID for sorting.
    Returns a tuple of (prefix, numeric_id) for consistent sorting."""
    id_str = str(record.get("id", ""))

    # If empty ID, return lowest priority
    if not id_str:
        return ("", 0)

    # Split into prefix and number parts
    parts = id_str.split("_")

    if len(parts) >= 2:
        # Handle cases like "exec_simple_84"
        try:
            numeric_part = int(parts[-1])  # Get last part as number
            prefix = "_".join(parts[:-1])  # Join all previous parts as prefix
            return (prefix, numeric_part)
        except ValueError:
            pass

    # Fallback: extract any numbers found
    try:
        numeric_part = int("".join(filter(str.isdigit, id_str)))
        prefix = "".join(filter(str.isalpha, id_str))
        return (prefix, numeric_part)
    except ValueError:
        return (id_str, 0)  # If no numbers found, use full string as prefix


def sort_by_numeric_id(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort records by their prefix first, then by numeric ID."""
    return sorted(records, key=extract_numeric_id)


def sample_records_with_answers(
    records: Union[List[Dict[str, Any]], Dict[str, Any]],
    answers: List[Dict[str, Any]],
    sample_ratio: float = 0.05,
) -> tuple:
    """Sample records while ensuring they have corresponding answers.
    Returns sampled records and their corresponding answers."""
    # Get IDs from answers
    answer_ids = get_answer_ids(answers)

    # Filter records to only those with answers
    valid_records = filter_records_with_answers(records, answer_ids)

    # Create a mapping of IDs to answers for quick lookup
    answer_map = {answer["id"]: answer for answer in answers}

    # Sample from valid records
    num_samples = max(1, int(len(valid_records) * sample_ratio))
    sampled_records = random.sample(valid_records, num_samples)

    # Sort sampled records by numeric ID
    sampled_records = sort_by_numeric_id(sampled_records)

    # Get corresponding answers in the same order
    sampled_answers = []
    for record in sampled_records:
        if record["id"] in answer_map:
            sampled_answers.append(answer_map[record["id"]])

    # Verify lengths match
    if len(sampled_records) != len(sampled_answers):
        print(
            f"Warning: Sampled records ({len(sampled_records)}) and answers ({len(sampled_answers)}) lengths don't match"
        )
        # Take the minimum length to ensure they match
        min_len = min(len(sampled_records), len(sampled_answers))
        sampled_records = sampled_records[:min_len]
        sampled_answers = sampled_answers[:min_len]

    # Filter answers to only those matching sampled records
    filtered_answers = [answer for answer in answers if answer.get("id") in sampled_ids]
    sorted_answers = sort_by_numeric_id(filtered_answers)

    return sampled_records, sorted_answers


def process_directory(src_dir: str, dest_dir: str, sample_rate: float = 0.05) -> None:
    """Process all JSON and JSONL files in a directory."""
    src_path = Path(src_dir)
    dest_path = Path(dest_dir)

    if not src_path.exists():
        print(f"Source directory {src_dir} does not exist")
        return

    # Create destination directory if it doesn't exist
    os.makedirs(dest_path, exist_ok=True)

    # Process all files in the directory
    for file_path in src_path.glob("*"):
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in [".json", ".jsonl"]:
            continue

        print(f"Processing {file_path}")

        try:
            # Load records based on file extension
            if file_path.suffix.lower() == ".jsonl":
                records = load_jsonl_file(str(file_path))

            # Check if possible answers exist
            possible_answer_dir = os.path.join(src_dir, "possible_answer")
            possible_answer_file = os.path.join(possible_answer_dir, file_path.name)

            if os.path.exists(possible_answer_file):
                # Load possible answers
                possible_answers = load_jsonl_file(possible_answer_file)

                # Sample records and get matching answers
                sampled_records, filtered_answers = sample_records_with_answers(
                    records, possible_answers, sample_rate
                )

                # Save sampled records
                dest_file = dest_path / file_path.name
                save_jsonl_file(sampled_records, str(dest_file))
                print(f"Saved sampled records to {dest_file}")

                # Save filtered answers
                dest_answer_dir = os.path.join(dest_dir, "possible_answer")
                os.makedirs(dest_answer_dir, exist_ok=True)
                dest_answer_file = os.path.join(dest_answer_dir, file_path.name)
                save_jsonl_file(filtered_answers, dest_answer_file)
                print(f"Saved filtered answers to {dest_answer_file}")
            else:
                # If no possible answers exist, just sample records
                sampled_records = random.sample(
                    records, max(1, int(len(records) * sample_rate))
                )
                dest_file = dest_path / file_path.name
                save_jsonl_file(sampled_records, str(dest_file))
                print(f"Saved sampled records to {dest_file}")

        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")


def main():
    # Add argument parsing
    parser = argparse.ArgumentParser(
        description="Sample data with a specified percentage"
    )
    parser.add_argument(
        "--percentage",
        type=float,
        default=5.0,
        help="Percentage of data to sample (between 0 and 100)",
    )
    args = parser.parse_args()

    # Convert percentage to ratio
    sample_ratio = args.percentage / 100.0

    if not 0 < sample_ratio <= 1:
        raise ValueError("Percentage must be between 0 and 100")

    # Base directories
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "berkeley-function-call-leaderboard", "data")
    sample_dir = os.path.join(
        base_dir, "berkeley-function-call-leaderboard", f"data_{int(args.percentage)}"
    )

    # Create destination directory if it doesn't exist
    os.makedirs(sample_dir, exist_ok=True)

    # Process all JSON files in the data directory
    for file_path in Path(data_dir).glob("BFCL_v3_*.json"):
        if not file_path.is_file():
            continue

        print(f"Processing {file_path}")

        try:
            # Load records as JSONL
            records = load_jsonl_file(str(file_path))

            # Check if possible answers exist
            possible_answer_dir = os.path.join(data_dir, "possible_answer")
            possible_answer_file = os.path.join(possible_answer_dir, file_path.name)

            if os.path.exists(possible_answer_file):
                # Load possible answers
                possible_answers = load_jsonl_file(possible_answer_file)

                # Sample records and get matching answers
                sampled_records, filtered_answers = sample_records_with_answers(
                    records, possible_answers, sample_ratio
                )

                # Save sampled records
                dest_file = Path(sample_dir) / file_path.name
                save_jsonl_file(sampled_records, str(dest_file))
                print(f"Saved sampled records to {dest_file}")

                # Save filtered answers
                dest_answer_dir = os.path.join(sample_dir, "possible_answer")
                os.makedirs(dest_answer_dir, exist_ok=True)
                dest_answer_file = os.path.join(dest_answer_dir, file_path.name)
                save_jsonl_file(filtered_answers, dest_answer_file)
                print(f"Saved filtered answers to {dest_answer_file}")
            else:
                # If no possible answers exist, sample and sort records
                sampled_records = random.sample(
                    records, max(1, int(len(records) * sample_ratio))
                )
                sampled_records = sort_by_numeric_id(sampled_records)
                dest_file = Path(sample_dir) / file_path.name
                save_jsonl_file(sampled_records, str(dest_file))
                print(f"Saved sampled records to {dest_file}")

        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")

    # Copy special directories if they exist
    special_dirs = ["multi_turn_func_doc"]
    for dir_name in special_dirs:
        src_dir = os.path.join(data_dir, dir_name)
        if os.path.exists(src_dir):
            dest_dir = os.path.join(sample_dir, dir_name)
            shutil.copytree(src_dir, dest_dir, dirs_exist_ok=True)
            print(f"Copied directory {dir_name}")

    # Copy README.md if it exists
    readme_path = os.path.join(data_dir, "README.md")
    if os.path.exists(readme_path):
        shutil.copy2(readme_path, os.path.join(sample_dir, "README.md"))
        print("Copied README.md")


if __name__ == "__main__":
    main()
