def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        return "Error: Division by zero"
    return a / b

# Test
print("1 + 2 =", add(1, 2))
print("5 - 3 =", subtract(5, 3))
print("3 * 4 =", multiply(3, 4))
print("10 / 2 =", divide(10, 2))
