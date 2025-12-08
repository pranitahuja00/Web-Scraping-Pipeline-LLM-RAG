# scraper_pipeline/writer.py

from __future__ import annotations
import json
from pathlib import Path
from typing import Iterable, Union
from .models import Document


def write_documents_jsonl(
    documents: Iterable[Document],
    output_path: Union[str, Path],
) -> Path:
    """
    Write an iterable of Document objects to a JSONL file.

    - Each line is one JSON object (serialized Document).
    - Uses Document.to_serializable_dict() to ensure fields like datetime
      are converted to JSON-safe formats (e.g., ISO strings).

    Returns:
        Path to the written JSONL file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        for doc in documents:
            record = doc.to_serializable_dict()
            json_line = json.dumps(record, ensure_ascii=False)
            f.write(json_line + "\n")

    return output_path
