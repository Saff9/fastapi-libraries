# boardly/billing/context_and_precision.py
"""Context, precision, rounding modes, quantize, and the signal classes."""
import decimal
from decimal import (
    Decimal, getcontext, localcontext, Context,
    ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_DOWN, ROUND_05UP,
    InvalidOperation, Overflow, FloatOperation,
)


# 1. The default context
ctx = getcontext()
print(f"default prec={ctx.prec}, rounding={ctx.rounding}")   # prec=28, rounding=ROUND_HALF_EVEN

# 2. A custom context
high_prec = Context(prec=10, rounding=ROUND_HALF_UP)
print(f"custom  prec={high_prec.prec}, rounding={high_prec.rounding}")

# 3. Precision affects division, not addition
print("default 1/3 =", Decimal("1") / Decimal("3"))             # 0.3333333333333333333333333333
with localcontext() as scoped:
    scoped.prec = 10
    print("scoped 1/3   =", Decimal("1") / Decimal("3"))       # 0.3333333333
print("after scope 1/3 =", Decimal("1") / Decimal("3"))       # 0.3333333333333333333333333333 again

# 4. Rounding modes: banker's (default) vs half-up vs down
half_way = Decimal("1.005")
print("quantize HALF_EVEN:", half_way.quantize(Decimal("0.01")))                          # 1.00
print("quantize HALF_UP:  ", half_way.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))   # 1.01
print("quantize DOWN:     ", half_way.quantize(Decimal("0.01"), rounding=ROUND_DOWN))      # 1.00

# 5. localcontext with a pre-built Context
scoped_ctx = Context(prec=6, rounding=ROUND_HALF_UP)
with localcontext(scoped_ctx) as ctx_in:
    print(f"inside: prec={getcontext().prec}, rounding={getcontext().rounding}")   # prec=6, HALF_UP
    print("inside 1/3 =", Decimal("1") / Decimal("3"))                              # 0.333333
print(f"after: prec={getcontext().prec}, rounding={getcontext().rounding}")       # prec=28, HALF_EVEN

# 6. The boardly tax calculation, scoped correctly
def tax_round(amount: Decimal) -> Decimal:
    """Round a tax amount to 2 decimal places, half-up (consumer-tax convention)."""
    with localcontext() as ctx:
        ctx.rounding = ROUND_HALF_UP
        return amount.quantize(Decimal("0.01"))

print("tax 1.005 ->", tax_round(Decimal("1.005")))               # 1.01
print("tax 1.004 ->", tax_round(Decimal("1.004")))               # 1.00
print("tax 2.5   ->", tax_round(Decimal("2.5")))                  # 2.50

# 7. Signals and traps
print("default traps:", {k.__name__: v for k, v in getcontext().traps.items()})

# FloatOperation is not trapped by default — but you can trap it
with localcontext() as ctx:
    ctx.traps[FloatOperation] = True
    try:
        Decimal(0.1)                       # raises FloatOperation
    except FloatOperation as e:
        print("FloatOperation trapped:", e)   # [<class 'decimal.FloatOperation'>]

# Overflow IS trapped by default — product exponent exceeds Emax (999999)
try:
    Decimal("1e999999") * Decimal("1e999999")
except Overflow as e:
    print("Overflow trapped:", str(e)[:60])

# InvalidOperation IS trapped by default — sqrt of negative
try:
    Decimal("-1").sqrt()
except InvalidOperation as e:
    print("InvalidOperation trapped:", str(e)[:60])
