"""
02_train_evaluate.py — 분할, 베이스라인, 모델 학습, 평가를 한 번에 수행한다.

실행:  python src/02_train_evaluate.py            (시드 3개 반복, 수 분 소요)
       python src/02_train_evaluate.py --seeds 0  (빠른 확인용)

이 스크립트가 답하려는 질문
  Q1. 구조(SMILES)만으로 상호작용 여부를 맞힐 수 있는가?
  Q2. 그 성능은 "처음 보는 약"에도 유지되는가? (= 데이터 누수 없이 측정했는가)
  Q3. 구조를 쓰지 않는 단순한 방법(베이스라인)보다 얼마나 나은가?
  Q4. 양성이 13%뿐인 불균형을 어떻게 다루고, 어떤 지표로 봐야 하는가?

평가 상황 3가지 (약물 단위로 나눈다)
  S1 둘 다 학습에서 본 약   : 기존 약끼리의 아직 등록되지 않은 조합
  S2 한쪽만 새 약           : 신약이 기존 약과 함께 쓰이는 경우
  S3 둘 다 새 약            : 가장 어려운 경우 (cold start)
  ※ 쌍을 무작위로 나누면 S1 만 측정하게 된다. 그 숫자를 "새 조합 예측 성능"이라고
    보고하면 과대평가다. 그래서 세 상황을 따로 잰다.
"""
import argparse
import json

import lightgbm as lgb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, f1_score,
                             precision_recall_curve, precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import GroupShuffleSplit

from common import MODEL_DIR, PROC_DIR, RESULT_DIR, pair_features

REGIMES = {"S1": "S1 둘 다 본 약", "S2": "S2 한쪽만 새 약", "S3": "S3 둘 다 새 약"}
MODELS = ["무작위 수준 (양성 비율)", "베이스라인: 약물별 빈도", "구조 모델 (LightGBM)", "구조 모델 + 가중치"]

# 표본 크기: 전체 145만 쌍을 다 쓰면 메모리·시간이 과하므로 무작위 표본을 쓴다.
# 무작위로 뽑기 때문에 양성 비율(약 13%)은 원래 분포 그대로 유지된다.
N_TRAIN, N_VAL, N_TEST_S1, N_TEST_S2 = 300_000, 40_000, 60_000, 60_000


# =============================================================================
# 1. 분할
# =============================================================================
def split_drugs(groups: np.ndarray, seed: int):
    """약물을 학습 70% / 검증 10% / 시험 20% 로 나눈다. 반환값은 약물별 역할 배열.

    GroupShuffleSplit 을 쓰는 이유: 구조가 완전히 같은 약물(group_id 동일)이
    학습과 시험에 갈라져 들어가지 않게 하려고. 갈라지면 '새 약' 평가가 오염된다.
    """
    idx = np.arange(len(groups))
    outer = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)
    rest, test = next(outer.split(idx, groups=groups))
    inner = GroupShuffleSplit(n_splits=1, test_size=0.125, random_state=seed)  # 0.8 × 0.125 = 0.1
    tr, va = next(inner.split(rest, groups=groups[rest]))
    role = np.empty(len(groups), dtype="U5")
    role[rest[tr]], role[rest[va]], role[test] = "train", "val", "test"
    return role


def build_pair_sets(n_drugs: int, positives: np.ndarray, role: np.ndarray, rng):
    """가능한 모든 쌍을 만들고 라벨을 붙인 뒤, 약물 역할에 따라 학습/검증/시험 세트로 나눈다."""
    i, j = np.triu_indices(n_drugs, k=1)                       # 모든 (i < j) 쌍
    # 라벨: 등록된 쌍이면 1, 아니면 0.
    # ※ 0 은 "상호작용 없음이 확인됨"이 아니라 "DB 에 등록되지 않음"이다 (한계로 README 에 명시).
    pos_key = positives[:, 0].astype(np.int64) * n_drugs + positives[:, 1]
    y = np.isin(i.astype(np.int64) * n_drugs + j, pos_key).astype(np.int8)

    ri, rj = role[i], role[j]
    both_train = (ri == "train") & (rj == "train")
    n_test = (ri == "test").astype(int) + (rj == "test").astype(int)
    has_val = (ri == "val") | (rj == "val")

    def take(mask, n=None):
        idx = np.flatnonzero(mask)
        if n is not None and len(idx) > n:
            idx = rng.choice(idx, size=n, replace=False)
        return {"i": i[idx], "j": j[idx], "y": y[idx]}

    # 학습 약물끼리의 쌍을 섞은 뒤, 앞부분은 S1 시험용으로 떼어 두고 나머지에서 학습 표본을 뽑는다.
    # 한 번 섞어서 자르므로 같은 쌍이 학습과 S1 시험에 동시에 들어가는 일은 없다.
    tt = rng.permutation(np.flatnonzero(both_train))
    s1, train = tt[:N_TEST_S1], tt[N_TEST_S1:N_TEST_S1 + N_TRAIN]
    sets = {
        "train": {"i": i[train], "j": j[train], "y": y[train]},
        "S1": {"i": i[s1], "j": j[s1], "y": y[s1]},
        # 검증: 검증 약물이 낀 쌍(시험 약물은 제외). '새 약' 상황을 흉내 내어 조기 종료·임계값을 정한다.
        "val": take(has_val & (n_test == 0), N_VAL),
        "S2": take((n_test == 1) & ~has_val, N_TEST_S2),
        "S3": take(n_test == 2),
    }
    return sets


def to_features(s: dict, fp: np.ndarray, chunk: int = 50_000):
    """쌍 목록 → 희소 행렬. 지문은 대부분 0 이라 희소 형식이 메모리를 크게 아낀다."""
    parts = [sparse.csr_matrix(pair_features(fp[s["i"][k:k + chunk]], fp[s["j"][k:k + chunk]]))
             for k in range(0, len(s["y"]), chunk)]
    return sparse.vstack(parts).astype(np.float32)


# =============================================================================
# 2. 모델
# =============================================================================
def frequency_baseline(sets):
    """베이스라인: 구조를 전혀 쓰지 않고 '각 약이 학습 데이터에서 얼마나 자주 상호작용했는가'만 쓴다.

    왜 이 베이스라인인가?
      상호작용이 많은 약(와파린 등)은 아무 약과 짝지어도 양성일 확률이 높다.
      이 정보만으로도 S1 에서는 성능이 꽤 나온다. 구조 모델이 이것보다 낫지 않다면
      '구조를 학습했다'고 말할 수 없다. 반대로 새 약에는 빈도 정보가 없으므로
      S2/S3 에서는 이 베이스라인이 무력해진다 → 구조 피처가 필요한 이유를 보여 준다.
    """
    tr = sets["train"]
    n = max(tr["i"].max(), tr["j"].max(), *[max(s["i"].max(), s["j"].max()) for s in sets.values()]) + 1
    pos = np.bincount(tr["i"], weights=tr["y"], minlength=n) + np.bincount(tr["j"], weights=tr["y"], minlength=n)
    cnt = np.bincount(tr["i"], minlength=n) + np.bincount(tr["j"], minlength=n)
    prior = tr["y"].mean()
    # 학습에 한 번도 안 나온 약(새 약)은 전체 평균으로 채운다. 그 약에 대해 아는 것이 없기 때문.
    rate = np.where(cnt > 0, pos / np.maximum(cnt, 1), prior)

    def feats(s):
        a, b = rate[s["i"]], rate[s["j"]]
        return np.column_stack([np.minimum(a, b), np.maximum(a, b), a * b])

    clf = LogisticRegression(max_iter=1000).fit(feats(tr), tr["y"])
    return {k: clf.predict_proba(feats(s))[:, 1] for k, s in sets.items()}


def train_lgbm(X, sets, weighted: bool, seed: int):
    """LightGBM 학습. weighted=True 면 양성에 (음성 수 / 양성 수) 만큼 가중치를 준다.

    왜 LightGBM 인가: 2048개의 0/1/2 값 피처처럼 희소한 표 데이터에서 빠르고,
      '구조 A 가 있고 구조 B 가 없을 때' 같은 피처 조합을 트리가 자연스럽게 학습한다.
    조기 종료: 검증 세트의 PR-AUC 가 30라운드 동안 좋아지지 않으면 멈춘다 (과적합 방지).
    """
    y = sets["train"]["y"]
    params = dict(
        objective="binary", learning_rate=0.1, num_leaves=63, n_estimators=600,
        colsample_bytree=0.3, subsample=0.8, subsample_freq=1, min_child_samples=20,
        random_state=seed, n_jobs=-1, verbose=-1,
        # 조기 종료 기준을 PR-AUC 하나로 고정한다. 지정하지 않으면 기본 지표인 logloss 가 기준이 되는데,
        # 양성 가중치를 주면 예측 확률이 전체적으로 올라가 검증 logloss 가 처음부터 나빠져서
        # 1라운드 만에 멈춰 버린다 (실제로 겪은 문제).
        metric="average_precision",
    )
    if weighted:
        params["scale_pos_weight"] = (y == 0).sum() / (y == 1).sum()
    model = lgb.LGBMClassifier(**params)
    model.fit(X["train"], y, eval_X=X["val"], eval_y=sets["val"]["y"],
              callbacks=[lgb.early_stopping(30, verbose=False)])
    return model, {k: model.predict_proba(X[k])[:, 1] for k in X}


# =============================================================================
# 3. 평가
# =============================================================================
def best_f1_threshold(y, p):
    """검증 세트에서 F1 이 최대가 되는 임계값. (시험 세트로 정하면 누수이므로 검증 세트만 사용)"""
    prec, rec, thr = precision_recall_curve(y, p)
    f1 = 2 * prec[:-1] * rec[:-1] / np.maximum(prec[:-1] + rec[:-1], 1e-12)
    return float(thr[np.argmax(f1)])


def evaluate(y, p, thr):
    pred = (p >= thr).astype(int)
    return {
        "양성 비율": y.mean(),
        "PR-AUC": average_precision_score(y, p),
        "ROC-AUC": roc_auc_score(y, p) if len(np.unique(p)) > 1 else 0.5,
        "정밀도": precision_score(y, pred, zero_division=0),
        "재현율": recall_score(y, pred, zero_division=0),
        "F1": f1_score(y, pred, zero_division=0),
        "정확도": accuracy_score(y, pred),
        "임계값": thr,
    }


def run_seed(seed, drugs, fp, positives, keep_curves=False):
    rng = np.random.default_rng(seed)
    role = split_drugs(drugs["group_id"].to_numpy(), seed)
    sets = build_pair_sets(len(drugs), positives, role, rng)

    # ---- 누수 점검 (자동): 조건이 깨지면 여기서 멈춘다 ----
    key = lambda s: set((s["i"].astype(np.int64) * len(drugs) + s["j"]).tolist())
    assert not key(sets["train"]) & key(sets["S1"]), "학습과 S1 시험에 같은 쌍이 있음"
    train_drugs = set(np.flatnonzero(role == "train").tolist())
    used = set(sets["train"]["i"].tolist()) | set(sets["train"]["j"].tolist())
    assert used <= train_drugs, "학습 쌍에 검증/시험 약물이 섞여 있음"
    g = drugs["group_id"].to_numpy()
    assert not set(g[role == "train"]) & set(g[role == "test"]), "같은 구조가 학습과 시험에 나뉘어 있음"

    X = {k: to_features(s, fp) for k, s in sets.items()}
    prior = float(sets["train"]["y"].mean())
    preds = {MODELS[0]: {k: np.full(len(s["y"]), prior) for k, s in sets.items()},
             MODELS[1]: frequency_baseline(sets)}
    model_plain, preds[MODELS[2]] = train_lgbm(X, sets, weighted=False, seed=seed)
    model_w, preds[MODELS[3]] = train_lgbm(X, sets, weighted=True, seed=seed)

    rows = []
    for name, p in preds.items():
        thr = 0.5 if name == MODELS[0] else best_f1_threshold(sets["val"]["y"], p["val"])
        for r in REGIMES:
            y = sets[r]["y"]
            rows.append({"seed": seed, "모델": name, "상황": r, "쌍 수": len(y), **evaluate(y, p[r], thr),
                         "기준": "검증 F1 최대 임계값"})
            if name in MODELS[2:]:   # 불균형 처리 비교용: 임계값 0.5 를 그대로 썼을 때
                rows.append({"seed": seed, "모델": name, "상황": r, "쌍 수": len(y), **evaluate(y, p[r], 0.5),
                             "기준": "임계값 0.5"})
    info = {"seed": seed, "학습 약물": int((role == "train").sum()), "검증 약물": int((role == "val").sum()),
            "시험 약물": int((role == "test").sum()), "학습 쌍": len(sets["train"]["y"]),
            "학습 양성 비율": prior, "트리 수(기본)": model_plain.best_iteration_, "트리 수(가중치)": model_w.best_iteration_}
    curves = {r: {m: (sets[r]["y"], preds[m][r]) for m in MODELS[1:3]} for r in REGIMES} if keep_curves else None
    return pd.DataFrame(rows), info, curves, model_plain


# =============================================================================
# 4. 그림
# =============================================================================
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
COLORS = {MODELS[0]: "#b9b8b2", MODELS[1]: "#eb6834", MODELS[2]: "#2a78d6"}
plt.rcParams.update({
    "font.family": "Malgun Gothic", "axes.unicode_minus": False,
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "savefig.facecolor": "#fcfcfb",
    "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "text.color": INK, "xtick.color": MUTED,
    "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True, "font.size": 10.5,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
})


def plot_prauc(summary):
    """그림 1. 상황별 PR-AUC: 베이스라인 대비 구조 모델 (막대 위 숫자 = 시드 평균)."""
    fig, ax = plt.subplots(figsize=(8.6, 4.3))
    w = 0.26
    for k, m in enumerate(MODELS[:3]):
        s = summary[summary["모델"] == m].set_index("상황").loc[list(REGIMES)]
        x = np.arange(3) + (k - 1) * (w + 0.02)
        ax.bar(x, s["PR-AUC_mean"], width=w, color=COLORS[m], label=m,
               yerr=s["PR-AUC_std"], error_kw=dict(ecolor=MUTED, lw=1, capsize=2))
        for xi, v, sd in zip(x, s["PR-AUC_mean"], s["PR-AUC_std"]):
            ax.text(xi, v + sd + 0.015, f"{v:.2f}", ha="center", fontsize=9.5, color=INK)
    ax.set_xticks(np.arange(3), list(REGIMES.values()))
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("PR-AUC (높을수록 좋음)")
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False, loc="upper right")
    ax.set_title("그림 1. 새 약이 낄수록 성능이 떨어진다 — 무작위 분할(S1)만 보면 과대평가")
    fig.savefig(RESULT_DIR / "fig1_prauc_by_regime.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def plot_pr_curves(curves):
    """그림 2. 정밀도-재현율 곡선 (시드 0). 점선 = 양성 비율(아무 정보 없이 찍었을 때의 정밀도)."""
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.7), sharey=True)
    for ax, (r, label) in zip(axes, REGIMES.items()):
        for m in MODELS[1:3]:
            y, p = curves[r][m]
            if len(np.unique(p)) == 1:
                # 모든 쌍에 같은 점수를 준 경우(S3 의 빈도 베이스라인: 새 약은 빈도 정보가 없음)
                # 곡선을 그릴 수 없다. 억지로 그리면 의미 없는 대각선이 나오므로 설명만 적는다.
                msg = ["빈도 베이스라인은 새 약에 대한", "정보가 없어 모든 쌍에 같은 점수", "= 양성 비율 수준(점선)"]
                for k, line in enumerate(msg):
                    ax.text(0.5, 0.66 - 0.08 * k, line, ha="center", fontsize=9, color=MUTED)
                ax.plot([], [], color=COLORS[m], lw=2, label=m)
                continue
            prec, rec, _ = precision_recall_curve(y, p)
            ax.plot(rec, prec, color=COLORS[m], lw=2, label=m)
        base = curves[r][MODELS[2]][0].mean()
        ax.axhline(base, color=MUTED, lw=1, ls="--")
        ax.text(0.01, base - 0.07, f"양성 비율 {base:.2f}", ha="left", fontsize=9, color=MUTED)
        ax.set_title(label, fontsize=11, fontweight="normal")
        ax.set_xlabel("재현율 (실제 상호작용 중 찾아낸 비율)")
        ax.set_xlim(0, 1); ax.set_ylim(0, 1.02)
    axes[0].set_ylabel("정밀도 (경고 중 실제 상호작용 비율)")
    axes[2].legend(frameon=False, loc="upper right", fontsize=9)
    fig.suptitle("그림 2. 정밀도-재현율 곡선", x=0.01, ha="left", fontweight="bold", fontsize=12)
    fig.tight_layout()
    fig.savefig(RESULT_DIR / "fig2_pr_curves.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


# =============================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    args = ap.parse_args()
    RESULT_DIR.mkdir(exist_ok=True); MODEL_DIR.mkdir(exist_ok=True)

    drugs = pd.read_csv(PROC_DIR / "drugs.csv")
    fp = np.load(PROC_DIR / "fingerprints.npy")
    positives = np.load(PROC_DIR / "positives.npy")

    all_rows, infos, curves0 = [], [], None
    for seed in args.seeds:
        df, info, curves, model = run_seed(seed, drugs, fp, positives, keep_curves=(seed == args.seeds[0]))
        all_rows.append(df); infos.append(info)
        if curves is not None:
            curves0 = curves
            # predict.py 가 읽는 모델. LightGBM 의 save_model() 은 경로에 한글이 있으면 실패하므로
            # 모델을 문자열로 받아 파이썬으로 직접 쓴다.
            (MODEL_DIR / "ddi_lgbm_seed0.txt").write_text(model.booster_.model_to_string(), encoding="utf-8")
        main_rows = df[(df["기준"] == "검증 F1 최대 임계값")]
        print(f"\n[seed {seed}] {info}")
        print(main_rows.pivot(index="모델", columns="상황", values="PR-AUC").loc[MODELS].round(3).to_string())

    metrics = pd.concat(all_rows, ignore_index=True)
    metrics.to_csv(RESULT_DIR / "metrics_by_seed.csv", index=False, encoding="utf-8-sig")
    num = ["양성 비율", "PR-AUC", "ROC-AUC", "정밀도", "재현율", "F1", "정확도"]
    summary = metrics.groupby(["기준", "모델", "상황"])[num].agg(["mean", "std"]).fillna(0)
    summary.columns = [f"{a}_{b}" for a, b in summary.columns]
    summary = summary.reset_index()
    summary.to_csv(RESULT_DIR / "metrics_summary.csv", index=False, encoding="utf-8-sig")
    (RESULT_DIR / "split_info.json").write_text(json.dumps(infos, ensure_ascii=False, indent=2), encoding="utf-8")

    main_summary = summary[summary["기준"] == "검증 F1 최대 임계값"]
    plot_prauc(main_summary)
    plot_pr_curves(curves0)

    show = main_summary.set_index(["모델", "상황"])[[f"{c}_mean" for c in num]].round(3)
    print("\n===== 시드 평균 (검증 F1 최대 임계값) =====\n", show.to_string())
    half = summary[summary["기준"] == "임계값 0.5"].set_index(["모델", "상황"])[
        ["정밀도_mean", "재현율_mean", "F1_mean", "정확도_mean"]].round(3)
    print("\n===== 불균형 처리 비교 (임계값 0.5 고정) =====\n", half.to_string())


if __name__ == "__main__":
    main()
