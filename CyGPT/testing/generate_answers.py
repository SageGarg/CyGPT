#!/usr/bin/env python3
"""
Generate answers for questions in cygpt_blooms_questions_final.csv
and save them back to the same file with a new 'Answer' column.
"""
import sys
import csv
from pathlib import Path
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))

from src.indexer import load_index
from src.retriever import retrieve
from src.answerer import answer
from config import BASE_DIR


def generate_answers_for_csv(csv_path: Path, output_path: Path | None = None):
    """
    Read questions from CSV, generate answers, and save to output file.
    
    Args:
        csv_path: Path to input CSV file
        output_path: Path to save output CSV (default: same as input with _answered suffix)
    """
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        sys.exit(1)
    
    if output_path is None:
        output_path = csv_path.parent / (csv_path.stem + "_answered.csv")
    
    # Load the index
    print("📚 Loading FAISS index...")
    try:
        index, bm25, chunks = load_index()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("   Run: python ingest.py")
        sys.exit(1)
    
    # Read CSV
    print(f"📖 Reading questions from: {csv_path}")
    questions_data = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        questions_data = list(reader)
    
    print(f"✅ Found {len(questions_data)} questions")
    
    # Generate answers
    print(f"\n🚀 Generating answers...\n")
    results = []
    
    for i, row in enumerate(tqdm(questions_data, desc="Processing"), 1):
        question = row.get('Question', '').strip()
        
        if not question:
            row['Answer'] = "❌ No question provided"
            results.append(row)
            continue
        
        try:
            # Retrieve relevant chunks
            chunks_retrieved = retrieve(
                question=question,
                index=index,
                bm25=bm25,
                chunks=chunks,
                expand=True
            )
            
            # Generate answer
            answer_text = answer(
                question=question,
                chunks=chunks_retrieved,
                history=[]
            )
            
            row['Answer'] = answer_text
            
        except Exception as e:
            row['Answer'] = f"⚠️ Error generating answer: {str(e)}"
        
        results.append(row)
    
    # Save to CSV
    print(f"\n💾 Saving answers to: {output_path}")
    
    if results:
        fieldnames = list(results[0].keys())
        # Ensure 'Answer' is the last column
        if 'Answer' in fieldnames:
            fieldnames.remove('Answer')
        fieldnames.append('Answer')
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        
        print(f"✅ Saved {len(results)} answers to: {output_path}")
    
    return output_path


if __name__ == "__main__":
    # Default to the testing directory CSV
    csv_file = BASE_DIR / "testing" / "cygpt_blooms_questions_final.csv"
    
    if len(sys.argv) > 1:
        csv_file = Path(sys.argv[1])
    
    output_file = None
    if len(sys.argv) > 2:
        output_file = Path(sys.argv[2])
    
    result = generate_answers_for_csv(csv_file, output_file)
    print(f"\n✨ Done! Check the output file for results.")
