# reverse-plot-tool

Structured-storytelling-project 配下で、結末から物語構造を遡上する実験サービス。

## リポジトリ

- upstream clone: `/home/shino/work/upstream/Structured-storytelling-project/reverse-plot-tool/`
- parent project: `/home/shino/work/projects/Structured-storytelling-project/`

## 想定デプロイ先

- URL: `https://reverse-plot-tool.lab.ktsys.jp`
- サーバ: `ktsys-lab`

## 構成

- Slim PHP: 最小 Web 入口
- FastAPI: 物語構造 JSON 生成 API
- nginx: ルーティング

## 現在地

- v0.0.1 の足場作成段階
- `POST /api/story/reverse-plot` を仮実装
- UI は最小の検証用フォーム
- 現在は `Swallow-8B` 経由の品質優先試験運用

## 現行の LLM 経路

- `reverse-plot-tool` は `https://swallow-relay.wos.ktsys.jp` を使う
- モデル名は `swallow`
- timeout は `120` 秒
- 単発の重いプロット生成を想定し、実測では約 52 秒で成功を確認した
