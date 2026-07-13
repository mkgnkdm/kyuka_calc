# kyuka_calc（年休計算機）

<!-- 2026-07-13 新規作成。設計: C:\Projects\_ideas\10_portfolio_kyuka_calc.md -->

## 概要

年次有給休暇の付与日・付与日数（比例付与含む）を計算する**公開ポートフォリオツール**。
他の内部アプリと違い、**個人情報を扱わない・何も保存しない・公開してよい**アプリ。
GitHub public リポジトリ化と PythonAnywhere 公開を予定（ポートフォリオ計画=
`_ideas\portfolio_plan.md`）。

## 起動方法

- ローカル: `start.bat`（ポート **5011**）／停止: `stop.bat`

## デプロイ先

- サービス: PythonAnywhere（2026-07-13〜 セットアップ）
- URL: https://kyukacalc.pythonanywhere.com
- PythonAnywhere アカウント: kyukacalc（このアプリ専用。他アプリとは別アカウント）
- 本番ディレクトリ: /home/kyukacalc/kyuka_calc
- GitHub リポジトリ: mkgnkdm/kyuka_calc（**public**。公開ポートフォリオのため他アプリと違い公開リポジトリ）
- ブランチ: main
- GitHub Secret 名: KYUKACALC_PA_API_TOKEN
- git push origin main だけで GitHub Actions が自動反映（詳細は deploy Skill 参照）。
  requirements.txt 変更時のみ PythonAnywhere の Bash コンソールで
  `pip3.10 install --user -r requirements.txt` を手動実行してから Reload が必要
- **公開リポジトリのため**: 事務所名・顧問先情報・他プロジェクトへの言及を絶対にコミットしない。
  push前に `git status` で意図しないファイルが含まれていないか必ず確認する

## テスト

```
venv\Scripts\python.exe -m pytest test_app.py -v
```

全項目パス必須（法定表の構造検証／期待値〔人間確認前は下書き扱い〕／境界ケース
〔月末入社・うるう年・勤続上限・next_grant〕／歩き通しシナリオA〜Cのスモーク）。

## このプロジェクト固有のルール

- **法定の付与日数は rules.json でのみ管理**（コードに書かない）。`status: "draft"` の間は
  画面に「下書き・実務に使わない」警告が出る。**人間が条文と突き合わせて確認したら
  verified_at を入れて status を "verified" にする**（この確認はユーザー本人の仕事）
- DBなし・セッションなし・入力を保存しない設計を崩さない（公開ツールのプライバシー前提）
- 計算は GET（副作用ゼロ・結果URL共有可）。POSTで状態を変える機能を足すときは CSRF 必須
- スコープ外（出勤率判定・基準日方式・取得義務管理）を安易に足さない。足すなら設計書を先に
- **公開リポジトリにする前提**: 事務所名・顧問先・他プロジェクトへの言及をコード・コミットに
  含めない。個人情報を扱う他アプリのコードを流用したら出所コメントも汎用化する

## 個人情報の取り扱い(第0条)

このアプリ自体は個人情報を扱わない（入力も保存しない）。それでも DB 実体・.env 等を
Claude が読むことは禁止（ユーザーCLAUDE.md参照）。
