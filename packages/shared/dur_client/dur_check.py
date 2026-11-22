"""
DUR 기반 상호작용·주의 판정 (통합 진입점)
=========================================

제품명/성분명 목록을 받아 식약처 DUR 공식 데이터로:
  1) 병용금기(두 약을 함께 쓰면 안 되는 절대 금기)
  2) 품목 단위 주의(노인주의·임부금기·특정연령대금기 등)
를 조회해 돌려준다.

파이프라인:
  이름 → (drug_permit_resolver) 허가정보 ITEM_SEQ → (dur_api) DUR 품목정보 조회

중요한 범위 한계(실측으로 확인):
- DUR '병용금기'는 **절대 금기만** 등재한다. 와파린+NSAID처럼 흔히 '주의'로 다루는
  조합은 DUR 병용금기에 없다(용량주의/임상판단 영역). 따라서 DUR는 앱의 로컬 규칙을
  **대체하지 않고**, 자신이 덮는 범주에서 공식 근거로 **보강**한다.
- DUR 병용금기는 특정 품목코드로 등재되므로, 한 성분도 여러 후보 제품을 시도해야
  놓치지 않는다(아래 max_try).

반환 결과에는 출처가 "식약처 DUR"로 표시된다. 등재가 없다고 안전을 뜻하지 않는다.
"""

import drug_permit_resolver as _resolver
import dur_api as _dur

MAX_TRY = 3  # 성분당 시도할 후보 제품 수(병용금기 미등재 품목을 건너뛰기 위함)


def _candidates(product_name=None, eng_ingredient=None):
    cands = []
    if product_name:
        cands = _resolver.resolve_by_product_name(product_name)
    if not cands and eng_ingredient:
        cands = _resolver.resolve_by_ingredient_eng(eng_ingredient)
    return cands


def dur_profile(label, product_name=None, eng_ingredient=None, with_cautions=True):
    """
    한 약의 DUR 프로필을 반환.
    반환: {
      "label", "item_seq", "item_name", "resolved"(bool),
      "own_codes": {성분코드...},
      "taboo_partners": {상대성분코드: 사유},   # 병용금기
      "cautions": {"노인주의":[...], ...}         # 품목 단위 주의(with_cautions=True일 때)
    }
    """
    cands = _candidates(product_name, eng_ingredient)
    live = [c for c in cands if not c["cancelled"] and c["item_seq"]]
    ordered = live or cands
    prof = {
        "label": label, "item_seq": None, "item_name": None, "resolved": bool(cands),
        "own_codes": set(), "taboo_partners": {}, "cautions": {},
    }
    if not ordered:
        return prof
    prof["item_seq"] = ordered[0]["item_seq"]
    prof["item_name"] = ordered[0]["item_name"]

    tried = 0
    for c in ordered:
        if not c["item_seq"]:
            continue
        tried += 1
        partners = _dur.taboo_partners_by_item_seq(c["item_seq"])
        if partners:
            prof["item_seq"] = c["item_seq"]
            prof["item_name"] = c["item_name"]
            prof["own_codes"] = {p["base_ingr_code"] for p in partners if p.get("base_ingr_code")}
            prof["taboo_partners"] = {p["ingr_code"]: p["reason"] for p in partners}
            break
        if tried >= MAX_TRY:
            break

    if with_cautions and prof["item_seq"]:
        prof["cautions"] = _dur.cautions_by_item_seq(
            prof["item_seq"], types=["노인주의", "임부금기", "특정연령대금기"]
        )
    return prof


def check_interactions(drugs, with_cautions=True):
    """
    여러 약의 DUR 병용금기·주의를 판정.
    drugs: [{"label","product_name"?,"eng_ingredient"?}, ...]
    반환: {
      "profiles": [dur_profile ...],
      "combination_taboo": [{"a","b","reason","source":"식약처 DUR"}],
      "unresolved": [label ...],           # 허가정보에서 못 찾은 약
    }
    """
    profiles = [
        dur_profile(d["label"], d.get("product_name"), d.get("eng_ingredient"), with_cautions)
        for d in drugs
    ]
    unresolved = [p["label"] for p in profiles if not p["resolved"]]

    hits = []
    for i in range(len(profiles)):
        for j in range(i + 1, len(profiles)):
            a, b = profiles[i], profiles[j]
            reason = None
            shared = b["own_codes"] & set(a["taboo_partners"].keys())
            if shared:
                reason = a["taboo_partners"][next(iter(shared))]
            else:
                shared = a["own_codes"] & set(b["taboo_partners"].keys())
                if shared:
                    reason = b["taboo_partners"][next(iter(shared))]
            if reason:
                hits.append({"a": a["label"], "b": b["label"],
                             "reason": reason, "source": "식약처 DUR"})
    return {"profiles": profiles, "combination_taboo": hits, "unresolved": unresolved}


if __name__ == "__main__":
    import functools
    print = functools.partial(print, flush=True)
    drugs = [
        {"label": "스포라녹스(이트라코나졸)", "eng_ingredient": "Itraconazole"},
        {"label": "조코(심바스타틴)", "eng_ingredient": "Simvastatin"},
        {"label": "타이레놀", "product_name": "타이레놀"},
    ]
    res = check_interactions(drugs)
    print("== 병용금기 ==")
    for h in res["combination_taboo"]:
        print(f"  {h['a']} + {h['b']} => {h['reason']} [{h['source']}]")
    if not res["combination_taboo"]:
        print("  (DUR 등재 병용금기 없음)")
    print("== 각 약 DUR 프로필 ==")
    for p in res["profiles"]:
        cz = ", ".join(f"{k} {len(v)}건" for k, v in p["cautions"].items()) or "없음"
        print(f"  {p['label']}: ITEM_SEQ={p['item_seq']} 병용금기파트너 {len(p['taboo_partners'])} | 주의: {cz}")
    if res["unresolved"]:
        print("미해석:", res["unresolved"])
