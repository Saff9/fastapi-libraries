"""Demonstrate product, combinations, permutations, combinations_with_replacement."""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class User:
    id: UUID
    name: str


@dataclass(frozen=True)
class Project:
    id: UUID
    name: str
    status: str   # "planning" | "active" | "archived"


# A small fixture: 3 users, 2 statuses, 3 projects
users = [
    User(uuid4(), "Ana"),
    User(uuid4(), "Bo"),
    User(uuid4(), "Cai"),
]
statuses = ["planning", "active"]
projects = [
    Project(uuid4(), "Auth Rewrite", "planning"),
    Project(uuid4(), "Search v2", "active"),
    Project(uuid4(), "Onboarding", "planning"),
]


def product_cartesian() -> None:
    """product(*iterables, repeat=1) — the Cartesian product."""
    # One iterable, repeated: product("AB", repeat=2) -> AA, AB, BA, BB
    pairs = list(itertools.product("AB", repeat=2))
    print(f"product('AB', repeat=2) -> {pairs}")

    # Two iterables: product(users, statuses) -> every (user, status) pair
    assignments = list(itertools.product(users, statuses))
    print(f"product(users, statuses) — {len(assignments)} (user, status) pairs:")
    for u, s in assignments:
        print(f"  {u.name} x {s}")

    # Three iterables: product(users, projects, statuses) -> 3*3*2 = 18 triples
    triples = list(itertools.product(users[:2], projects[:2], statuses))
    print(f"product(users[:2], projects[:2], statuses) — {len(triples)} triples (2*2*2)")


def combinations_subsets() -> None:
    """combinations(iterable, r) — r-length subsets, no repetition, lex order."""
    # All pairs of reviewers from 3 users
    review_pairs = list(itertools.combinations(users, 2))
    print(f"combinations(users, 2) — {len(review_pairs)} review pairs:")
    for pair in review_pairs:
        print(f"  {pair[0].name} + {pair[1].name}")

    # 3-of-5 from "ABCDE"
    triples = list(itertools.combinations("ABCDE", 3))
    print(f"combinations('ABCDE', 3) -> {triples}")
    print(f"  (len = C(5, 3) = {math.comb(5, 3)})")


def permutations_orderings() -> None:
    """permutations(iterable, r=None) — r-length orderings; default r=len(iterable)."""
    # Default r = len(iterable): all orderings of "ABC"
    all_orders = list(itertools.permutations("ABC"))
    print(f"permutations('ABC') -> {all_orders}")
    print(f"  (len = 3! = {math.factorial(3)})")

    # r=2: orderings of length 2 (AB != BA, so 6 not 3)
    pairs = list(itertools.permutations("ABC", 2))
    print(f"permutations('ABC', 2) -> {pairs}")
    print(f"  (len = P(3, 2) = {math.perm(3, 2)})")

    # Assignment orderings: 3 tickets, 3 engineers, all 1-to-1 assignments
    assignments = list(itertools.permutations(users, 3))
    print(f"permutations(users, 3) — {len(assignments)} 1-to-1 assignment orderings")
    for assign in assignments:
        print(f"  {[u.name for u in assign]}")


def combinations_with_replacement_demo() -> None:
    """combinations_with_replacement(iterable, r) — subsets with repetition allowed."""
    # Multisets of size 2 from "AB" -> AA, AB, BB (not BA — order doesn't matter)
    multisets = list(itertools.combinations_with_replacement("AB", 2))
    print(f"combinations_with_replacement('AB', 2) -> {multisets}")
    print(f"  (len = C(2+2-1, 2) = {math.comb(3, 2)})")

    # Pick 2 snacks from {apple, banana, cherry} with replacement
    snacks = list(itertools.combinations_with_replacement("ABC", 2))
    print(f"combinations_with_replacement('ABC', 2) -> {snacks}")


def combinatorial_explosion_warning() -> None:
    """Show the math — these grow fast."""
    # product with repeat — password-style enumeration
    n_chars = 26
    n_length = 6
    product_size = n_chars ** n_length
    print(f"product(alphabet, repeat={n_length}) = {n_chars}^{n_length} = {product_size:,} passwords")
    print(f"  (real password crackers: 95^8 = {95**8:,} for 8-char printable ASCII)")

    # combinations — lottery ticket
    n = 50
    r = 5
    comb_size = math.comb(n, r)
    print(f"combinations(range({n}), {r}) = C({n}, {r}) = {comb_size:,} tickets")

    # permutations — race finish order
    n = 8
    r = 3
    perm_size = math.perm(n, r)
    print(f"permutations(range({n}), {r}) = P({n}, {r}) = {perm_size:,} podiums")

    # combinations_with_replacement — dice rolls
    n = 6
    r = 3
    cwr_size = math.comb(n + r - 1, r)
    print(f"combinations_with_replacement(range({n}), {r}) = C({n+r-1}, {r}) = {cwr_size:,} dice outcomes")

    # Memory cost of materialising: each tuple is ~80 bytes
    bytes_estimate = product_size * 80
    print(f"\nMaterialising product(alphabet, repeat=6) as a list would take ~{bytes_estimate / 1_000_000_000:.1f} GB of RAM")
    print(f"Iterating one-by-one via `for pwd in product(...)` takes O(1) memory")


def password_brute_force_demo() -> None:
    """A realistic demo: enumerate 3-char 'abc' passwords."""
    charset = "abc"
    found = None
    target = "cab"
    for pwd in itertools.product(charset, repeat=3):
        candidate = "".join(pwd)
        if candidate == target:
            found = candidate
            break  # early exit — don't enumerate the rest
    print(f"brute-force 'abc' x 3 looking for {target!r}: found {found!r}")
    print(f"  (max space = {3**3} = 27 candidates; early break = O(1) memory)")


def main() -> None:
    print("=== product: Cartesian ===")
    product_cartesian()
    print()
    print("=== combinations: subsets, no repetition ===")
    combinations_subsets()
    print()
    print("=== permutations: all orderings ===")
    permutations_orderings()
    print()
    print("=== combinations_with_replacement: subsets with repetition ===")
    combinations_with_replacement_demo()
    print()
    print("=== combinatorial explosion ===")
    combinatorial_explosion_warning()
    print()
    print("=== password brute-force demo ===")
    password_brute_force_demo()


if __name__ == "__main__":
    main()
