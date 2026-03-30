# reverse-plot-tool 仕様書

## 概要

結末や終着条件から、物語の成立条件を遡上して物語構造 JSON を生成する。
現在は、一括生成 API と staged flow API を併用している。

## 入力

- `ending_text`
- `protagonist_hint` (任意)
- `genre_hint` (任意)
- `wild_twist_level` (0〜10, 任意, 既定値 0)

## 一括生成 API

- `POST /api/story/reverse-plot`
- 成功時は `status` と `story` を返す
- `story` の中に物語構造 JSON 本体を入れる

### 一括生成レスポンス例

```json
{
  "status": "success",
  "story": {
    "title": "仮タイトル",
    "ending_summary": "物語の結末要約",
    "core_theme": "中心テーマ",
    "protagonist_final_state": "結末時の主人公の状態",
    "structural_conditions": {
      "initial_lack": "初期欠落",
      "desire": "主人公の欲望",
      "fear": "主人公の恐れ",
      "false_belief": "誤信念",
      "starting_situation": "物語開始時の初期配置"
    },
    "relationship_changes": [
      "必要な関係変化1",
      "必要な関係変化2"
    ],
    "required_turning_points": [
      "必要な転換点1",
      "必要な転換点2",
      "必要な転換点3"
    ],
    "failure_conditions": [
      "破綻してはいけない条件1",
      "破綻してはいけない条件2"
    ],
    "plot": {
      "prologue": "2〜3文のあらすじ",
      "ki": "2〜3文のあらすじ",
      "sho": "2〜3文のあらすじ",
      "ten": "2〜3文のあらすじ",
      "ketsu": "2〜3文のあらすじ",
      "epilogue": "2〜3文のあらすじ"
    }
  }
}
```

## staged flow

- 一括 JSON 生成ボタンは置かず、現在どの段を作成するかを固定文言で表示する
- 段階選択は `epilogue -> ketsu -> ten -> sho -> ki -> prologue` の順で進める
- 実行ボタン表記は `xxxxx候補の作成及び選択` とする
- 確定済みの plot は 1 つの長文欄に連結せず、段ごとのカードとして表示する
- 各段で候補を 3 件返し、ユーザーは modal 内の radio で 1 件を確定する
- 各段の確定後、次段候補は自動では取りに行かず、ボタン押下で進む
- modal を閉じても進捗は捨てず、その時点の段から再開できる
- 確定済みの後段は次段候補の生成条件として API に渡す
- 6 段すべて確定後、最終組み立て API が構造情報を補完して完成 JSON を返す
- 各段の候補生成 prompt には、その段の役割と前後段への接続条件を入れる

## staged flow API

### `POST /api/story/reverse-plot/staged/epilogue`

- `epilogue` 候補を返す
- 成功時レスポンスは `status`, `step`, `choices` を返す
- `choices` は文字列配列ではなく、`id` と `text` を持つ object 配列

#### レスポンス例

```json
{
  "status": "success",
  "step": "epilogue",
  "choices": [
    {
      "id": "epilogue_1",
      "text": "候補1"
    },
    {
      "id": "epilogue_2",
      "text": "候補2"
    },
    {
      "id": "epilogue_3",
      "text": "候補3"
    }
  ]
}
```

### `POST /api/story/reverse-plot/staged/choices`

- `step` と `selected_plot` を受け取り、指定段の候補を返す
- 成功時レスポンスは `status`, `step`, `choices` を返す
- `choices` は `id` と `text` を持つ object 配列

#### リクエスト補足

- `step` は `ketsu`, `ten`, `sho`, `ki`, `prologue` のいずれか
- `selected_plot` は、すでに確定済みの後段だけを入れる

#### レスポンス例

```json
{
  "status": "success",
  "step": "ketsu",
  "choices": [
    {
      "id": "ketsu_1",
      "text": "候補1"
    },
    {
      "id": "ketsu_2",
      "text": "候補2"
    },
    {
      "id": "ketsu_3",
      "text": "候補3"
    }
  ]
}
```

### `POST /api/story/reverse-plot/staged/finalize`

- 6 段すべての `selected_plot` を受け取り、最終 JSON を返す
- 成功時レスポンスは `status` と `story` を返す
- `story` が最終的な物語構造 JSON 本体

#### リクエスト補足

- `selected_plot` には `prologue`, `ki`, `sho`, `ten`, `ketsu`, `epilogue` をすべて含める
- 1 つでも欠けると 400 を返す

#### レスポンス例

```json
{
  "status": "success",
  "story": {
    "title": "仮タイトル",
    "ending_summary": "物語の結末要約",
    "core_theme": "中心テーマ",
    "protagonist_final_state": "結末時の主人公の状態",
    "structural_conditions": {
      "initial_lack": "初期欠落",
      "desire": "主人公の欲望",
      "fear": "主人公の恐れ",
      "false_belief": "誤信念",
      "starting_situation": "物語開始時の初期配置"
    },
    "relationship_changes": [
      "必要な関係変化1",
      "必要な関係変化2"
    ],
    "required_turning_points": [
      "必要な転換点1",
      "必要な転換点2",
      "必要な転換点3"
    ],
    "failure_conditions": [
      "破綻してはいけない条件1",
      "破綻してはいけない条件2"
    ],
    "plot": {
      "prologue": "2〜3文のあらすじ",
      "ki": "2〜3文のあらすじ",
      "sho": "2〜3文のあらすじ",
      "ten": "2〜3文のあらすじ",
      "ketsu": "2〜3文のあらすじ",
      "epilogue": "2〜3文のあらすじ"
    }
  }
}
```

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
- LLM 問い合わせ中はローディング modal を表示し、入力欄と実行ボタンを一時ロックする
- ローディング modal には待機中であることが視覚的に分かる spinner と経過秒を表示する
- 全段完了後は、実行ボタンを `最初から選び直す` 状態へ切り替える

## バージョン表示

- 画面タイトル横に `version: <short-sha>` を表示する
- 表示値は `/api/health` の `version` から取得する
- deploy workflow は `main` に反映された commit の short SHA を `APP_VERSION` として渡す

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
