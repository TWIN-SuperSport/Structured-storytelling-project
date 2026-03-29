# reverse-plot-tool

Structured-storytelling-project 配下で、結末から物語構造を遡上する実験サービス。

## リポジトリ

- upstream clone: `/home/shino/work/upstream/Structured-storytelling-project/reverse-plot-tool/`
- parent project: `/home/shino/work/projects/Structured-storytelling-project/`

## 想定デプロイ先

- URL: `https://reverse-plot-tool.lab.ktsys.jp`
- サーバ: `ktsys-pubserver`

## 構成

- Slim PHP: 最小 Web 入口
- FastAPI: 物語構造 JSON 生成 API
- nginx: ルーティング

## 現在地

- v0.0.1 の足場作成段階
- `POST /api/story/reverse-plot` を仮実装
- UI は最小の検証用フォーム
