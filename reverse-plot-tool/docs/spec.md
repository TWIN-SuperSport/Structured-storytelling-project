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

## ゴール

- この JSON を正本とする
- 後段で `.md` プロットへ投影できるようにする
- さらに断片ツールへ接続できるようにする
- `wild_twist_level` に応じて、とくに `required_turning_points` と `plot.ten` の跳ね方を調整できるようにする
