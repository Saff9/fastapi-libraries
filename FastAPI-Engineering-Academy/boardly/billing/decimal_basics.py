# boardly/billing/decimal_basics.py
"""The decimal type, the string-constructor rule, and the exactness guarantee."""
from decimal import Decimal
from dataclasses import dataclass


@dataclass
class Project:
    name: str
    budget: Decimal                       # always Decimal, never float


# 1. The bug: passing a float captures the binary imprecision
print("Decimal(0.1) ->", Decimal(0.1))    # 0.1000000000000000055511151231257827021181583404541015625

# 2. The rule: always pass a string
print('Decimal("0.1") ->', Decimal("0.1"))   # 0.1

# 3. The exactness guarantee
float_total = 0.1 + 0.2
decimal_total = Decimal("0.1") + Decimal("0.2")
print("float 0.1 + 0.2 == 0.3:    ", float_total == 0.3)          # False
print("Decimal 0.1 + 0.2 == 0.3:  ", decimal_total == Decimal("0.3"))  # True

# 4. The boardly use: budget arithmetic
p = Project(name="alpha", budget=Decimal("1000.00"))
spent = Decimal("12.34")
remaining = p.budget - spent
print(f"{p.name} remaining: {remaining}")                        # 987.66
print("exact equality: ", remaining == Decimal("987.66"))         # True

# 5. Multiplication and division stay exact (within context precision)
unit_price = Decimal("9.99")
three = Decimal(unit_price) * Decimal(3)
print("9.99 * 3 ==", three)                                          # 29.97

# 6. Inspection: as_tuple reveals the digits
print("Decimal('1.00').as_tuple():", Decimal("1.00").as_tuple())   # DecimalTuple(sign=0, digits=(1, 0, 0), exponent=-2)

# 7. The forbidden pattern in billing
def bad_invoice_total(lines: list[tuple[float, int]]) -> float:
    return sum(p * q for p, q in lines)        # float * int -> float; bug

def good_invoice_total(lines: list[tuple[Decimal, int]]) -> Decimal:
    return sum(p * q for p, q in lines)       # Decimal * int -> Decimal; exact

lines_f = [(0.10, 3), (0.20, 1), (0.30, 2)]
lines_d = [(Decimal("0.10"), 3), (Decimal("0.20"), 1), (Decimal("0.30"), 2)]
print("float total raw:", bad_invoice_total(lines_f))            # 1.1 (looks clean; the underlying float is 1.1000000000000001)
print("Decimal total raw:", good_invoice_total(lines_d))        # 1.10 (exact; preserves the two-decimal-places scale)
