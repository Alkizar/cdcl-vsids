from core import Clause, BoolLiteral

def parse_dimacs(path):
    clauses = []
    with open(path) as f:
        for line in f:
            if line.startswith('c') or line.startswith('p'):
                continue
            nums = line.strip().split()
            if not nums:
                continue
            literals = []
            for n in nums:
                if n == '0':
                    break
                if n.startswith('-'):
                    literals.append(BoolLiteral.make_neg(n[1:]))
                else:
                    literals.append(BoolLiteral.make_pos(n))
            clauses.append(Clause(*literals))
    return clauses