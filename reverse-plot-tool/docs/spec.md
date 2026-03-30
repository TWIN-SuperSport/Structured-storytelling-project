# reverse-plot-tool 仕様書

## 概要

結末や終着条件から、物語の成立条件を遡上して物語構造 JSON を生成する。

## 入力

- `ending_text`
- `protagonist_hint` (任意)
- `genre_hint` (任意)
- `wild_twist_level` (0〜10, 任意, 既定値 0)

## 出力

- 物語構造 JSON
- `plot.prologue`, `plot.ki`, `plot.sho`, `plot.ten`, `plot.ketsu`, `plot.epilogue`
- 構造条件:
  - `initial_lack`
  - `desire`
  - `fear`
  - `false_belief`
  - `starting_situation`
- 関係変化、転換点、破綻条件

## 段階選択フロー

- 従来の一括 JSON 生成に加えて、段階選択フローを持つ
- 段階選択は `epilogue -> ten -> sho -> ki -> prologue` の順で進める
- 各段で候補を 3 件返し、ユーザーは modal 内の radio で 1 件を確定する
- 確定済みの後段は次段候補の生成条件として API に渡す
- 5 段すべて確定後、最終組み立て API が構造情報を補完して完成 JSON を返す

## 段階選択 API

- `POST /api/story/reverse-plot/staged/epilogue`
  - `epilogue` 候補を返す
- `POST /api/story/reverse-plot/staged/choices`
  - `step` と `selected_plot` を受け取り、指定段の候補を返す
- `POST /api/story/reverse-plot/staged/finalize`
  - 5 段すべての `selected_plot` を受け取り、最終 JSON を返す

## UI 待機表示

- 生成開始直後は単に「考え中」とせず、`送信済み` として relay へ依頼を投げ終わったことを明示する
- 生成待機中は経過秒を表示する
- 待機メッセージは固定文言 1 つにせず、経過時間に応じて段階表示する
- 想定する段階表示:
  - 開始直後: `リレーに依頼を投げて、生成結果を待ってる`
  - 15 秒以降: `Swallow が長めに考えてる`
  - 45 秒以降: `固まっているわけではなく、重めの候補生成が続いている`
  - 90 秒以降: `かなり長考中だが、そのまま待機してよい`
- 待機中は送信ボタンを無効化し、二重送信を防ぐ

## UI エラー表示

- HTTP エラー時は、単なる失敗表示ではなく `HTTP status` と応答本文を確認できる形で出す
- JSON 以外の応答を受けた場合は、`サーバが JSON 以外を返した` ことを明示する
- 通信例外時は、`通信エラー` として切り分け可能な文言を出す
- 成功時は `生成完了` として、JSON が返ってきたことを UI 上でも明示する
- エラー時も待機状態を解除し、ボタンを再度押せる状態へ戻す

## ゴール

- この JSON を正本とする
- 後段で `.md` プロットへ投影できるようにする
- さらに断片ツールへ接続できるようにする
- `wild_twist_level` に応じて、とくに `required_turning_points` と `plot.ten` の跳ね方を調整できるようにする
