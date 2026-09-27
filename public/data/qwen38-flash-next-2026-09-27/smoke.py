"""Small API check; run after start.sh reports ready. Does not execute model output."""
import json
import time
import urllib.request
from pathlib import Path

base = 'http://127.0.0.1:8731'
out = Path(__file__).resolve().parent / 'results'
out.mkdir(exist_ok=True)
stamp = time.strftime('%Y%m%d-%H%M%S')
for route in ('health', 'v1/models'):
    with urllib.request.urlopen(f'{base}/{route}', timeout=15) as response:
        data = json.load(response)
    (out / f'{stamp}-{route.replace("/", "-")}.json').write_text(json.dumps(data, indent=2) + '\n')
    print(route, json.dumps(data))
body = {
    'messages': [{'role': 'user', 'content': 'Return only a JSON object with keys sum and sorted. sum is 17 + 25. sorted is [9, 2, 7] sorted in ascending order.'}],
    'max_tokens': 128, 'temperature': 0, 'enable_thinking': False,
}
request = urllib.request.Request(base + '/v1/chat/completions', json.dumps(body).encode(),
                                 {'Content-Type': 'application/json'})
with urllib.request.urlopen(request, timeout=300) as response:
    data = json.load(response)
(out / f'{stamp}-smoke.json').write_text(json.dumps({'request': body, 'response': data}, indent=2) + '\n')
message = data['choices'][0]['message']
print(json.dumps(data, indent=2))
assert not message.get('reasoning_content'), 'Unexpected reasoning in thinking-off check'
assert json.loads(message['content']) == {'sum': 42, 'sorted': [2, 7, 9]}, 'Incorrect JSON answer'
print('PASS: thinking-off arithmetic and sorting smoke check')
