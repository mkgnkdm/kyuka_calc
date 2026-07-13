# ==========================================================
# leave.py — 年次有給休暇の付与計算エンジン（Flask 非依存の純ロジック）
#
# 設計方針（_ideas/10_portfolio_kyuka_calc.md）:
# - 法定の付与日数はコードに書かず rules.json から読む（出典・確認日つき）
# - 法定原則（入社日起算・6か月後に初回付与、以後1年ごと）に加えて、
#   基準日方式（一斉付与・§9-2）を扱う。出勤率8割の要件は判定しない（注記のみ）
# ==========================================================

import calendar
import json
import os
from datetime import date, timedelta

RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules.json")

# 付与の表示件数（初回＋6回で法定表の全段階をカバーする）
MAX_GRANTS = 7


def load_rules(path=RULES_PATH) -> dict:
    """法定テーブルを読み込む。アプリ起動時と計算時に使う。"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def add_months(d: date, months: int) -> date:
    """月単位の加算。月末を超える日は月末に丸める（例: 8/31 + 6か月 → 2/28）。"""
    total = d.year * 12 + (d.month - 1) + months
    year, month = divmod(total, 12)
    month += 1
    if month == 12:
        last_day = 31
    else:
        last_day = (date(year, month + 1, 1) - timedelta(days=1)).day
    return date(year, month, min(d.day, last_day))


def calc_grants(hire_date: date, category: str, rules: dict) -> list:
    """入社日と働き方区分から、付与日・付与日数の一覧を返す。

    戻り値: [{"grant_date": date, "service_label": str, "days": int,
              "is_final_step": bool}, ...]
    is_final_step は「以後毎年この日数」の段階（勤続6年6か月以上）を示す。
    """
    cat = rules["categories"][category]
    days_table = cat["days_by_service"]
    labels = rules["service_labels"]

    grants = []
    for i in range(MAX_GRANTS):
        # 初回は入社6か月後、以後は1年ごと（法定原則・入社日起算）
        grant_date = add_months(hire_date, 6 + 12 * i)
        step = min(i, len(days_table) - 1)
        grants.append({
            "grant_date": grant_date,
            "service_label": labels[step],
            "days": days_table[step],
            "is_final_step": step == len(days_table) - 1,
        })
    return grants


def _clamp_base_date(year: int, month: int, day: int) -> date:
    """基準日（月・日）を指定の年にあてはめる。2/29かつ非うるう年なら2/28に丸める
    （add_months の月末丸めと同じ考え方）。"""
    if month == 2 and day == 29 and not calendar.isleap(year):
        return date(year, 2, 28)
    return date(year, month, day)


def _next_base_date_after(d: date, base_month: int, base_day: int) -> date:
    """d より後（d 自身は含まない）で最初に到来する基準日を返す。"""
    candidate = _clamp_base_date(d.year, base_month, base_day)
    if candidate <= d:
        candidate = _clamp_base_date(d.year + 1, base_month, base_day)
    return candidate


def calc_grants_base_date(hire_date: date, category: str, base_month: int, base_day: int, rules: dict) -> list:
    """基準日方式（一斉付与）の付与一覧を返す（設計書 §9-2）。

    初回のみ法定原則どおり（入社6か月後）。2回目以降は、直前の付与日より後で
    最初に到来する基準日に統一する（日数・勤続段階は既存 calc_grants の対応する
    段階＝前倒しをそのまま使う）。各行に legal_date（本来の法定付与日）を持たせ、
    画面の「前倒し」表示に使う。

    法令上の要点: 斉一的取扱いは付与を法定より早める方向でのみ認められる。
    この関数の構成上、常に company[k].grant_date <= legal[k].grant_date が成り立つ
    （不変条件。test_app.py のプロパティテストで検証する）。
    """
    legal = calc_grants(hire_date, category, rules)

    grants = [{**legal[0], "legal_date": legal[0]["grant_date"]}]
    for i in range(1, len(legal)):
        prev_date = grants[-1]["grant_date"]
        grant_date = _next_base_date_after(prev_date, base_month, base_day)
        grants.append({
            "grant_date": grant_date,
            "service_label": legal[i]["service_label"],
            "days": legal[i]["days"],
            "is_final_step": legal[i]["is_final_step"],
            "legal_date": legal[i]["grant_date"],
        })
    return grants


def next_grant(grants: list, today: date):
    """付与一覧から「次回の付与」を返す。全付与が過去なら、最終段階の翌周期を合成して返す。"""
    for g in grants:
        if g["grant_date"] >= today:
            return g
    # 表示範囲を超えて勤続している場合: 最終段階（毎年同日数）の次回付与日を計算する
    last = grants[-1]
    grant_date = last["grant_date"]
    while grant_date < today:
        grant_date = add_months(grant_date, 12)
    return {**last, "grant_date": grant_date}
