#!/bin/sh
# usage: scripts/bench.sh <label>  - mints a token, 5s warmup, 30s @ 64 conns, writes $BENCH_OUT/<label>.json
TOKEN=$(curl -s -X POST http://localhost:8080/realms/tenant-rbac-kit/protocol/openid-connect/token \
  -d grant_type=password -d client_id=tenant-rbac-api -d client_secret=dev-secret \
  -d username=alice -d password=alice | jq -r .access_token)
oha -z 5s -c 64 --no-tui -H "Authorization: Bearer $TOKEN" http://localhost:8000/invoices >/dev/null
oha -z 30s -c 64 --no-tui --output-format json -H "Authorization: Bearer $TOKEN" http://localhost:8000/invoices > "${BENCH_OUT:-/tmp}/$1.json"
jq -r '"\(input_filename|split("/")|last): rps=\(.summary.requestsPerSec|round) p50=\((.latencyPercentiles.p50*1000*100|round)/100)ms p99=\((.latencyPercentiles.p99*1000*100|round)/100)ms 2xx=\(.statusCodeDistribution["200"]) other=\([.statusCodeDistribution|to_entries[]|select(.key!="200")|.value]|add // 0)"' "${BENCH_OUT:-/tmp}/$1.json"
