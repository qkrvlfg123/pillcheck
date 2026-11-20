"""
01_prepare_data.py — 원본 DDI 데이터를 내려받아 정제하고 약물별 지문을 계산한다.

실행:  python src/01_prepare_data.py

산출물 (data/processed/)
- drugs.csv          약물 1개당 1행: drug_idx, drug_id, smiles, group_id
- fingerprints.npy   (약물 수, 1024) 0/1 배열. 행 순서 = drug_idx
- positives.npy      상호작용이 등록된 쌍 (i, j), i < j
- data_report.json   정제 과정에서 걸러낸 건수 (README 에 그대로 인용)
"""
import json
from urllib.request import urlretrieve

import numpy as np
import pandas as pd

from common import DATA_URL, PROC_DIR, RAW_DIR, RAW_FILE, canonical_smiles, smiles_to_fingerprint


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    if not RAW_FILE.exists():
        print("DrugBank DDI 데이터 다운로드 중 (약 44MB)...")
        urlretrieve(DATA_URL, RAW_FILE)

    # 컬럼: ID1, ID2 = DrugBank 약물 ID / X1, X2 = SMILES / Y = 상호작용 유형(86종) / Map = 유형 설명
    raw = pd.read_csv(RAW_FILE, sep="\t")
    report = {"원본 행 수": len(raw)}

    # ---- 1) 약물 목록 만들기 ---------------------------------------------------
    drugs = pd.concat([
        raw[["ID1", "X1"]].set_axis(["drug_id", "smiles"], axis=1),
        raw[["ID2", "X2"]].set_axis(["drug_id", "smiles"], axis=1),
    ]).drop_duplicates("drug_id").reset_index(drop=True)
    report["약물 수 (원본)"] = len(drugs)

    # ---- 2) 지문 계산. 해석 불가 SMILES 는 제외 ---------------------------------
    fps = [smiles_to_fingerprint(s) for s in drugs["smiles"]]
    valid = np.array([fp is not None for fp in fps])
    report["해석 불가 SMILES 로 제외한 약물"] = int((~valid).sum())
    drugs = drugs[valid].reset_index(drop=True)
    fingerprints = np.vstack([fp for fp in fps if fp is not None])

    # ---- 3) 구조가 같은 약물 묶기 (누수 방지용 그룹) -----------------------------
    # 같은 분자가 서로 다른 ID 로 등록되어 있을 수 있다. 이 둘이 학습/시험에 갈라져 들어가면
    # "처음 보는 약"이라고 평가했지만 사실은 본 구조인 셈이 된다(데이터 누수).
    # 표준화한 SMILES 가 같으면, 그리고 지문이 완전히 같으면 같은 group_id 를 줘서
    # 분할할 때 항상 같은 쪽에 들어가게 한다.
    drugs["canonical"] = drugs["smiles"].map(canonical_smiles)
    fp_key = [fp.tobytes() for fp in fingerprints]
    drugs["group_id"] = pd.factorize(pd.Series(fp_key))[0]
    report["표준 SMILES 가 중복인 약물"] = int(drugs["canonical"].duplicated().sum())
    report["지문이 완전히 같은 약물 (그룹으로 묶음)"] = int(drugs["group_id"].duplicated().sum())
    drugs["drug_idx"] = np.arange(len(drugs))
    idx_of = dict(zip(drugs["drug_id"], drugs["drug_idx"]))

    # ---- 4) 양성 쌍 정리 ------------------------------------------------------
    # (A,B) 와 (B,A) 는 같은 쌍이므로 작은 번호를 앞에 두어 통일한 뒤 중복 제거.
    # 같은 쌍이 상호작용 유형만 달리해 여러 번 나오는 경우가 있어서 필요하다.
    # 이 중복을 그대로 두면 같은 쌍이 학습과 시험에 동시에 들어갈 수 있다(누수).
    keep = raw["ID1"].isin(idx_of) & raw["ID2"].isin(idx_of)
    i = raw.loc[keep, "ID1"].map(idx_of).to_numpy()
    j = raw.loc[keep, "ID2"].map(idx_of).to_numpy()
    pairs = np.unique(np.column_stack([np.minimum(i, j), np.maximum(i, j)]), axis=0)
    pairs = pairs[pairs[:, 0] != pairs[:, 1]]          # 자기 자신과의 쌍 제거
    report["제외된 약물이 포함되어 빠진 행"] = int((~keep).sum())
    report["중복 쌍(유형만 다른 같은 쌍) 제거"] = int(keep.sum() - len(pairs))
    report["약물 수 (최종)"] = len(drugs)
    report["상호작용 쌍 (최종, 양성)"] = len(pairs)

    n = len(drugs)
    n_all = n * (n - 1) // 2
    report["가능한 전체 쌍"] = n_all
    report["양성 비율 (%)"] = round(100 * len(pairs) / n_all, 2)
    report["상호작용 유형 수"] = int(raw["Y"].nunique())

    drugs[["drug_idx", "drug_id", "smiles", "group_id"]].to_csv(PROC_DIR / "drugs.csv", index=False)
    np.save(PROC_DIR / "fingerprints.npy", fingerprints)
    np.save(PROC_DIR / "positives.npy", pairs.astype(np.int32))
    (PROC_DIR / "data_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    for k, v in report.items():
        print(f"{k:<40} {v:>12,}" if isinstance(v, int) else f"{k:<40} {v:>12}")
    print(f"지문 1개당 켜진 비트 수: 평균 {fingerprints.sum(1).mean():.1f} / {fingerprints.shape[1]}")


if __name__ == "__main__":
    main()
