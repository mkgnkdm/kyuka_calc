# ==========================================================
# 年休計算機（年次有給休暇 付与日数計算） — 公開ポートフォリオツール第1号
#
# 設計: _ideas/10_portfolio_kyuka_calc.md（歩き通しシナリオA〜Cが受入条件）
# 性格: 個人情報を扱わない・何も保存しない・認証なしの公開ツール。
#       計算は GET で行い、結果URLを共有できる。DBなし・セッションなし。
# ==========================================================

import secrets
from datetime import date

from flask import Flask, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import leave

app = Flask(__name__)
# セッションは使わないが Flask の要件として設定（毎起動ランダムで問題ない）
app.secret_key = secrets.token_hex(32)

# 公開ツールのため軽いレートリミットを設定（通常利用では到達しない値）
limiter = Limiter(get_remote_address, app=app, default_limits=["60 per minute"])

# 起動時に法定テーブルを読み込む（不正なJSONなら起動時に落ちて気づける）
RULES = leave.load_rules()


@app.after_request
def set_security_headers(response):
    """安全なセキュリティヘッダーを付与する（snippets/security_headers.py 準拠）。"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response


@app.route("/")
def index():
    """入力と結果を1画面で完結させる（歩き通しシナリオA）。

    計算は副作用ゼロのため GET で行う。入力値はサーバーに保存しない。
    """
    hire_date_raw = request.args.get("hire_date", "").strip()
    category = request.args.get("category", "").strip()
    method_raw = request.args.get("method", "").strip()
    # 未知の値が来ても既定（法定原則）に倒す（防御的）
    selected_method = method_raw if method_raw in ("legal", "base_date") else "legal"
    base_month_raw = request.args.get("base_month", "").strip()
    base_day_raw = request.args.get("base_day", "").strip()

    error = None
    result = None

    if hire_date_raw or category:
        # 何か入力されたときだけ検証・計算する（初期表示はフォームのみ）
        if category not in RULES["categories"]:
            error = "週の所定労働日数を選択してください。"
        else:
            try:
                hire_date = date.fromisoformat(hire_date_raw)
            except ValueError:
                hire_date = None
            if hire_date is None:
                error = "入社日を入力してください（例: 2024-10-01）。"
            elif hire_date.year < 1950 or hire_date.year > date.today().year + 2:
                # 極端な日付だけ弾く。近い未来は「入社予定」の試算として有効なので許可する
                error = "入社日が現実的な範囲ではないようです。年をご確認ください。"
            elif selected_method == "base_date":
                base_month = base_day = None
                try:
                    base_month = int(base_month_raw)
                    base_day = int(base_day_raw)
                    date(2024, base_month, base_day)  # 妥当性検証用（うるう年の年で解釈）
                except (ValueError, TypeError):
                    error = "基準日が正しくありません（月と日をご確認ください。例: 4月1日）。"

                # 2/29 は基準日として禁止する。うるう年の丸めにより、特定の月末入社
                # （例: 8/28入社で初回付与が非うるう年の2/28）と組み合わさると、会社付与が
                # 法定付与日より1日遅れる＝適法でない結果を表示しうるため（2026-07-13 検品で実証）
                if not error and base_month == 2 and base_day == 29:
                    error = "2月29日は基準日に指定できません。2月末を基準日とする場合は 2月28日 を指定してください。"

                if not error:
                    grants = leave.calc_grants_base_date(hire_date, category, base_month, base_day, RULES)
                    result = {
                        "hire_date": hire_date,
                        "category_label": RULES["categories"][category]["label"],
                        "is_proportional": RULES["categories"][category]["proportional"],
                        "grants": grants,
                        "next": leave.next_grant(grants, date.today()),
                        "is_base_date": True,
                    }
            else:
                grants = leave.calc_grants(hire_date, category, RULES)
                result = {
                    "hire_date": hire_date,
                    "category_label": RULES["categories"][category]["label"],
                    "is_proportional": RULES["categories"][category]["proportional"],
                    "grants": grants,
                    "next": leave.next_grant(grants, date.today()),
                    "is_base_date": False,
                }

    return render_template(
        "index.html",
        rules=RULES,
        error=error,
        result=result,
        hire_date_raw=hire_date_raw,
        selected_category=category,
        selected_method=selected_method,
        base_month_raw=base_month_raw,
        base_day_raw=base_day_raw,
        today=date.today(),
    )


if __name__ == "__main__":
    # ローカル動作確認用（ポート割り当ては _framework/PORTS.md 参照: 5011）
    app.run(host="127.0.0.1", port=5011, debug=False)
