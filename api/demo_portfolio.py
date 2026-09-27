def split_quantity_evenly(quantity, parts):
    """Return a balanced integer allocation whose sum equals quantity."""
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 0:
        raise ValueError("quantity must be a non-negative integer")
    if not isinstance(parts, int) or isinstance(parts, bool) or parts <= 0:
        raise ValueError("parts must be a positive integer")

    base, remainder = divmod(quantity, parts)
    return [base + int(index < remainder) for index in range(parts)]
