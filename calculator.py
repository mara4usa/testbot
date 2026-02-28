def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        raise ValueError("Division by zero")
    return a / b

def power(a, b):
    return a ** b

def modulo(a, b):
    if b == 0:
        raise ValueError("Modulo by zero")
    return a % b

if __name__ == "__main__":
    print("1 + 2 =", add(1, 2))
    print("5 - 3 =", subtract(5, 3))
    print("3 * 4 =", multiply(3, 4))
    print("10 / 2 =", divide(10, 2))
    
    # Test power and modulo
    print("2 ** 3 =", power(2, 3))
    print("10 % 3 =", modulo(10, 3))
    
    # Test exception handling
    try:
        divide(5, 0)
    except ValueError as e:
        print("divide(5, 0) raised:", e)
