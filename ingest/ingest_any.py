from pathlib import Path
from typing import Optional, List
from .schema import CanonicalProp
from .csv_loaders import load_playerprops_csv
from .excel_loaders import load_playerprops_excel

def ingest_playerprops(path: str | Path, sport: Optional[str] = None) -> List[CanonicalProp]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    ext = path.suffix.lower()
    if ext == '.csv':
        return load_playerprops_csv(path, sport_hint=sport)
    elif ext in ['.xlsx', '.xls']:
        return load_playerprops_excel(path, sport_hint=sport)
    else:
        raise ValueError(f"Unsupported format: {ext}")
