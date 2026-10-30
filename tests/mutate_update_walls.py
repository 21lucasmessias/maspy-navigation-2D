"""Mutation testing for Walker.update_walls.

Generates one mutant per change below inside update_walls, writes it over
src/Walker_Ag.py, runs the test suite and restores the file. A mutant must
make at least one test fail ("killed"); a surviving mutant is a test gap.

    .venv/Scripts/python.exe tests/mutate_update_walls.py
"""

import ast
import copy
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGET = ROOT / "src" / "Walker_Ag.py"
FUNC = "update_walls"

SLICES = ["[-1:]", "[:1]", "[1:]", "[:-1]"]


def find_func(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == FUNC:
            return node
    raise SystemExit(f"{FUNC} not found in {TARGET}")


# Each site is (description, function that mutates the copied tree in place).
def mutation_sites(func):
    sites = []
    nodes = list(ast.walk(func))

    for i, node in enumerate(nodes):
        # in <-> not in
        if isinstance(node, ast.Compare):
            for j, op in enumerate(node.ops):
                swap = {ast.NotIn: ast.In, ast.In: ast.NotIn,
                        ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}.get(type(op))
                if swap:
                    sites.append((f"line {node.lineno}: {type(op).__name__} -> {swap.__name__}",
                                  lambda f, i=i, j=j, s=swap: setattr_op(f, i, j, s)))
        # if x -> if not x
        if isinstance(node, ast.If):
            sites.append((f"line {node.lineno}: negate if",
                          lambda f, i=i: negate_if(f, i)))
        # drop the comprehension filter
        if isinstance(node, ast.comprehension) and node.ifs:
            sites.append((f"line {node.target.lineno}: drop comprehension filter",
                          lambda f, i=i: setattr(at(f, i), "ifs", [])))
        # slice the iterated list
        if isinstance(node, ast.comprehension):
            for sl in SLICES:
                sites.append((f"line {node.target.lineno}: iterate {ast.unparse(node.iter)}{sl}",
                              lambda f, i=i, sl=sl: slice_iter(f, i, sl)))
        # method swaps
        if isinstance(node, ast.Attribute) and node.attr in {"extend", "append"}:
            other = "append" if node.attr == "extend" else "extend"
            sites.append((f"line {node.lineno}: .{node.attr} -> .{other}",
                          lambda f, i=i, o=other: setattr(at(f, i), "attr", o)))
        # change(values=old_set) -> change(values=new)
        if isinstance(node, ast.keyword) and node.arg == "values":
            sites.append((f"line {node.value.lineno}: change(values=new)",
                          lambda f, i=i: setattr(at(f, i), "value", ast.Name("new", ast.Load()))))

    # delete each statement (replace by pass)
    for i, node in enumerate(nodes):
        body = getattr(node, "body", None)
        if isinstance(body, list):
            for k, stmt in enumerate(body):
                sites.append((f"line {stmt.lineno}: delete `{ast.unparse(stmt).splitlines()[0]}`",
                              lambda f, i=i, k=k: delete_stmt(f, i, k)))
    return sites


def at(func, i):
    return list(ast.walk(func))[i]


def setattr_op(func, i, j, new_op):
    at(func, i).ops[j] = new_op()


def negate_if(func, i):
    node = at(func, i)
    node.test = ast.UnaryOp(ast.Not(), node.test)


def slice_iter(func, i, sl):
    node = at(func, i)
    node.iter = ast.parse(f"{ast.unparse(node.iter)}{sl}", mode="eval").body


def delete_stmt(func, i, k):
    at(func, i).body[k] = ast.Pass()


def run_tests():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(ROOT / "tests"), "-x", "-q", "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True)
    return result.returncode


def main():
    original = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(original)
    sites = mutation_sites(find_func(tree))

    if run_tests() != 0:
        raise SystemExit("suite fails on the unmutated code; fix it first")

    survivors = []
    try:
        for n, (desc, mutate) in enumerate(sites, 1):
            mutant = copy.deepcopy(tree)
            mutate(find_func(mutant))
            ast.fix_missing_locations(mutant)
            TARGET.write_text(ast.unparse(mutant), encoding="utf-8")
            killed = run_tests() != 0
            print(f"[{n:2}/{len(sites)}] {'killed  ' if killed else 'SURVIVED'} {desc}", flush=True)
            if not killed:
                survivors.append(desc)
    finally:
        TARGET.write_text(original, encoding="utf-8")

    print(f"\n{len(sites) - len(survivors)}/{len(sites)} mutants killed")
    for desc in survivors:
        print(f"  survived: {desc}")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
