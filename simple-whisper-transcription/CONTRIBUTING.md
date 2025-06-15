All contributions to this repo should include Python types and Google style docstrings for clarity.

Here is an example:
```
def foo(
    a: int = 1,
    b: int = 1
) -> int:
    """
    This function demonstrates appropriate function docstrings and typing.

    Args:
        a (int): sample integer input with hardcoded default.
        b (int): sample integer input with hardcoded default.

    Returns:
        int: sample integer return value
    """
    return a * b
```