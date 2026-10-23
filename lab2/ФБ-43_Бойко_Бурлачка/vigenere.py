import contextlib
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            st.write(s)

    def flush(self):
        for st in self.streams:
            st.flush()

ALPH = 'абвгдежзийклмнопрстуфхцчшщъыьэюя'
M = len(ALPH)
IDX = {c: i for i, c in enumerate(ALPH)}

FREQ = {
    'о': 0.1098, 'е': 0.0845, 'а': 0.0640, 'и': 0.0635, 'т': 0.0561,
    'н': 0.0545, 'с': 0.0453, 'в': 0.0450, 'р': 0.0405, 'л': 0.0350,
    'к': 0.0325, 'м': 0.0270, 'д': 0.0270, 'п': 0.0240, 'у': 0.0210,
    'я': 0.0200, 'ы': 0.0160, 'з': 0.0160, 'ь': 0.0140, 'б': 0.0140,
    'г': 0.0130, 'ч': 0.0120, 'й': 0.0095, 'х': 0.0080, 'ж': 0.0065,
    'ю': 0.0055, 'ш': 0.0050, 'ц': 0.0030, 'щ': 0.0025, 'э': 0.0025,
    'ф': 0.0015, 'ъ': 0.0002,
}


def prepare(raw):
    raw = raw.lower().replace('ё', 'е')
    return ''.join(c for c in raw if c in IDX)


def encrypt(pt, key):
    return ''.join(ALPH[(IDX[x] + IDX[key[i % len(key)]]) % M]
                   for i, x in enumerate(pt))


def decrypt(ct, key):
    return ''.join(ALPH[(IDX[y] - IDX[key[i % len(key)]]) % M]
                   for i, y in enumerate(ct))


def ic(text):
    n = len(text)
    if n < 2:
        return 0.0
    cnt = Counter(text)
    return sum(v * (v - 1) for v in cnt.values()) / (n * (n - 1))


def coincidences(ct, r):
    return sum(1 for i in range(len(ct) - r) if ct[i] == ct[i + r])


def mean_block_ic(ct, r):
    vals = [ic(ct[i::r]) for i in range(r) if len(ct[i::r]) > 1]
    return sum(vals) / len(vals)


def find_period(ct, rmax=30):
    return max(range(2, rmax + 1),
               key=lambda r: coincidences(ct, r) / (len(ct) - r))


def best_shift(block):
    cnt, n = Counter(block), len(block)
    scores = []
    for g in range(M):
        chi = sum((cnt.get(ALPH[(t + g) % M], 0) - n * FREQ[ALPH[t]]) ** 2
                  / (n * FREQ[ALPH[t]]) for t in range(M))
        scores.append((chi, g))
    return min(scores)[1]


def relative_shifts(ct, r):
    rel = [[0] * r for _ in range(r)]
    for i in range(r):
        ci, ni = Counter(ct[i::r]), len(ct[i::r])
        fi = {t: ci.get(ALPH[t], 0) / ni for t in range(M)}
        for j in range(i + 1, r):
            cj, nj = Counter(ct[j::r]), len(ct[j::r])
            fj = {t: cj.get(ALPH[t], 0) / nj for t in range(M)}
            g = max(range(M), key=lambda g: sum(fi[t] * fj[(t + g) % M] for t in range(M)))
            rel[i][j] = g
            rel[j][i] = (-g) % M
    return rel


def recover_key(ct, r):
    rel = relative_shifts(ct, r)
    k0 = best_shift(ct[0::r])
    return ''.join(ALPH[(k0 + rel[0][i]) % M] for i in range(r))


def error_experiment(ct, key, pos, letter):
    bad_key = key[:pos] + letter + key[pos + 1:]
    good, bad = decrypt(ct, key), decrypt(ct, bad_key)
    diff = [i for i in range(len(ct)) if good[i] != bad[i]]
    return diff, bad


def main():
    pt = prepare(open('plaintext.txt', encoding='utf-8').read())
    print(f'IC(ВТ) = {ic(pt):.4f}')
    for k in ('ой', 'три', 'ключ', 'университет'):
        print(f'ключ={k:<12} r={len(k):<2} IC(ШТ)={ic(encrypt(pt, k)):.4f}')

    lines = open('variant.txt', encoding='utf-8').read().split('\n')
    header = next(ln for ln in lines if ln.strip())
    ct = prepare('\n'.join(ln for ln in lines if ln != header))
    print(f'\nn = {len(ct)}')
    print('r\tD_r\tD_r/(n-r)\tIC_block')
    for r in range(1, 31):
        d = coincidences(ct, r)
        print(f'{r}\t{d}\t{d / (len(ct) - r):.4f}\t{mean_block_ic(ct, r):.4f}')

    r = find_period(ct)
    key = recover_key(ct, r)
    print(f'\nr = {r}\nkey = {key}\n{decrypt(ct, key)}')

    diff, bad = error_experiment(ct, key, 4, 'м')
    print(f'\nchanged = {len(diff)} ({100 * len(diff) / len(ct):.1f}%), '
          f'period = {all(i % r == 4 for i in diff)}')
    print(bad[:200])


if __name__ == '__main__':
    with open('results.txt', 'w', encoding='utf-8') as f, \
            contextlib.redirect_stdout(Tee(sys.__stdout__, f)):
        main()
