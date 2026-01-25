from __future__ import annotations

import argparse
import json

from src.pipeline import predict_row, train


def main() -> None:
    ap = argparse.ArgumentParser(description='Single-command demo: train + predict')
    ap.add_argument('--data', required=True, help='Path to CSV dataset')
    ap.add_argument('--target', default='target', help='Target column name')
    ap.add_argument('--row', required=True, help='JSON dict for a single row')
    args = ap.parse_args()
    result = train(data_path=args.data, target_col=args.target)
    print('TRAIN:', json.dumps(result['metrics'], indent=2))
    row = json.loads(args.row)
    pred = predict_row(row)
    print('PREDICT:', json.dumps({'probability': pred.probability, 'label': pred.label, 'meta': pred.meta}, indent=2))


if __name__ == '__main__':
    main()
