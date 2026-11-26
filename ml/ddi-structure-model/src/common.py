"""
common.py — 데이터 준비·학습·예측 스크립트가 함께 쓰는 경로와 피처 함수.

피처 설계 두 가지
1) 약물 1개 → Morgan 지문(fingerprint) 1024비트
2) 약물 쌍 → 두 지문을 "순서에 무관하게" 합친 2048차원 벡터
"""
from pathlib import Path

import numpy as np
from rdkit import Chem, RDLogger
from rdkit.Chem import rdFingerprintGenerator

RDLogger.DisableLog("rdApp.*")  # 잘못된 SMILES 경고는 직접 세어서 보고하므로 로그는 끈다

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROC_DIR = ROOT / "data" / "processed"
RESULT_DIR = ROOT / "results"
MODEL_DIR = ROOT / "models"

# Therapeutics Data Commons(TDC)가 배포하는 DrugBank DDI 데이터 (로그인·키 불필요)
DATA_URL = "https://dataverse.harvard.edu/api/access/datafile/4139573"
RAW_FILE = RAW_DIR / "drugbank_ddi.tab"

N_BITS = 1024   # 지문 길이
RADIUS = 2      # 원자 주변 몇 결합까지 볼 것인가 (2 = ECFP4 에 해당, 가장 널리 쓰는 설정)

_generator = rdFingerprintGenerator.GetMorganGenerator(radius=RADIUS, fpSize=N_BITS)


def smiles_to_fingerprint(smiles: str):
    """SMILES 문자열 → 0/1 로 된 길이 1024 배열. 해석할 수 없는 SMILES 면 None.

    Morgan 지문이란?
      분자의 각 원자를 중심으로 반경 2 결합 이내의 부분 구조(작용기, 고리 등)를 모두 뽑아
      해시해서, 그 부분 구조가 "있다(1)/없다(0)"로 표시한 고정 길이 벡터.
    왜 이것을 썼나?
      - 약물 상호작용은 대사 효소(CYP)나 수용체에 대한 결합처럼 특정 부분 구조와 관련이 깊다.
      - 분자 크기와 상관없이 길이가 같아 표 형태 모델에 바로 넣을 수 있다.
      - 구조만 있으면 계산되므로, 상호작용 정보가 전혀 없는 "새 약"에도 적용할 수 있다.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return _generator.GetFingerprintAsNumPy(mol).astype(np.uint8)


def canonical_smiles(smiles: str):
    """같은 분자를 한 가지 표기로 통일. (같은 구조가 다른 ID 로 중복 등록됐는지 찾는 데 사용)"""
    mol = Chem.MolFromSmiles(smiles)
    return None if mol is None else Chem.MolToSmiles(mol)


def pair_features(fp_a: np.ndarray, fp_b: np.ndarray) -> np.ndarray:
    """두 약물의 지문 → 쌍 피처 (2048차원).

    [앞 1024칸] a + b      : 0 = 둘 다 없음, 1 = 한쪽만 있음, 2 = 둘 다 있음
    [뒤 1024칸] |a - b|    : 1 = 한쪽에만 있는 구조 (두 약의 '차이')

    왜 단순히 이어 붙이지(concat) 않았나?
      (A, B) 와 (B, A) 는 같은 약물 쌍인데, 이어 붙이면 서로 다른 입력이 되어
      모델이 입력 순서에 따라 다른 답을 낼 수 있다. 합과 차의 절댓값은 순서를 바꿔도 값이 같다.
      → 데이터를 두 배로 늘리지 않고도 대칭성이 보장된다.

    fp_a, fp_b 는 (쌍 개수, 1024) 모양의 배열.
    """
    a = fp_a.astype(np.int8)
    b = fp_b.astype(np.int8)
    return np.hstack([a + b, np.abs(a - b)]).astype(np.uint8)
