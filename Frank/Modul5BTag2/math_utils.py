class MathUtils:
    """A class containing various mathematical utility methods."""

    def add(self, a, b):
        """Returns the sum of two integers, a and b."""
        return a + b

    def subtract(self, a, b):
        """Returns the result of subtracting b from a."""
        return a - b

    def multiply(self, a, b):
        """Returns the product of two integers, a and b."""
        return a * b

    def divide(self, a, b):
        """Returns the result of dividing a by b, handling division by zero."""
        if b == 0:
            return -1.0  # Handle division by zero
        else:
            return a / b
            
from math_utils import MathUtils  # Import the class

math_utils = MathUtils()  # Create an instance of the class

# Call the methods to perform calculations
sum = math_utils.add(5, 3)
difference = math_utils.subtract(10, 4)
product = math_utils.multiply(6, 7)
quotient = math_utils.divide(15, 3)

print(sum)  # Output: 8
print(difference)  # Output: 6
print(product)  # Output: 42
print(quotient)  # Output: 5.0