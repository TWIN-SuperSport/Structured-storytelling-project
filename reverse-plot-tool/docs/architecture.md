# reverse-plot-tool architecture

Browser
 -> ktsys-pubserver nginx-proxy
 -> reverse-plot-tool-nginx
 -> Slim PHP
 -> FastAPI
 -> BASE swallow-relay.wos.ktsys.jp
 -> BASE wos-llm-relay-swallow
 -> Win10PC Swallow-8B (:8080)

正本は FastAPI が返す story JSON。
