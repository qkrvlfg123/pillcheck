"""
predict.py — 두 약물의 SMILES 를 넣으면 상호작용 등록 가능성 점수를 돌려준다. (연구용 데모)

실행 예 (와파린 + 이부프로펜):
  python src/predict.py "CC(=O)CC(C1=CC=CC=C1)C1=C(O)C2=CC=CC=C2OC1=O" "CC(C)CC1=CC=C(C=C1)C(C)C(O)=O"

주의
- 이 점수는 "DrugBank 에 상호작용으로 등록된 쌍과 구조가 닮은 정도"이지 임상적 위험도가 아니다.
- PillCheck 의 판정 원칙은 "판정은 공식 데이터(DUR)가 한다"이다. 이 모델은 그 판정을 대체하지 않으며,
  서비스 엔진(packages/shared)에 연결되어 있지 않다.
- 학습 데이터에 없던 새 약일수록 신뢰도가 낮다 (README 의 S2/S3 결과 참고).
"""
import sys

import lightgbm as lgb
import numpy as np

from common import MODEL_DIR, pair_features, smiles_to_fingerprint


def predict_pair(smiles_a: str, smiles_b: str) -> float:
    fa, fb = smiles_to_fingerprint(smiles_a), smiles_to_fingerprint(smiles_b)
    if fa is None or fb is None:
        raise ValueError("SMILES 를 해석할 수 없습니다.")
    model_file = MODEL_DIR / "ddi_lgbm_seed0.txt"
    if not model_file.exists():
        raise FileNotFoundError("모델이 없습니다. 먼저 `python src/02_train_evaluate.py` 를 실행하세요.")
    # 경로에 한글이 있어도 읽히도록 파일 내용을 문자열로 넘긴다
    booster = lgb.Booster(model_str=model_file.read_text(encoding="utf-8"))
    x = pair_features(fa[None, :], fb[None, :]).astype(np.float32)
    return float(booster.predict(x)[0])


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    a, b = sys.argv[1], sys.argv[2]
    p_ab, p_ba = predict_pair(a, b), predict_pair(b, a)
    assert abs(p_ab - p_ba) < 1e-9, "입력 순서에 따라 결과가 달라짐 (대칭성 위반)"
    print(f"상호작용 등록 가능성 점수: {p_ab:.3f}  (입력 순서를 바꿔도 동일: {p_ba:.3f})")
    print("※ 연구용 참고 점수입니다. 실제 복약 판단은 DUR 과 의사·약사 상담을 따르세요.")
