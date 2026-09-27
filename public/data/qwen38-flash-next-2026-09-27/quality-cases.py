"""Versioned local diagnostic tasks. Expected answers never enter model prompts."""
import collections
import csv
import heapq
import io
import itertools
import random
import re

SEED = 20260927

def merge_intervals(items):
    result = []
    for a, b in sorted(items):
        if result and a <= result[-1][1]:
            result[-1][1] = max(b, result[-1][1])
        else:
            result.append([a, b])
    return result

def topo(nodes, edges):
    outgoing = {n: set() for n in nodes}
    degree = dict.fromkeys(nodes, 0)
    for a, b in edges:
        if b not in outgoing[a]:
            outgoing[a].add(b)
            degree[b] += 1
    ready = [n for n in nodes if degree[n] == 0]
    heapq.heapify(ready)
    result = []
    while ready:
        n = heapq.heappop(ready)
        result.append(n)
        for b in outgoing[n]:
            degree[b] -= 1
            if degree[b] == 0:
                heapq.heappush(ready, b)
    return result if len(result) == len(nodes) else None

def lru(capacity, operations):
    cache = collections.OrderedDict()
    result = []
    for op in operations:
        if op[0] == 'put':
            _, k, v = op
            cache.pop(k, None)
            cache[k] = v
            if len(cache) > capacity:
                cache.popitem(last=False)
        else:
            k = op[1]
            if k in cache:
                v = cache.pop(k)
                cache[k] = v
                result.append(v)
            else:
                result.append(-1)
    return result

def window(s, t):
    if not t:
        return ''
    need = collections.Counter(t)
    best = None
    for start in range(len(s)):
        have = collections.Counter()
        for end in range(start, len(s)):
            have[s[end]] += 1
            if all(have[k] >= v for k, v in need.items()):
                candidate = s[start:end + 1]
                if best is None or len(candidate) < len(best):
                    best = candidate
                break
    return best or ''

def glob(s, pattern):
    return re.fullmatch(''.join('.*' if c == '*' else '.' if c == '?' else re.escape(c)
                               for c in pattern), s, flags=re.DOTALL) is not None

def path_count(grid):
    if not grid or not grid[0]:
        return 0
    ways = [[0] * len(grid[0]) for _ in grid]
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if not cell:
                ways[y][x] = 1 if x == y == 0 else ((ways[y-1][x] if y else 0) + (ways[y][x-1] if x else 0))
    return ways[-1][-1]

def case(task_id, spec, reference, args):
    return {'id': task_id, 'spec': spec, 'cases': [{'args': a, 'expected': reference(*a)} for a in args]}

def tasks():
    rng = random.Random(SEED)
    result = []
    args = [[[]], [[[1, 2], [2, 4], [7, 7]]], [[[-3, 0], [-1, 5], [2, 3]]]]
    for _ in range(45):
        args.append([[sorted([rng.randint(-20, 20), rng.randint(-20, 20)]) for _ in range(rng.randrange(15))]])
    result.append(case('intervals', 'solve(intervals): merge closed integer intervals [start,end]. Endpoints are ordered. Touching intervals merge. Return sorted disjoint intervals as lists; empty input returns [].', merge_intervals, args))
    args = [[[], []], [['a'], [['a', 'a']]], [['a','b'], [['a','b'], ['a','b']]], [['a','b'], [['a','b'], ['b','a']]]]
    for _ in range(45):
        nodes = list('abcdefg'[:rng.randrange(1, 8)])
        edges = [[a,b] for a in nodes for b in nodes if rng.random() < .16]
        args.append([nodes, edges])
    result.append(case('toposort', 'solve(nodes, edges): directed graph with distinct string node names; every edge [a,b] references listed nodes. Return lexicographically smallest topological ordering, or None for any cycle including self-loops. Ignore duplicate edges. Include isolated nodes. Empty graph returns [].', topo, args))
    args = [[0, [['put','a',1],['get','a']]], [2, [['put','a',1],['put','b',2],['get','a'],['put','c',3],['get','b']]]]
    for _ in range(45):
        ops = [[rng.choice(['put','get']), rng.choice('abcd')] for _ in range(40)]
        for op in ops:
            if op[0] == 'put': op.append(rng.randint(-5, 5))
        args.append([rng.randrange(5), ops])
    result.append(case('lru', 'solve(capacity, operations): simulate an LRU cache. Nonnegative capacity. Operations ["put",key,value] insert/update and mark most recently used; ["get",key] returns value or -1 and successful gets mark most recently used. Return the list of get results only. Updating must not evict another key. Capacity zero stores nothing.', lru, args))
    args = [['ADOBECODEBANC','ABC'], ['',''], ['aa','aa'], ['abxba','ab'], ['é🙂é','éé']]
    args += [[''.join(rng.choices('abcé🙂', k=rng.randrange(20))), ''.join(rng.choices('abcé🙂', k=rng.randrange(6)))] for _ in range(60)]
    result.append(case('min_window', 'solve(s,t): shortest contiguous substring of s containing every character of t with multiplicity. Ties choose earliest start. Return empty string if impossible or t is empty. Treat Python Unicode characters normally.', window, args))
    args = [['','*'], ['a\nb','a?b'], ['a.b','a.b'], ['ab','a**?'], ['','?']]
    args += [[''.join(rng.choices('ab.\n',k=rng.randrange(10))), ''.join(rng.choices('ab.*?',k=rng.randrange(10)))] for _ in range(80)]
    result.append(case('wildcard', 'solve(text,pattern): boolean full-string wildcard match. ? matches exactly one character, * matches zero or more characters, including newlines. Every other character is literal (including dots and backslashes). No escape syntax. Repeated stars allowed.', glob, args))
    args = [[[]], [[[]]], [[[0]]], [[[1]]], [[[0,0],[0,0]]]]
    args += [[[[int(rng.random()<.25) for _ in range(w)] for _ in range(h)]] for h,w in [(rng.randrange(1,8),rng.randrange(1,8)) for _ in range(45)]]
    result.append(case('grid_paths', 'solve(grid): count paths from top-left to bottom-right moving only right/down. Rectangular grid contains 0 for open cells and 1 for blocked cells. Empty grid or zero-width grid gives 0. Blocked start or end gives 0. Return exact integer.', path_count, args))
    args = []
    for rows in [[], [['a,b','c"d','line\nbreak','']], [['🙂','x\r\ny']], [['']], [['a'],['b']]] + [[[rng.choice(['a','b,c','"quoted"','x\ny','', 'é']) for _ in range(4)] for _ in range(rng.randrange(1,8))] for _ in range(40)]:
        f = io.StringIO(newline='')
        csv.writer(f, lineterminator='\r\n').writerows(rows)
        args.append([f.getvalue()])
    result.append(case('csv_parse', 'solve(text): parse valid comma-delimited CSV and return a list of rows of string fields. Double quotes enclose fields; doubled quotes escape a quote; quoted fields may contain commas and CR/LF. Preserve embedded newlines exactly. Records use CRLF. Empty input returns []. Python standard library is allowed.', lambda s: list(csv.reader(io.StringIO(s, newline=''))), args))
    args = []
    for _ in range(55):
        events = [[rng.randrange(8),rng.choice('abc'),rng.randint(-20,20)] for _ in range(rng.randrange(25))]
        args.append([events])
    def latest(events):
        out = {}
        for i, (ts,k,v) in enumerate(events):
            if k not in out or (ts,i) > out[k][:2]: out[k]=(ts,i,v)
        return {k: v[2] for k,v in out.items()}
    result.append(case('latest_events', 'solve(events): each event is [integer_timestamp,string_key,integer_value]. Return dict mapping each key to value at greatest timestamp. On timestamp ties, the later input occurrence wins. Input is unsorted and may be empty. Values can be zero or negative.', latest, args))
    args = []
    def expression_value(expr):
        # Inputs constructed below from integers, +/-/* and parentheses only.
        return eval(expr, {'__builtins__': {}}, {})
    expressions = ['1--2','-(2+3)*4','2*-3 + 4','--5','1 + -(-2)','0','-0', '(2+3)*(4-7)']
    for _ in range(55):
        a,b,c = [rng.randint(-20,20) for _ in range(3)]
        expressions.append(f'({a} {rng.choice(["+","-","*"])} {b}) * -({c})')
    args = [[s] for s in expressions]
    result.append(case('expression_parser', 'solve(expression): evaluate a valid integer expression using +, -, *, parentheses, whitespace and unary +/- (including repeated unary signs). Standard precedence, arbitrary-size integers, no division. Implement parsing; do NOT use eval, exec, compile, ast or subprocess. Return integer.', expression_value, args))
    args = []
    for _ in range(55):
        args.append([[rng.randint(-8,8) for _ in range(rng.randrange(13))]])
    def lis(seq):
        best = 0
        for n in range(len(seq)+1):
            if any(all(a < b for a,b in zip(s,s[1:])) for s in itertools.combinations(seq,n)):
                best = n
        return best
    result.append(case('lis', 'solve(numbers): length of longest strictly increasing subsequence (not necessarily contiguous). Equal values cannot extend it. Empty input gives 0. Integers may be negative. Aim for O(n log n) time.', lis, args + [[[2,2,2]], [[]], [[-3,-2,-1]]]))
    return result

if __name__ == '__main__':
    assert merge_intervals([[1,2],[2,3]]) == [[1,3]]
    assert topo(['a','b'], [['a','b'],['b','a']]) is None
    assert window('ADOBECODEBANC','ABC') == 'BANC'
    assert lru(0,[['put','x',1],['get','x']]) == [-1]
    assert path_count([[0,0],[0,0]]) == 2
    all_tasks = tasks()
    print(f'{len(all_tasks)} tasks, {sum(len(t["cases"]) for t in all_tasks)} hidden cases')
