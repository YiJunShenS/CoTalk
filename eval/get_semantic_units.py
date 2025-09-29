import re
import json
import os
import pandas as pd
from tqdm import tqdm
import argparse

from llm.llm import llm
from prompt.PROMPT_TEMPLATE import Prompt_Caption_Refinement, Prompt_Semantic_Unit_Parsing


def parse_args():
    """
    Parse command-line arguments for semantic unit extraction.

    Returns:
        argparse.Namespace: Parsed arguments with attributes:
            - annotation_json_folder (str): Input folder path containing JSON files.
            - save_folder (str): Output folder path to save results.
    """

    parser = argparse.ArgumentParser(
        description="Extract structured semantic units from image captions in JSON files."
    )
    parser.add_argument("--annotation_json_folder", type=str, default="output/annotation_json", help="Path to input folder containing JSON annotation files.")
    parser.add_argument("--save_folder", type=str, default="output/semantic_units_json", help="Path to save processed JSON files.")
    return parser.parse_args()

def load_json(file_path):
    """Load JSON file safely."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load JSON: {file_path}, error: {e}")


def save_json(data, file_path):
    """Safely save dictionary to JSON file."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise RuntimeError(f"Failed to save JSON: {file_path}, error: {e}")

def extract_json_content(llm_output) :
    """
    Extract JSON content from LLM output that may contain markdown-style code blocks.
    """
    pattern = r"```json\s*(\{[\s\S]*?\})\s*```|```json\s*(\[?[\s\S]*\]?)\s*```"
    match = re.search(pattern, llm_output, re.DOTALL | re.IGNORECASE)

    json_str = match.group(1) or match.group(2) if match else llm_output.strip()

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from LLM output: {e}\nRaw output:\n{llm_output}")

def refine_caption(caption):
    """
    Use LLM to refine caption: fix typos, remove redundancy, ensure clarity.
    """
    prompt = Prompt_Caption_Refinement.format(caption=caption)
    response = llm(prompt)
    parsed = extract_json_content(response)
    return parsed.get("caption", caption)  # fallback to original if missing

def parse_semantic_units(refined_caption):
    """
    Parse refined caption into structured semantic units.
    """
    prompt = Prompt_Semantic_Unit_Parsing.format(caption=refined_caption)
    response = llm(prompt)
    return extract_json_content(response)


def process_caption(caption):
    """
    Full pipeline: refine + parse.
    """
    if not caption or not caption.strip():
        return []
    try:
        refined = refine_caption(caption)
        units = parse_semantic_units(refined)
        return units
    except Exception as e:
        print(f"[Error] Caption processing failed: {e}")
        return []
        
def batch_process_annotations(
    annotation_json_folder,
    save_folder
):
    """
    Process all JSON files in the input folder, extract semantic units, and save results.

    Args:
        annotation_json_folder (str): Path to folder containing input JSON files.
        save_folder (str): Path to folder for saving output JSON files.
    """
    if not os.path.exists(annotation_json_folder):
        raise FileNotFoundError(f"Input folder not found: {annotation_json_folder}")

    os.makedirs(save_folder, exist_ok=True)

    json_files = [f for f in os.listdir(annotation_json_folder) if f.endswith("json")]
    
    if not json_files:
        print(f"No (json) files found in {annotation_json_folder}")
        return

    failed_files = []

    for filename in tqdm(json_files, desc="Processing files"):
        file_path = os.path.join(annotation_json_folder, filename)
        save_path = os.path.join(save_folder, filename)

        try:
            data = load_json(file_path)
            caption = data.get("overall_annotation", "").strip()

            if not caption:
                print(f"Skipped: {filename} - missing or empty 'overall_annotation'")
            else:
                semantic_units = process_caption(caption)
                data["semantic_units"] = semantic_units
                save_json(data, save_path)

        except Exception as e:
            print(f"Failed to process {filename}: {e}")
            failed_files.append(filename)

    # Final report
    print(f"\n✅ Processing complete.")
    print(f"Total files: {len(json_files)}")
    print(f"Success: {len(json_files) - len(failed_files)}")
    if failed_files:
        print(f"Failed: {len(failed_files)} → {failed_files}")
            

if __name__ == "__main__":
    args = parse_args()
    batch_process_annotations(
        annotation_json_folder=args.annotation_json_folder,
        save_folder=args.save_folder,
    )
    

    




