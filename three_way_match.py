"""
Three-Way Match Demo using SQLite
----------------------------------
A "three-way match" is an accounts-payable control. Before paying a supplier,
we compare three documents for the same Purchase Order (PO):

  1. Purchase Order  - what we ORDERED (quantity and agreed price)
  2. Receipt         - what we actually RECEIVED in the warehouse
  3. Invoice         - what the supplier is BILLING us for

If quantity and price agree across all three, the invoice can be paid.
If anything differs, the invoice is flagged for a human to review.
"""

import sqlite3  # SQLite comes built into Python - no install needed


# ---------------------------------------------------------------------------
# STEP 1: Create a database and the three tables
# ---------------------------------------------------------------------------

# ":memory:" creates a temporary database that lives only while the script runs.
# (Use a filename like "ap.db" instead if you want the data saved to disk.)
conn = sqlite3.connect(":memory:")
cursor = conn.cursor()  # The cursor is what we use to run SQL commands

# Each table holds the same three columns: PO number, quantity, and unit price.
cursor.execute("""
    CREATE TABLE PurchaseOrder (
        po_number TEXT PRIMARY KEY,  -- Unique ID for each order
        quantity  INTEGER,           -- How many units we ordered
        price     REAL               -- Agreed price per unit
    )
""")

cursor.execute("""
    CREATE TABLE Receipt (
        po_number TEXT PRIMARY KEY,  -- Links back to the purchase order
        quantity  INTEGER,           -- How many units actually arrived
        price     REAL               -- Price per unit on the delivery note
    )
""")

cursor.execute("""
    CREATE TABLE Invoice (
        po_number TEXT PRIMARY KEY,  -- Links back to the purchase order
        quantity  INTEGER,           -- How many units the supplier billed
        price     REAL               -- Price per unit the supplier billed
    )
""")


# ---------------------------------------------------------------------------
# STEP 2: Insert sample data
# ---------------------------------------------------------------------------
# Format of each row: (po_number, quantity, price)

# What we ordered
cursor.executemany(
    "INSERT INTO PurchaseOrder VALUES (?, ?, ?)",
    [
        ("PO-1001", 100, 5.00),   # Will match perfectly
        ("PO-1002", 50, 20.00),   # Quantity problem: fewer received
        ("PO-1003", 10, 99.00),   # Price problem: supplier overbilled
    ],
)

# What arrived in the warehouse
cursor.executemany(
    "INSERT INTO Receipt VALUES (?, ?, ?)",
    [
        ("PO-1001", 100, 5.00),
        ("PO-1002", 45, 20.00),   # Only 45 of 50 units arrived
        ("PO-1003", 10, 99.00),
    ],
)

# What the supplier billed us
cursor.executemany(
    "INSERT INTO Invoice VALUES (?, ?, ?)",
    [
        ("PO-1001", 100, 5.00),
        ("PO-1002", 50, 20.00),   # Billed for all 50, but only 45 received
        ("PO-1003", 10, 105.00),  # Billed $105/unit instead of $99
    ],
)

conn.commit()  # Save the inserts to the database


# ---------------------------------------------------------------------------
# STEP 3: The three-way match function
# ---------------------------------------------------------------------------

def check_three_way_match(po_number):
    """Compare quantity and price for one PO across all three tables."""

    # Look up the matching row in each table.
    # The "?" is a placeholder; SQLite safely fills it in with po_number.
    # fetchone() returns a single row like (100, 5.0), or None if not found.
    po = cursor.execute(
        "SELECT quantity, price FROM PurchaseOrder WHERE po_number = ?", (po_number,)
    ).fetchone()
    receipt = cursor.execute(
        "SELECT quantity, price FROM Receipt WHERE po_number = ?", (po_number,)
    ).fetchone()
    invoice = cursor.execute(
        "SELECT quantity, price FROM Invoice WHERE po_number = ?", (po_number,)
    ).fetchone()

    print(f"\nChecking {po_number}...")

    # If any of the three documents is missing, we can't match - flag it.
    if po is None or receipt is None or invoice is None:
        print("  FLAGGED FOR REVIEW: one or more documents are missing.")
        return

    # Unpack each row into named variables so the comparisons are easy to read.
    po_qty, po_price = po
    rc_qty, rc_price = receipt
    inv_qty, inv_price = invoice

    print(f"  PO:      qty={po_qty}, price={po_price:.2f}")
    print(f"  Receipt: qty={rc_qty}, price={rc_price:.2f}")
    print(f"  Invoice: qty={inv_qty}, price={inv_price:.2f}")

    # Collect every problem we find, so the reviewer sees all of them at once.
    problems = []

    if not (po_qty == rc_qty == inv_qty):
        problems.append("quantity does not match")

    if not (po_price == rc_price == inv_price):
        problems.append("price does not match")

    # Report the result
    if problems:
        print("  FLAGGED FOR REVIEW: " + ", ".join(problems))
    else:
        print("  MATCH: OK to pay")


# ---------------------------------------------------------------------------
# STEP 4: Run the check for each sample PO
# ---------------------------------------------------------------------------

check_three_way_match("PO-1001")  # Expected: match
check_three_way_match("PO-1002")  # Expected: flagged (quantity)
check_three_way_match("PO-1003")  # Expected: flagged (price)
check_three_way_match("PO-9999")  # Expected: flagged (doesn't exist)

conn.close()  # Always close the database connection when finished
