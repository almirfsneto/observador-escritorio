"""CLI: somente demonstra e analisa dados ja existentes. Nao captura Windows."""
import argparse
import json
from pathlib import Path
from .store import EventStore
from .discovery import discover_patterns
from .sample import generate_sample

def main() -> None:
    p = argparse.ArgumentParser(description="Observador Escritorio - base offline de desenvolvimento")
    sub = p.add_subparsers(dest="command", required=True)
    s1 = sub.add_parser("demo", help="grava 36 eventos sinteticos em SQLite")
    s1.add_argument("--db", default="demo.sqlite3")
    s2 = sub.add_parser("analyze", help="identifica candidatos a microtarefas no banco")
    s2.add_argument("--db", required=True)
    s2.add_argument("--out", default="analise.json")
    s3 = sub.add_parser("export", help="exporta JSONL com campos do contrato")
    s3.add_argument("--db", required=True)
    s3.add_argument("--out", default="eventos.jsonl")
    args = p.parse_args()
    store = EventStore(args.db)
    try:
        if args.command == "demo":
            n = sum(store.insert(e) for e in generate_sample())
            print(json.dumps({"inserted":n,"total":len(store.list_events()),"capture_real":False}))
        elif args.command == "analyze":
            pats = discover_patterns(store.list_events(), min_count=3)
            Path(args.out).write_text(json.dumps(pats, indent=2, ensure_ascii=False), encoding="utf-8")
            print(json.dumps({"patterns":len(pats), "file":args.out,"capture_real":False}))
        else:
            n=store.export_jsonl(args.out)
            print(json.dumps({"exported":n,"file":args.out}))
    finally:
        store.close()

if __name__ == "__main__":
    main()
